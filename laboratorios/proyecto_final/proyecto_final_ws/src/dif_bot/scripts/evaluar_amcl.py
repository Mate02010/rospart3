#!/usr/bin/env python3
"""Práctica 4: mide cómo converge AMCL a partir de una pose inicial.

Le da a AMCL una pose inicial por /initialpose (o pide localización global), recorre
una ruta corta en la zona libre cerca del origen y guarda a 10 Hz la estimación de
AMCL contra la pose real de Gazebo. El robot se maneja con la pose real, como lo
haría un teleoperador, para que la ruta sea la misma en todas las corridas.
  estimación -> TF map -> odom (AMCL) compuesto con odom -> base_footprint (EKF)
  /amcl_pose -> pose y covarianza que publica AMCL en cada actualización
  pose real  -> /ground_truth/odom (marco world, que coincide con map)

Uso (con localizacion.launch.py corriendo):
  ros2 run dif_bot evaluar_amcl.py --ros-args -p use_sim_time:=true -p etiqueta:=pose_correcta
  ros2 run dif_bot evaluar_amcl.py --ros-args -p use_sim_time:=true -p etiqueta:=pose_incorrecta \
      -p x0:=1.0 -p y0:=-0.8 -p yaw0:=0.6
  ros2 run dif_bot evaluar_amcl.py --ros-args -p use_sim_time:=true -p etiqueta:=global \
      -p global_loc:=true -p vueltas:=2
Cada corrida va con un localizacion.launch.py nuevo, para que el robot parta de (0, 0, 0)
y AMCL no arrastre partículas de la corrida anterior. Al terminar la ruta el robot gira
a yaw 0, así que si se repite sin relanzar al menos queda orientado como al inicio.
"""
import csv
import json
import math
import os
from collections import deque

import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped, TwistStamped
from lifecycle_msgs.srv import GetState
from nav2_msgs.msg import ParticleCloud
from nav_msgs.msg import Odometry
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from std_srvs.srv import Empty
from tf2_ros import Buffer, TransformException, TransformListener

# Puntos de la ruta en el marco del mundo (= map), pensada para arrancar en (0, 0).
# Despeje mínimo a los obstáculos de bodega.sdf: 0,87 m (muro_interior_1); el robot
# mide 0,31 m del centro a la esquina, así que pasa sobrado.
RUTA = [(1.2, 0.0), (1.2, -1.2), (-0.8, -1.2), (-0.8, 0.4), (0.0, 0.0)]

UMBRAL_POS = 0.15   # m
UMBRAL_YAW = 5.0    # grados
PERMANENCIA = 2.0   # s que el error debe quedarse bajo los umbrales

COLUMNAS = ['t', 'x_est', 'y_est', 'yaw_est', 'x_real', 'y_real', 'yaw_real', 'err_pos', 'err_yaw_deg',
            'x_amcl', 'y_amcl', 'yaw_amcl', 'var_xy_amcl', 'var_yaw_amcl', 'err_pos_amcl',
            'err_yaw_amcl_deg', 'particulas']


def yaw_de(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def angulo(a):
    return math.atan2(math.sin(a), math.cos(a))


def segundos(stamp):
    return stamp.sec + stamp.nanosec * 1e-9


def errores(est, real):
    """Error de posición [m] y de orientación [°] entre dos poses (x, y, yaw)."""
    return (math.hypot(est[0] - real[0], est[1] - real[1]),
            abs(math.degrees(angulo(est[2] - real[2]))))


def convergencia(t, e_pos, e_yaw):
    """Primera muestra desde la que el error queda bajo los umbrales durante PERMANENCIA s."""
    inicio = None
    for i, (ti, ep, ey) in enumerate(zip(t, e_pos, e_yaw)):
        if ep < UMBRAL_POS and ey < UMBRAL_YAW:
            if inicio is None:
                inicio = i
            if ti - t[inicio] >= PERMANENCIA:
                return inicio
        else:
            inicio = None
    return None


def rms(valores):
    return math.sqrt(sum(v * v for v in valores) / len(valores)) if valores else None


def redondear(v, n=4):
    return None if v is None or math.isnan(v) else round(v, n)


class EvaluarAmcl(Node):
    def __init__(self):
        super().__init__('evaluar_amcl')
        self.x0 = self.numero('x0', 0.0)
        self.y0 = self.numero('y0', 0.0)
        self.yaw0 = self.numero('yaw0', 0.0)
        self.cov_xy = self.numero('cov_xy', 0.25)     # (0,5 m)^2, igual que RViz
        self.cov_yaw = self.numero('cov_yaw', 0.0685)  # (15°)^2, igual que RViz
        self.global_loc = bool(self.declare_parameter('global_loc', False).value)
        self.etiqueta = self.declare_parameter('etiqueta', 'pose_correcta').value
        self.salida = self.declare_parameter('salida', os.path.expanduser('~/proyecto_final_ws/resultados')).value
        self.v = self.numero('v', 0.25)
        self.w_max = self.numero('w_max', 0.8)
        self.vueltas = int(self.declare_parameter('vueltas', 1).value)
        self.duracion_max = self.numero('duracion_max', 120.0)
        cmd_topic = self.declare_parameter('cmd_topic', '/diff_drive_controller/cmd_vel').value

        self.pub_cmd = self.create_publisher(TwistStamped, cmd_topic, 10)
        self.pub_ini = self.create_publisher(PoseWithCovarianceStamped, '/initialpose', 10)
        self.create_subscription(Odometry, '/ground_truth/odom', self.cb_real, 50)
        self.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', self.cb_amcl, 10)
        self.create_subscription(ParticleCloud, '/particle_cloud', self.cb_particulas, qos_profile_sensor_data)
        self.cli_estado = self.create_client(GetState, '/amcl/get_state')
        self.cli_global = self.create_client(Empty, '/reinitialize_global_localization')
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        self.real = deque(maxlen=500)  # (stamp, x, y, yaw): últimos 10 s de la pose real
        self.t_llegada_real = 0.0
        self.amcl = None               # última /amcl_pose: x, y, yaw, var_xy, var_yaw, err_pos, err_yaw
        self.n_amcl = 0
        self.particulas = None
        self.futuro = None
        self.t_pedido = None           # cuándo se pidió la pose inicial o la localización global
        self.t0 = None                 # t = 0 del registro: AMCL ya aceptó la pose inicial
        self.t_mov = None
        self.fase = 'esperando_amcl'
        self.t_fase = 0.0
        self.t_consulta = -10.0
        self.ruta = RUTA * self.vueltas
        self.i_punto = 0
        self.ruta_completa = False
        self.filas = []
        self.n_tick = 0
        self.create_timer(0.05, self.paso)  # control a 20 Hz, registro a 10 Hz

    def numero(self, nombre, defecto):
        # Acepta 1 o 1.0 desde la línea de comandos.
        return float(self.declare_parameter(nombre, defecto, ParameterDescriptor(dynamic_typing=True)).value)

    def ahora(self):
        return self.get_clock().now().nanoseconds * 1e-9

    # ---------------- Entradas ----------------

    def cb_real(self, m):
        p = m.pose.pose
        self.real.append((segundos(m.header.stamp), p.position.x, p.position.y, yaw_de(p.orientation)))
        self.t_llegada_real = self.ahora()

    def real_en(self, stamp):
        """Pose real más cercana en el tiempo a 'stamp'."""
        return min(self.real, key=lambda r: abs(r[0] - stamp))[1:]

    def cb_amcl(self, m):
        if self.t_pedido is None or not self.real:
            return  # todavía no se ha dado la pose inicial
        p, c = m.pose.pose, m.pose.covariance
        est = (p.position.x, p.position.y, yaw_de(p.orientation))
        self.amcl = est + (c[0] + c[7], c[35]) + errores(est, self.real_en(segundos(m.header.stamp)))
        self.n_amcl += 1

    def cb_particulas(self, m):
        self.particulas = len(m.particles)

    def estimacion(self):
        """Pose del robot en map según AMCL.

        Se compone a mano porque AMCL publica map -> odom con la marca de tiempo adelantada
        transform_tolerance (1 s) y la consulta directa map -> base_footprint falla al inicio.
        """
        try:
            m_o = self.tf_buffer.lookup_transform('map', 'odom', Time())
            o_b = self.tf_buffer.lookup_transform('odom', 'base_footprint', Time())
        except TransformException:
            return None
        mx, my = m_o.transform.translation.x, m_o.transform.translation.y
        myaw = yaw_de(m_o.transform.rotation)
        ox, oy = o_b.transform.translation.x, o_b.transform.translation.y
        c, s = math.cos(myaw), math.sin(myaw)
        est = (mx + c * ox - s * oy, my + s * ox + c * oy, angulo(myaw + yaw_de(o_b.transform.rotation)))
        return segundos(o_b.header.stamp), est

    # ---------------- Salidas ----------------

    def publicar(self, v, w):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_footprint'
        msg.twist.linear.x, msg.twist.angular.z = v, w
        self.pub_cmd.publish(msg)

    def publicar_pose_inicial(self):
        msg = PoseWithCovarianceStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'map'
        msg.pose.pose.position.x = self.x0
        msg.pose.pose.position.y = self.y0
        msg.pose.pose.orientation.z = math.sin(self.yaw0 / 2.0)
        msg.pose.pose.orientation.w = math.cos(self.yaw0 / 2.0)
        cov = [0.0] * 36
        cov[0] = cov[7] = self.cov_xy   # varianza en x e y
        cov[35] = self.cov_yaw          # varianza en yaw
        msg.pose.covariance = cov
        self.pub_ini.publish(msg)

    # ---------------- Máquina de estados ----------------

    def cambiar_fase(self, fase, t):
        self.fase, self.t_fase = fase, t

    def paso(self):
        t = self.ahora()
        if self.fase == 'esperando_amcl':
            self.publicar(0.0, 0.0)
            self.esperar_amcl(t)
        elif self.fase == 'pose_inicial':
            self.publicar(0.0, 0.0)
            self.dar_pose_inicial(t)
        else:
            self.n_tick += 1
            if self.n_tick % 2 == 0:
                self.registrar(t)
            self.mover(t)

    def esperar_amcl(self, t):
        """Pregunta cada segundo el estado de AMCL hasta que el lifecycle manager lo active."""
        if self.futuro is not None:
            if not self.futuro.done():
                return
            r = self.futuro.result()
            self.futuro = None
            estado = r.current_state.label if r is not None else '?'
            if estado == 'active' and self.real:
                self.get_logger().info('AMCL activo y llegando la pose real.')
                self.cambiar_fase('pose_inicial', t)
                return
            if estado != 'active':
                self.get_logger().info(f'AMCL en estado "{estado}"; esperando a que lo active el lifecycle manager.',
                                       throttle_duration_sec=5.0)
            else:
                self.get_logger().warning('AMCL activo, pero no llega /ground_truth/odom.', throttle_duration_sec=5.0)
        if t - self.t_consulta < 1.0:
            return
        self.t_consulta = t
        if self.cli_estado.service_is_ready():
            self.futuro = self.cli_estado.call_async(GetState.Request())
        else:
            self.get_logger().info('Esperando /amcl/get_state...', throttle_duration_sec=5.0)

    def dar_pose_inicial(self, t):
        """Manda la pose inicial (cada 2 s) hasta que AMCL publique /amcl_pose."""
        if self.n_amcl > 0:
            x, y, yaw = self.amcl[:3]
            self.get_logger().info(f'AMCL aceptó la pose: ({x:.2f}, {y:.2f}, {math.degrees(yaw):.1f}°). Registrando.')
            self.t0 = t
            self.cambiar_fase('quieto', t)
            return
        if self.t_pedido is not None and t - self.t_pedido < 2.0:
            return
        if self.global_loc:
            if not self.cli_global.service_is_ready():
                self.get_logger().info('Esperando /reinitialize_global_localization...', throttle_duration_sec=5.0)
                return
            self.cli_global.call_async(Empty.Request())
            self.get_logger().info('Localización global: partículas repartidas en todo el mapa.')
        else:
            if self.pub_ini.get_subscription_count() == 0:
                self.get_logger().info('Nadie escucha /initialpose todavía...', throttle_duration_sec=5.0)
                return
            self.publicar_pose_inicial()
            self.get_logger().info(
                f'Pose inicial enviada: ({self.x0:.2f}, {self.y0:.2f}, {math.degrees(self.yaw0):.1f}°)')
        self.t_pedido = t

    def mover(self, t):
        if t - self.t0 > self.duracion_max and self.fase != 'final':
            self.get_logger().warning('Se acabó el tiempo (duracion_max) antes de terminar la ruta.')
            self.cambiar_fase('final', t)
        if self.fase == 'quieto':
            # 2 s quieto: muestra la pose que tomó AMCL antes de moverse.
            self.publicar(0.0, 0.0)
            if t - self.t_fase >= 2.0:
                self.t_mov = t - self.t0
                self.cambiar_fase('ruta', t)
        elif self.fase == 'ruta':
            self.publicar(*self.ir_a_punto(t))
        elif self.fase == 'orientar':
            self.publicar(0.0, self.girar_a_cero(t))
        elif self.fase == 'final':
            self.publicar(0.0, 0.0)
            if t - self.t_fase >= 2.0:
                self.reportar()
                raise SystemExit

    def ir_a_punto(self, t):
        """Control al siguiente punto con la pose real: gira en el sitio y luego avanza corrigiendo el rumbo."""
        _, x, y, yaw = self.real[-1]
        if t - self.t_llegada_real > 0.5:
            return 0.0, 0.0  # sin pose real reciente, quieto
        px, py = self.ruta[self.i_punto]
        dist = math.hypot(px - x, py - y)
        if dist < 0.1:
            self.i_punto += 1
            if self.i_punto >= len(self.ruta):
                self.ruta_completa = True
                self.get_logger().info('Ruta completa; girando a yaw 0.')
                self.cambiar_fase('orientar', t)
            return 0.0, 0.0
        e = angulo(math.atan2(py - y, px - x) - yaw)
        w = max(-self.w_max, min(self.w_max, 2.0 * e))
        if abs(e) > 0.2:
            return 0.0, w
        return min(self.v, 0.6 * dist + 0.05), w

    def girar_a_cero(self, t):
        """Giro en el sitio hasta yaw 0: el último tramo deja al robot a unos -27°."""
        if t - self.t_llegada_real > 0.5:
            return 0.0
        e = angulo(-self.real[-1][3])
        if abs(e) < 0.03:
            self.cambiar_fase('final', t)
            return 0.0
        w = max(-self.w_max, min(self.w_max, 2.0 * e))
        return math.copysign(max(abs(w), 0.1), w)

    def registrar(self, t):
        e = self.estimacion()
        if e is None or self.amcl is None or not self.real:
            return
        stamp, est = e
        real = self.real_en(stamp)
        fila = [t - self.t0, *est, *real, *errores(est, real), *self.amcl]
        fila.append(float('nan') if self.particulas is None else self.particulas)
        self.filas.append(fila)

    # ---------------- Resultados ----------------

    def reportar(self):
        os.makedirs(self.salida, exist_ok=True)
        base = os.path.join(self.salida, f'p4_{self.etiqueta}')
        with open(base + '.csv', 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(COLUMNAS)
            for fila in self.filas:
                w.writerow([f'{v:.6g}' if isinstance(v, float) else v for v in fila])
        if not self.filas:
            self.get_logger().error('No se registró ninguna muestra (¿hay TF map -> odom?).')
            return

        t = [f[0] for f in self.filas]
        ep = [f[7] for f in self.filas]
        ey = [f[8] for f in self.filas]
        i = convergencia(t, ep, ey)
        # Distancia recorrida (pose real) hasta cada muestra.
        recorrido = [0.0]
        for a, b in zip(self.filas, self.filas[1:]):
            recorrido.append(recorrido[-1] + math.hypot(b[4] - a[4], b[5] - a[5]))
        post_p = ep[i:] if i is not None else []
        post_y = ey[i:] if i is not None else []
        x_a, y_a, yaw_a, var_xy, var_yaw, ep_a, ey_a = self.amcl

        if self.global_loc:
            inicial = 'localización global (/reinitialize_global_localization)'
        else:
            inicial = {'x': self.x0, 'y': self.y0, 'yaw_deg': round(math.degrees(self.yaw0), 2),
                       'cov_xy': self.cov_xy, 'cov_yaw': self.cov_yaw}
        res = {
            'etiqueta': self.etiqueta,
            'pose_inicial_dada': inicial,
            'pose_real_inicial': {'x': redondear(self.filas[0][4], 3), 'y': redondear(self.filas[0][5], 3),
                                  'yaw_deg': round(math.degrees(self.filas[0][6]), 2)},
            'ruta': f'{len(RUTA)} puntos x {self.vueltas} vuelta(s), v={self.v} m/s',
            'ruta_completa': self.ruta_completa,
            'inicio_movimiento_s': redondear(self.t_mov, 2),
            'duracion_s': round(t[-1], 2),
            'muestras': len(self.filas),
            'mensajes_amcl_pose': self.n_amcl,
            'umbral_convergencia': {'pos_m': UMBRAL_POS, 'yaw_deg': UMBRAL_YAW, 'permanencia_s': PERMANENCIA},
            'convergio': i is not None,
            'tiempo_convergencia_s': round(t[i], 2) if i is not None else None,
            'recorrido_al_converger_m': round(recorrido[i], 2) if i is not None else None,
            'error_inicial_m': round(ep[0], 3),
            'error_inicial_yaw_deg': round(ey[0], 2),
            'error_final_m': round(ep[-1], 3),
            'error_final_yaw_deg': round(ey[-1], 2),
            'error_max_m': round(max(ep), 3),
            'error_max_yaw_deg': round(max(ey), 2),
            'error_rms_post_convergencia_m': redondear(rms(post_p), 3),
            'error_rms_post_convergencia_yaw_deg': redondear(rms(post_y), 2),
            'error_max_post_convergencia_m': round(max(post_p), 3) if post_p else None,
            'amcl_pose_final': {'error_m': round(ep_a, 3), 'error_yaw_deg': round(ey_a, 2),
                                'var_xy': redondear(var_xy, 5), 'var_yaw': redondear(var_yaw, 5)},
            'particulas_final': self.particulas,
        }
        with open(base + '.json', 'w', encoding='utf-8') as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
        self.get_logger().info(json.dumps(res, ensure_ascii=False))
        self.get_logger().info(f'Guardado en {base}.csv / .json')


def main():
    rclpy.init()
    nodo = EvaluarAmcl()
    try:
        rclpy.spin(nodo)
    except SystemExit:
        pass
    except (KeyboardInterrupt, ExternalShutdownException):
        # Cortado a mano: guarda lo que haya.
        if nodo.filas:
            nodo.reportar()
    finally:
        nodo.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
