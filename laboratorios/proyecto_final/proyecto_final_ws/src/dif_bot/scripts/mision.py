#!/usr/bin/env python3
"""Proyecto final: misión autónoma por waypoints con nav2_simple_commander.

Lee los puntos de un YAML (config/waypoints.yaml), espera a que Nav2 esté activo y
deja la misión lista para arrancar con un servicio. Cada punto se manda con goToPose
para medir su tiempo y su resultado; al final guarda un JSON con el resumen y un CSV
con la trayectoria (pose real de Gazebo y estimación de AMCL).
  estimación de AMCL -> TF map -> odom (AMCL) compuesto con odom -> base_footprint (EKF);
  no se usa /amcl_pose porque AMCL solo la publica al actualizar el filtro (cada 0,25 m
  o 0,2 rad) y al llegar a un punto puede ir atrasada.

Servicios (std_srvs/Trigger):
  /iniciar_mision   arranca la misión y responde enseguida (corre en otro hilo)
  /cancelar_mision  cancela la meta actual y termina la misión
Tópicos:
  /estado_mision     std_msgs/String con el estado en texto
  /waypoints_mision  visualization_msgs/MarkerArray con los puntos para RViz

Parámetros: waypoints_file, salida, publicar_pose_inicial, x0, y0, yaw0 (rad),
tiempo_max_s (por punto) y continuar_si_falla.

Uso (con navegacion.launch.py corriendo; o todo junto con mision.launch.py):
  ros2 run dif_bot mision.py --ros-args -p use_sim_time:=true
  ros2 service call /iniciar_mision std_srvs/srv/Trigger
  ros2 topic echo /estado_mision
Si el robot ya se movió y AMCL está localizado, agregar -p publicar_pose_inicial:=false
para no reiniciar AMCL en (x0, y0, yaw0).
"""
from collections import deque
import csv
import json
import math
import os
import re
import signal
import threading
import time

from ament_index_python.packages import get_package_share_directory
from geometry_msgs.msg import Point, PoseStamped
from lifecycle_msgs.msg import State
from lifecycle_msgs.srv import GetState
from nav2_msgs.action import NavigateToPose
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from nav_msgs.msg import Odometry
import rclpy
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from rclpy.signals import SignalHandlerOptions
from rclpy.time import Time
from std_msgs.msg import ColorRGBA, String
from std_srvs.srv import Trigger
from tf2_ros import Buffer, TransformException, TransformListener
from visualization_msgs.msg import Marker, MarkerArray
import yaml

RESULTADOS = {
    TaskResult.SUCCEEDED: 'LOGRADO',
    TaskResult.FAILED: 'FALLIDO',
    TaskResult.CANCELED: 'CANCELADO',
    TaskResult.UNKNOWN: 'DESCONOCIDO',
}
COLORES = {'pendiente': '#52514e', 'actual': '#2a78d6', 'logrado': '#1baf7a', 'fallido': '#eb6834'}


def yaw_de(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def angulo(a):
    return math.atan2(math.sin(a), math.cos(a))


def segundos(stamp):
    return stamp.sec + stamp.nanosec * 1e-9


def pose_stamped(frame, x, y, yaw, stamp=None):
    p = PoseStamped()
    p.header.frame_id = frame
    if stamp is not None:
        p.header.stamp = stamp
    p.pose.position.x = float(x)
    p.pose.position.y = float(y)
    p.pose.orientation.z = math.sin(yaw / 2.0)
    p.pose.orientation.w = math.cos(yaw / 2.0)
    return p


def color(hex_, alfa=1.0):
    c = ColorRGBA()
    c.r, c.g, c.b = (int(hex_[k:k + 2], 16) / 255.0 for k in (1, 3, 5))
    c.a = alfa
    return c


def cargar_mision(ruta):
    """Lee el YAML y devuelve {'nombre', 'frame', 'waypoints': [...]} ya validado."""
    with open(ruta, encoding='utf-8') as f:
        datos = yaml.safe_load(f) or {}
    m = datos.get('mision', datos) if isinstance(datos, dict) else None
    if not isinstance(m, dict) or not m.get('waypoints'):
        raise ValueError('el archivo no tiene mision.waypoints')
    puntos = []
    for i, w in enumerate(m['waypoints'], 1):
        try:
            puntos.append({
                'nombre': str(w.get('nombre', f'wp{i}')),
                'x': float(w['x']),
                'y': float(w['y']),
                'yaw_deg': float(w.get('yaw_deg', 0.0)),
                'espera_s': max(0.0, float(w.get('espera_s', 0.0))),
            })
        except (KeyError, TypeError, ValueError, AttributeError) as e:
            raise ValueError(f'waypoint {i} mal escrito ({e!r})') from e
    return {'nombre': str(m.get('nombre', 'mision')), 'frame': str(m.get('frame', 'map')),
            'waypoints': puntos}


def dif(a, b):
    return None if a is None or b is None else round(a - b, 3)


def txt(v, unidad):
    return '-' if v is None else f'{v:.2f} {unidad}'


class Recorrido:
    """Última pose de una fuente de odometría, distancia acumulada (suma de tramos) y
    las poses del último segundo, para emparejarlas por tiempo con la estimación de AMCL."""

    def __init__(self):
        self.pose = None
        self.distancia = 0.0
        self.historial = deque(maxlen=60)  # (t, x, y, yaw), ~1 s a 50 Hz
        self.lock = threading.Lock()

    def actualizar(self, m):
        p = m.pose.pose
        x, y = p.position.x, p.position.y
        if self.pose is not None:
            self.distancia += math.hypot(x - self.pose[0], y - self.pose[1])
        self.pose = (x, y, yaw_de(p.orientation))
        with self.lock:
            self.historial.append((segundos(m.header.stamp),) + self.pose)

    def pose_en(self, t):
        """Pose más cercana en el tiempo a t [s]; la última si no hay una a menos de 0,5 s."""
        with self.lock:
            hist = list(self.historial)
        if not hist:
            return self.pose
        cerca = min(hist, key=lambda r: abs(r[0] - t))
        return cerca[1:] if abs(cerca[0] - t) < 0.5 else self.pose


class Mision(Node):
    """Servicios, estado y mediciones. El BasicNavigator solo se usa desde el hilo de la misión."""

    def __init__(self):
        super().__init__('mision')
        por_defecto = os.path.join(get_package_share_directory('dif_bot'), 'config', 'waypoints.yaml')
        self.archivo = self.declare_parameter('waypoints_file', por_defecto).value
        self.salida = self.declare_parameter('salida', os.path.expanduser('~/proyecto_final_ws/resultados')).value
        self.publicar_pose = bool(self.declare_parameter('publicar_pose_inicial', True).value)
        self.x0 = float(self.declare_parameter('x0', 0.0).value)
        self.y0 = float(self.declare_parameter('y0', 0.0).value)
        self.yaw0 = float(self.declare_parameter('yaw0', 0.0).value)
        self.tiempo_max = float(self.declare_parameter('tiempo_max_s', 120.0).value)
        self.continuar_si_falla = bool(self.declare_parameter('continuar_si_falla', True).value)

        # Estado compartido entre los hilos.
        self.lock = threading.Lock()          # banderas, resultados y trayectoria
        self.lock_cierre = threading.Lock()   # evita guardar dos veces la misma misión
        self.listo = False                    # Nav2 activo y AMCL con pose
        self.nav2_activo = False
        self.en_mision = False
        self.evento_inicio = threading.Event()
        self.evento_cancelar = threading.Event()
        self.salir = threading.Event()
        self.mision = None
        self.resultados = None
        self.trayectoria = []
        self.estado_wp = []
        self.indice = 0
        self.t0 = None
        self.t0_pared = time.time()
        self.d0 = {'real': None, 'ekf': None}
        self.guardado = True
        self.estado = 'ESPERANDO_NAV2'

        grupo_srv = MutuallyExclusiveCallbackGroup()
        grupo_sub = MutuallyExclusiveCallbackGroup()
        grupo_tmr = MutuallyExclusiveCallbackGroup()
        latch = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                           reliability=ReliabilityPolicy.RELIABLE)

        self.pub_estado = self.create_publisher(String, 'estado_mision', 10)
        self.pub_marcas = self.create_publisher(MarkerArray, 'waypoints_mision', latch)
        self.create_service(Trigger, 'iniciar_mision', self.srv_iniciar, callback_group=grupo_srv)
        self.create_service(Trigger, 'cancelar_mision', self.srv_cancelar, callback_group=grupo_srv)

        self.recorridos = {'real': Recorrido(), 'ekf': Recorrido()}
        self.create_subscription(Odometry, '/ground_truth/odom', self.recorridos['real'].actualizar, 20,
                                 callback_group=grupo_sub)
        self.create_subscription(Odometry, '/odom_filtered', self.recorridos['ekf'].actualizar, 20,
                                 callback_group=grupo_sub)
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)

        # Estado de bt_navigator (lifecycle) para saber si Nav2 sigue activo.
        self.cli_bt = self.create_client(GetState, '/bt_navigator/get_state', callback_group=grupo_tmr)
        self.consulta_bt = None
        self.create_timer(1.0, self.cada_segundo, callback_group=grupo_tmr)
        self.create_timer(0.2, self.registrar, callback_group=grupo_tmr)

        try:
            self.mision = cargar_mision(self.archivo)
            self.estado_wp = ['pendiente'] * len(self.mision['waypoints'])
            self.publicar_marcas()
            self.get_logger().info(f"Waypoints: {self.archivo} ({len(self.mision['waypoints'])} puntos)")
        except (OSError, ValueError, yaml.YAMLError) as e:
            self.get_logger().error(f'No se pudo leer {self.archivo}: {e}')

    # ---------- utilidades ----------
    def ahora(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def distancias(self):
        return {k: (r.distancia if r.pose is not None else None) for k, r in self.recorridos.items()}

    def estimacion_amcl(self):
        """(t, (x, y, yaw)) del robot en map según AMCL, o None si todavía no hay TF.

        Se compone a mano como en evaluar_amcl.py: AMCL publica map -> odom con la marca
        de tiempo adelantada transform_tolerance y la consulta directa a base_footprint falla.
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

    def fijar_estado(self, texto, log=True):
        self.estado = texto
        self.pub_estado.publish(String(data=texto))
        if log:
            self.get_logger().info(texto)

    def marcar(self, i, estado):
        self.estado_wp[i] = estado
        self.publicar_marcas()

    def publicar_marcas(self):
        m = self.mision
        if not m:
            return
        arr = MarkerArray()
        arr.markers.append(Marker(action=Marker.DELETEALL))
        # frame_locked: RViz los vuelve a ubicar cuando el frame map aparece en TF.
        linea = Marker(ns='orden', id=0, type=Marker.LINE_STRIP, frame_locked=True)
        linea.header.frame_id = m['frame']
        linea.scale.x = 0.03
        linea.color = color(COLORES['pendiente'], 0.6)
        linea.points.append(Point(x=self.x0, y=self.y0, z=0.02))
        for i, w in enumerate(m['waypoints']):
            col = color(COLORES[self.estado_wp[i]])
            flecha = Marker(ns='waypoints', id=i, type=Marker.ARROW, color=col, frame_locked=True)
            flecha.header.frame_id = m['frame']
            flecha.pose = pose_stamped(m['frame'], w['x'], w['y'], math.radians(w['yaw_deg'])).pose
            flecha.scale.x, flecha.scale.y, flecha.scale.z = 0.45, 0.08, 0.08
            texto = Marker(ns='nombres', id=i, type=Marker.TEXT_VIEW_FACING, color=col, frame_locked=True)
            texto.header.frame_id = m['frame']
            texto.pose.position.x, texto.pose.position.y, texto.pose.position.z = w['x'], w['y'], 0.45
            texto.pose.orientation.w = 1.0
            texto.scale.z = 0.22
            texto.text = f"{i + 1}. {w['nombre']}"
            arr.markers += [flecha, texto]
            linea.points.append(Point(x=w['x'], y=w['y'], z=0.02))
        arr.markers.append(linea)
        self.pub_marcas.publish(arr)

    # ---------- callbacks (ejecutor de varios hilos) ----------
    def cada_segundo(self):
        self.pub_estado.publish(String(data=self.estado))
        if self.consulta_bt is not None and not self.consulta_bt.done():
            return
        if not self.cli_bt.service_is_ready():
            self.nav2_activo = False
            return
        self.consulta_bt = self.cli_bt.call_async(GetState.Request())
        self.consulta_bt.add_done_callback(self.respuesta_bt)

    def respuesta_bt(self, futuro):
        r = futuro.result()
        self.nav2_activo = r is not None and r.current_state.id == State.PRIMARY_STATE_ACTIVE

    def registrar(self):
        if not self.en_mision or self.t0 is None:
            return
        e = self.estimacion_amcl()
        if e is None:
            real, amcl = self.recorridos['real'].pose, None
        else:
            # Pose real del mismo instante que la estimación (girando a 1 rad/s, 20 ms ya son 1°).
            amcl = e[1]
            real = self.recorridos['real'].pose_en(e[0])
        fila = [round(self.ahora() - self.t0, 2)]
        fila += [round(v, 4) for v in real] if real else [None] * 3
        fila += [round(v, 4) for v in amcl] if amcl else [None] * 3
        fila.append(self.indice)
        with self.lock:
            self.trayectoria.append(fila)

    def srv_iniciar(self, _pedido, respuesta):
        with self.lock:
            if self.en_mision:
                respuesta.success = False
                respuesta.message = (f"Ya hay una misión en curso ('{self.mision['nombre']}', "
                                     f"punto {self.indice}/{len(self.mision['waypoints'])})")
                return respuesta
            if not self.listo:
                respuesta.success = False
                respuesta.message = 'Nav2 todavía no está listo (esperando bt_navigator y la pose de AMCL)'
                return respuesta
            if not self.nav2_activo:
                respuesta.success = False
                respuesta.message = 'bt_navigator no está activo'
                return respuesta
            try:
                # Se relee el YAML en cada arranque para poder cambiar los puntos sin reiniciar.
                self.mision = cargar_mision(self.archivo)
            except (OSError, ValueError, yaml.YAMLError) as e:
                respuesta.success = False
                respuesta.message = f'No se pudo leer {self.archivo}: {e}'
                return respuesta
            self.en_mision = True
            self.t0 = None
            self.evento_cancelar.clear()
            self.evento_inicio.set()
        n = len(self.mision['waypoints'])
        respuesta.success = True
        respuesta.message = f"Misión iniciada: '{self.mision['nombre']}' con {n} waypoints"
        self.get_logger().info(respuesta.message)
        return respuesta

    def srv_cancelar(self, _pedido, respuesta):
        if not self.en_mision:
            respuesta.success = False
            respuesta.message = 'No hay misión en curso'
        else:
            self.evento_cancelar.set()
            respuesta.success = True
            respuesta.message = 'Cancelación solicitada'
            self.get_logger().warn('Cancelación solicitada por servicio')
        return respuesta

    # ---------- hilo de la misión (único dueño del BasicNavigator) ----------
    def trabajador(self, nav):
        try:
            self.preparar(nav)
        except Exception as e:  # p. ej. se cerró ROS mientras esperaba a Nav2
            if not self.salir.is_set():
                self.get_logger().error(f'No se pudo preparar Nav2: {e!r}')
            return
        while not self.salir.is_set():
            if not self.evento_inicio.wait(timeout=0.5):
                continue
            self.evento_inicio.clear()
            try:
                self.ejecutar(nav)
            except Exception as e:  # p. ej. el contexto de ROS se cerró a mitad de una llamada
                if self.salir.is_set():
                    return
                self.get_logger().error(f'Error durante la misión: {e!r}')
                self.cerrar_mision('ERROR')
                with self.lock:
                    self.en_mision = False

    def preparar(self, nav):
        self.fijar_estado('ESPERANDO_NAV2: esperando bt_navigator y AMCL')
        if self.publicar_pose:
            pose = pose_stamped('map', self.x0, self.y0, self.yaw0, self.get_clock().now().to_msg())
            nav.setInitialPose(pose)
            # Con localizer='amcl' la librería republica la pose hasta recibir /amcl_pose.
            nav.waitUntilNav2Active(navigator='bt_navigator', localizer='amcl')
        else:
            # 'robot_localization' hace que solo espere a bt_navigator, sin publicar pose.
            nav.waitUntilNav2Active(navigator='bt_navigator', localizer='robot_localization')
            self.get_logger().info('Esperando /amcl_pose: fija la pose con "2D Pose Estimate" en RViz')
            while not nav.initial_pose_received and not self.salir.is_set():
                rclpy.spin_once(nav, timeout_sec=0.5)
        self.listo = True
        self.nav2_activo = True
        self.publicar_marcas()  # ya existe el frame map en TF
        self.fijar_estado('LISTA: llama al servicio /iniciar_mision')

    def ejecutar(self, nav):
        m = self.mision
        wps = m['waypoints']
        with self.lock:
            self.resultados = [{
                'indice': i + 1, 'nombre': w['nombre'], 'x': w['x'], 'y': w['y'],
                'yaw_deg': w['yaw_deg'], 'espera_s': w['espera_s'], 'resultado': 'NO_EJECUTADO',
                'tiempo_s': None, 'distancia_real_m': None, 'distancia_ekf_m': None,
                'recuperaciones': 0, 'error_pos_m': None, 'error_yaw_deg': None, 'error_amcl_m': None,
                'codigo_error': 0, 'mensaje_error': '',
            } for i, w in enumerate(wps)]
            self.trayectoria = []
            self.guardado = False
            self.indice = 0
            self.d0 = self.distancias()
            self.t0_pared = time.time()
            self.t0 = self.ahora()
        self.estado_wp = ['pendiente'] * len(wps)
        self.publicar_marcas()

        estado = 'COMPLETADA'
        for i, w in enumerate(wps):
            if self.evento_cancelar.is_set() or self.salir.is_set():
                estado = 'CANCELADA'
                break
            self.indice = i + 1
            resultado = self.ir_a(nav, i, w, m['frame'])
            if resultado == 'CANCELADO':
                estado = 'CANCELADA'
                break
            if resultado != 'LOGRADO':
                r = self.resultados[i]
                self.get_logger().warn(f"[{i + 1}/{len(wps)}] {w['nombre']}: {resultado} "
                                       f"(código {r['codigo_error']}) {r['mensaje_error']}")
                if not self.continuar_si_falla:
                    estado = 'ABORTADA'
                    break
                continue
            self.esperar_en(i, w)

        if self.salir.is_set():
            estado = 'INTERRUMPIDA'
        elif estado == 'COMPLETADA' and any(r['resultado'] != 'LOGRADO' for r in self.resultados):
            estado = 'COMPLETADA_CON_FALLAS'
        self.cerrar_mision(estado)

    def ir_a(self, nav, i, w, frame):
        r = self.resultados[i]
        etiqueta = f"[{i + 1}/{len(self.resultados)}] {w['nombre']}"
        yaw = math.radians(w['yaw_deg'])
        meta = pose_stamped(frame, w['x'], w['y'], yaw, self.get_clock().now().to_msg())
        self.marcar(i, 'actual')
        self.fijar_estado(f"NAVEGANDO {etiqueta} -> ({w['x']:.2f}, {w['y']:.2f}, {w['yaw_deg']:.0f}°)")
        t_ini, d_ini = self.ahora(), self.distancias()

        nav.feedback = None  # la librería conserva el feedback de la meta anterior
        try:
            tarea = nav.goToPose(meta)
        except AttributeError:
            # En Kilted, si bt_navigator rechaza la meta, goToPose falla al usar
            # NavigateToPose.UNKNOWN (la constante está en NavigateToPose.Result).
            tarea = None
            nav.setTaskError(NavigateToPose.Result.UNKNOWN, 'bt_navigator rechazó la meta')
        if tarea is None:
            r['resultado'] = 'RECHAZADO'
            r['codigo_error'], r['mensaje_error'] = nav.getTaskError()
        else:
            r['resultado'] = self.esperar_tarea(nav, tarea, etiqueta, t_ini, r)
            if r['resultado'] == 'FALLIDO':
                r['codigo_error'], r['mensaje_error'] = nav.getTaskError()

        d_fin = self.distancias()
        r['tiempo_s'] = round(self.ahora() - t_ini, 2)
        r['distancia_real_m'] = dif(d_fin['real'], d_ini['real'])
        r['distancia_ekf_m'] = dif(d_fin['ekf'], d_ini['ekf'])
        real, e = self.recorridos['real'].pose, self.estimacion_amcl()
        if real:
            r['error_pos_m'] = round(math.hypot(real[0] - w['x'], real[1] - w['y']), 3)
            r['error_yaw_deg'] = round(math.degrees(angulo(real[2] - yaw)), 2)
            if e is not None:
                amcl, real_e = e[1], self.recorridos['real'].pose_en(e[0])
                r['error_amcl_m'] = round(math.hypot(amcl[0] - real_e[0], amcl[1] - real_e[1]), 3)
        self.marcar(i, 'logrado' if r['resultado'] == 'LOGRADO' else 'fallido')
        self.get_logger().info(f"{etiqueta}: {r['resultado']} en {r['tiempo_s']:.1f} s, "
                               f"error {txt(r['error_pos_m'], 'm')}")
        return r['resultado']

    def esperar_tarea(self, nav, tarea, etiqueta, t_ini, r):
        motivo = None      # por qué se pidió cancelar: CANCELADO o TIEMPO_AGOTADO
        t_cancel = None
        ultimo_estado = ultimo_log = 0.0
        while not nav.isTaskComplete(task=tarea):
            t = self.ahora() - t_ini
            fb = nav.getFeedback(task=tarea)
            pared = time.monotonic()
            if fb is not None:
                r['recuperaciones'] = int(fb.number_of_recoveries)
            if fb is not None and pared - ultimo_estado >= 1.0:
                log = pared - ultimo_log >= 3.0
                ultimo_estado = pared
                ultimo_log = pared if log else ultimo_log
                self.fijar_estado(f'NAVEGANDO {etiqueta}: faltan {fb.distance_remaining:.1f} m, '
                                  f'{t:.0f} s, recuperaciones {fb.number_of_recoveries}', log=log)
            if motivo is None:
                if self.evento_cancelar.is_set() or self.salir.is_set():
                    motivo = 'CANCELADO'
                elif t > self.tiempo_max:
                    motivo = 'TIEMPO_AGOTADO'
                    self.get_logger().warn(f'{etiqueta}: pasaron {self.tiempo_max:.0f} s, cancelo la meta')
                if motivo:
                    nav.cancelTask()
                    t_cancel = time.monotonic()
            elif time.monotonic() - t_cancel > (2.0 if self.salir.is_set() else 10.0):
                self.get_logger().warn(f'{etiqueta}: Nav2 no confirmó la cancelación')
                return motivo
        resultado = RESULTADOS.get(nav.getResult(), 'DESCONOCIDO')
        if motivo == 'TIEMPO_AGOTADO' and resultado == 'CANCELADO':
            return 'TIEMPO_AGOTADO'
        return resultado

    def esperar_en(self, i, w):
        if w['espera_s'] <= 0:
            return
        self.fijar_estado(f"EN [{i + 1}/{len(self.resultados)}] {w['nombre']}: "
                          f"espera de {w['espera_s']:.0f} s")
        fin = self.ahora() + w['espera_s']  # tiempo simulado
        while self.ahora() < fin and not (self.evento_cancelar.is_set() or self.salir.is_set()):
            time.sleep(0.05)

    def cerrar_mision(self, estado):
        """Guarda JSON + CSV y deja libre el servicio. Se llama una sola vez por misión."""
        with self.lock_cierre:
            with self.lock:
                if self.guardado or self.resultados is None:
                    return
                self.guardado = True
                resultados = [dict(r) for r in self.resultados]
                trayectoria = list(self.trayectoria)
            if estado == 'INTERRUMPIDA' and 0 < self.indice <= len(resultados):
                actual = resultados[self.indice - 1]
                if actual['resultado'] == 'NO_EJECUTADO':
                    actual['resultado'] = 'INTERRUMPIDO'

            m = self.mision
            t_total = self.ahora() - self.t0 if self.t0 is not None else 0.0
            d = self.distancias()
            d_real, d_ekf = dif(d['real'], self.d0['real']), dif(d['ekf'], self.d0['ekf'])
            d_ref = d_real if d_real is not None else d_ekf
            logrados = sum(r['resultado'] == 'LOGRADO' for r in resultados)

            nombre = re.sub(r'[^A-Za-z0-9_-]+', '_', m['nombre'])
            base = os.path.join(self.salida, f"mision_{nombre}_{time.strftime('%Y%m%d_%H%M%S')}")
            res = {
                'mision': m['nombre'],
                'archivo_waypoints': self.archivo,
                'inicio': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.t0_pared)),
                'estado_final': estado,
                'waypoints_logrados': logrados,
                'waypoints_total': len(resultados),
                'tiempo_total_s': round(t_total, 2),
                'tiempo_total_pared_s': round(time.time() - self.t0_pared, 2),
                'distancia_real_m': d_real,
                'distancia_ekf_m': d_ekf,
                'velocidad_media_m_s': round(d_ref / t_total, 3) if d_ref and t_total > 0 else None,
                'pose_inicial': {'x': self.x0, 'y': self.y0, 'yaw_rad': self.yaw0,
                                 'publicada': self.publicar_pose},
                'tiempo_max_s': self.tiempo_max,
                'continuar_si_falla': self.continuar_si_falla,
                'trayectoria_csv': base + '_trayectoria.csv',
                'waypoints': resultados,
            }
            try:
                os.makedirs(self.salida, exist_ok=True)
                with open(base + '_trayectoria.csv', 'w', newline='', encoding='utf-8') as f:
                    w = csv.writer(f)
                    w.writerow(['t', 'x_real', 'y_real', 'yaw_real', 'x_amcl', 'y_amcl', 'yaw_amcl', 'waypoint'])
                    w.writerows(trayectoria)
                with open(base + '.json', 'w', encoding='utf-8') as f:
                    json.dump(res, f, indent=2, ensure_ascii=False)
                guardado_en = f'Guardado en {base}.json'
            except OSError as e:
                guardado_en = f'No se pudo guardar en {self.salida}: {e}'

            lineas = [f"Misión '{m['nombre']}' {estado}: {logrados}/{len(resultados)} waypoints, "
                      f"{t_total:.1f} s simulados, {txt(d_ref, 'm')} recorridos"]
            for r in resultados:
                dist = r['distancia_real_m'] if r['distancia_real_m'] is not None else r['distancia_ekf_m']
                lineas.append(f"  {r['indice']}. {r['nombre']:<14} {r['resultado']:<14} "
                              f"{txt(r['tiempo_s'], 's'):>9} {txt(dist, 'm'):>8}  "
                              f"error {txt(r['error_pos_m'], 'm')}")
            lineas.append(guardado_en)
            self.get_logger().info('\n'.join(lineas))

            with self.lock:
                self.en_mision = False
            self.fijar_estado(f"{estado}: {logrados}/{len(resultados)} waypoints en {t_total:.1f} s, "
                              f"{txt(d_ref, 'm')}", log=False)


def _sigterm(_signum, _frame):
    raise KeyboardInterrupt


def main():
    # Sin los manejadores de rclpy: Ctrl+C llega como KeyboardInterrupt y así se alcanza
    # a cancelar la meta en Nav2 y a guardar el resultado antes de cerrar ROS.
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    signal.signal(signal.SIGTERM, _sigterm)
    mision = Mision()
    nav = BasicNavigator(node_name='mision_navegador')
    nav.set_parameters([Parameter('use_sim_time', Parameter.Type.BOOL,
                                  mision.get_parameter('use_sim_time').value)])

    # El nodo de servicios gira en su propio ejecutor; el BasicNavigator se gira solo
    # (spin_until_future_complete) desde el hilo de la misión.
    ejecutor = MultiThreadedExecutor(num_threads=4)
    ejecutor.add_node(mision)
    threading.Thread(target=ejecutor.spin, daemon=True).start()
    hilo_mision = threading.Thread(target=mision.trabajador, args=(nav,), daemon=True)
    hilo_mision.start()

    try:
        while not mision.salir.wait(0.5):
            pass
    except KeyboardInterrupt:
        # ros2 launch manda un segundo SIGINT; se ignora para terminar el cierre.
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        mision.get_logger().info('Ctrl+C: cerrando la misión')
    finally:
        mision.salir.set()
        hilo_mision.join(timeout=3.0)
        if mision.en_mision:
            mision.cerrar_mision('INTERRUMPIDA')
        ejecutor.shutdown(timeout_sec=1.0)
        if not hilo_mision.is_alive():
            nav.destroy_node()
        mision.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
