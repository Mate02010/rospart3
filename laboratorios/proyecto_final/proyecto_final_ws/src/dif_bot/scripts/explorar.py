#!/usr/bin/env python3
"""Práctica 3: recorre la bodega por una ruta fija mientras slam_toolbox hace el mapa.

Reemplaza la teleoperación para que la corrida se repita igual a distintas
velocidades. El robot va de punto en punto en el marco world de Gazebo (coincide
con map porque el SLAM arranca con el robot en el origen) usando la pose real de
/ground_truth/odom: gira en el sitio si el rumbo hacia el punto está desviado y,
si no, avanza corrigiendo el rumbo de forma proporcional.

Uso (con slam.launch.py corriendo):
  ros2 run dif_bot explorar.py --ros-args -p use_sim_time:=true -p v:=0.15 -p w_max:=0.4 -p etiqueta:=lento
  ros2 run dif_bot explorar.py --ros-args -p use_sim_time:=true -p v:=0.45 -p w_max:=1.2 -p etiqueta:=rapido
  ros2 run dif_bot explorar.py --ros-args -p use_sim_time:=true -p ruta:=/ruta/a/puntos.yaml

El YAML de 'ruta' es una lista de puntos [x, y] en metros, sola o bajo la llave 'puntos'.
Si el controlador escucha otro tópico: -p cmd_topic:=/cmd_vel
"""
import csv
import json
import math
import os
import time

import rclpy
import yaml
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from rclpy.executors import ExternalShutdownException
from rclpy.node import Node

# Ruta por defecto (marco world, metros). Pasa por las cuatro zonas de la bodega,
# por los dos lados de cada muro interior y vuelve al origen para cerrar el lazo.
# Revisada contra worlds/bodega.sdf: cada tramo queda a 0,45 m o más de todo
# obstáculo; como el robot mide 0,48 x 0,40 m, sobran 0,25 m por lado.
Y_NORTE, X_ESTE, X_OESTE = 3.4625, 5.4625, -5.4625  # centro de los pasillos angostos
RUTA = [
    (3.4, 0.0),          # al este por el centro
    (3.4, Y_NORTE),      # sube entre la columna 1 y el estante 3
    (X_ESTE, Y_NORTE),   # pasa por encima del estante 3
    (X_ESTE, -3.4),      # baja junto al muro este, entre el muro y la caja 3
    (3.3, -3.4),         # sigue junto al muro sur
    (3.3, -0.45),        # sube por el lado este del muro interior 2
    (1.7, -0.45),        # rodea su punta
    (1.7, -3.4),         # baja por su lado oeste
    (X_OESTE, -3.4),     # al oeste junto al muro sur, debajo de la caja 2 y el estante 2
    (X_OESTE, Y_NORTE),  # sube por detrás de los estantes 2 y 1
    (-2.3, 3.4),         # al este junto al muro norte
    (-2.3, 0.4),         # baja por el lado oeste del muro interior 1
    (-0.7, 0.4),         # rodea su punta
    (-0.7, 3.4),         # sube por su lado este
    (0.0, 0.0),          # vuelve al origen
]

K_ANG = 1.5       # w = K_ANG * error de rumbo
K_LIN = 0.8       # v = K_LIN * distancia: frena al acercarse al punto
V_MIN = 0.04      # m/s, para no quedarse a pocos centímetros del punto
W_MIN = 0.15      # rad/s al girar en el sitio, por la misma razón
ALINEADO = 0.05   # rad: termina el giro en el sitio
DESVIADO = 0.35   # rad: vuelve a girar en el sitio


def yaw_de(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def angulo(a):
    return math.atan2(math.sin(a), math.cos(a))


def leer_ruta(ruta):
    with open(os.path.expanduser(ruta), encoding='utf-8') as f:
        datos = yaml.safe_load(f)
    if isinstance(datos, dict):
        datos = datos['puntos']
    return [(float(p[0]), float(p[1])) for p in datos]


class Explorar(Node):
    def __init__(self):
        super().__init__('explorar')
        self.cmd_topic = self.declare_parameter('cmd_topic', '/diff_drive_controller/cmd_vel').value
        self.v_max = float(self.declare_parameter('v', 0.25).value)
        self.w_max = float(self.declare_parameter('w_max', 0.8).value)
        self.tol = float(self.declare_parameter('tolerancia', 0.03).value)
        ruta = self.declare_parameter('ruta', '').value
        self.etiqueta = self.declare_parameter('etiqueta', '').value or f'v{self.v_max:g}'
        self.salida = self.declare_parameter('salida', os.path.expanduser('~/proyecto_final_ws/resultados')).value

        self.puntos = leer_ruta(ruta) if ruta else list(RUTA)
        largo = sum(math.dist(a, b) for a, b in zip(self.puntos, self.puntos[1:]))
        self.get_logger().info(
            f'Ruta de {len(self.puntos)} puntos ({"archivo " + ruta if ruta else "por defecto"}), '
            f'{largo:.1f} m sin contar el tramo inicial. v={self.v_max} m/s, w_max={self.w_max} rad/s')

        self.pub = self.create_publisher(TwistStamped, self.cmd_topic, 10)
        self.create_subscription(Odometry, '/ground_truth/odom', self.cb_real, 50)

        self.pose = None          # (x, y, yaw) real
        self.fase = 'esperando'   # esperando -> recorriendo -> fin
        self.t_listo = None
        self.i = 0
        self.girando = True
        self.saltados = []
        self.distancia = 0.0
        self.filas = []           # trayectoria real a 10 Hz
        self.ciclos_fin = 0
        self.create_timer(0.05, self.paso)  # control a 20 Hz

    def ahora(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def cb_real(self, m):
        p = m.pose.pose
        nueva = (p.position.x, p.position.y, yaw_de(p.orientation))
        if self.fase == 'recorriendo':
            self.distancia += math.hypot(nueva[0] - self.pose[0], nueva[1] - self.pose[1])
            t = self.ahora() - self.t0
            if not self.filas or t - self.filas[-1][0] >= 0.1:
                self.filas.append([round(t, 3), round(nueva[0], 4), round(nueva[1], 4), round(nueva[2], 4)])
        self.pose = nueva

    def publicar(self, v, w):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_footprint'
        msg.twist.linear.x, msg.twist.angular.z = v, w
        self.pub.publish(msg)

    def ir_a(self, i):
        """Pasa al punto i y fija el tiempo máximo para llegar (3 veces lo esperado + 30 s)."""
        self.i = i
        self.girando = True
        self.t_punto = self.ahora()
        x, y, _ = self.pose
        self.t_max_punto = 3.0 * math.dist((x, y), self.puntos[i]) / self.v_max + 30.0

    def paso(self):
        if self.fase == 'esperando':
            self.publicar(0.0, 0.0)
            # Espera la pose real y que el controlador esté suscrito al tópico.
            if self.pose is None or self.pub.get_subscription_count() == 0:
                return
            if self.t_listo is None:
                self.t_listo = self.ahora()
                self.get_logger().info(f'Pose real y {self.cmd_topic} listos. Arranca en 2 s.')
            if self.ahora() - self.t_listo >= 2.0:
                self.fase = 'recorriendo'
                self.t0, self.t0_real = self.ahora(), time.monotonic()
                self.ir_a(0)
            return

        if self.fase == 'fin':
            self.publicar(0.0, 0.0)
            self.ciclos_fin += 1
            if self.ciclos_fin >= 10:
                raise SystemExit
            return

        x, y, th = self.pose
        px, py = self.puntos[self.i]
        d = math.hypot(px - x, py - y)
        if d < self.tol or self.ahora() - self.t_punto > self.t_max_punto:
            if d < self.tol:
                self.get_logger().info(f'Punto {self.i + 1}/{len(self.puntos)} ({px:.2f}, {py:.2f}) '
                                       f't={self.ahora() - self.t0:.1f} s')
            else:
                self.saltados.append(self.i + 1)
                self.get_logger().warn(f'Punto {self.i + 1} no alcanzado a tiempo (a {d:.2f} m). Sigue al próximo.')
            if self.i + 1 < len(self.puntos):
                self.ir_a(self.i + 1)
            else:
                self.terminar()
            return

        e = angulo(math.atan2(py - y, px - x) - th)
        # Histéresis: gira en el sitio hasta quedar alineado y solo vuelve a girar
        # si se desvía bastante (lejos del punto, donde el rumbo es estable).
        if self.girando and abs(e) < ALINEADO:
            self.girando = False
        elif not self.girando and abs(e) > DESVIADO and d > 0.15:
            self.girando = True

        if self.girando:
            w = math.copysign(max(min(W_MIN, self.w_max), min(self.w_max, K_ANG * abs(e))), e)
            self.publicar(0.0, w)
        else:
            v = max(min(V_MIN, self.v_max), min(self.v_max, K_LIN * d)) * max(0.0, math.cos(e))
            w = max(-self.w_max, min(self.w_max, K_ANG * e))
            self.publicar(v, w)

    def terminar(self):
        self.fase = 'fin'
        self.publicar(0.0, 0.0)
        tiempo = self.ahora() - self.t0
        tiempo_real = time.monotonic() - self.t0_real
        res = {
            'etiqueta': self.etiqueta,
            'v_max': self.v_max,
            'w_max': self.w_max,
            'puntos': len(self.puntos),
            'puntos_saltados': self.saltados,
            'distancia_m': round(self.distancia, 2),
            'tiempo_s': round(tiempo, 1),
            'tiempo_real_s': round(tiempo_real, 1),
            'velocidad_media_m_s': round(self.distancia / tiempo, 3) if tiempo > 0 else None,
            'factor_tiempo_real': round(tiempo / tiempo_real, 2) if tiempo_real > 0 else None,
        }
        os.makedirs(self.salida, exist_ok=True)
        base = os.path.join(self.salida, f'p3_ruta_{self.etiqueta}')
        with open(base + '.csv', 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['t', 'x', 'y', 'yaw'])
            w.writerows(self.filas)
        with open(base + '.json', 'w', encoding='utf-8') as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
        self.get_logger().info(f'Recorrido terminado: {res["distancia_m"]} m en {res["tiempo_s"]} s '
                               f'de simulación ({res["tiempo_real_s"]} s reales).')
        self.get_logger().info(f'Guardado en {base}.csv / .json')


def main():
    rclpy.init()
    nodo = Explorar()
    try:
        rclpy.spin(nodo)
    except (SystemExit, KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        nodo.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
