#!/usr/bin/env python3
"""Práctica 5: prueba de navegación con Nav2 (metas una tras otra).

Fija la pose inicial de AMCL, espera a que Nav2 esté activo y manda las metas con
nav2_simple_commander. De cada meta guarda: resultado, tiempo, recuperaciones del BT
(y cuáles: spin, backup, wait), largo del primer plan global, distancia recorrida y
error final. Distancia y error salen de la pose real de Gazebo (/ground_truth/odom);
su marco world coincide con map porque el mapa se hizo arrancando en el origen.
Por eso la pose inicial de AMCL también se toma de ahí: sirve aunque el robot no
arranque en el origen o se repita la prueba sin relanzar.

Caja en Gazebo durante la meta `meta_obstaculo` (la 2), cuando el robot ya va en camino:
  obstaculo:=true      caja de 0,5 x 0,5 x 0,6 m sobre el plan, con paso libre a los lados.
                       Mide cuánto tarda el plan global en rodearla desde que existe.
  bloquear_meta:=true  caja de lado_bloqueo (1 m) encima de la meta. No queda ningún punto
                       libre dentro de la tolerancia del planner (0,5 m), así que la meta
                       es inalcanzable y el BT recorre sus recuperaciones hasta rendirse.
En Kilted el BT solo recupera si el error del planner o del controlador es de los que
una recuperación puede arreglar (WouldAPlannerRecoveryHelp / WouldAControllerRecoveryHelp).
La caja sobre el plan casi nunca llega a eso (se replanifica antes); la de la meta sí.

Uso (con navegacion.launch.py corriendo; relanzarla entre corridas para quitar la caja):
  ros2 run dif_bot probar_nav.py
  ros2 run dif_bot probar_nav.py --ros-args -p obstaculo:=true
  ros2 run dif_bot probar_nav.py --ros-args -p bloquear_meta:=true
  ros2 run dif_bot probar_nav.py --ros-args -p metas:="[3.5, -2.0, 0.0, -4.0, 0.25, 3.14]"
  ros2 run dif_bot probar_nav.py --ros-args -p pose_inicial_real:=false -p x0:=-4.0 -p y0:=0.25 -p yaw0:=3.14
Guarda p5_<etiqueta>.json y p5_<etiqueta>.csv en ~/proyecto_final_ws/resultados
(etiqueta por defecto: sin_obstaculo, con_obstaculo o meta_bloqueada).
"""
import csv
import json
import math
import os
import subprocess
import time
import xml.etree.ElementTree as ET

import rclpy
from action_msgs.msg import GoalStatusArray
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from nav_msgs.msg import Odometry, Path
from rclpy.executors import ExternalShutdownException
from rclpy.parameter import Parameter

# x, y, yaw de cada meta: cuarto sureste, zona oeste y cuarto noroeste.
# Todas a más de 0,5 m de cualquier obstáculo de worlds/bodega.sdf.
METAS = [3.5, -2.0, 0.0,
         -4.0, 0.25, 3.14,
         -2.3, 2.9, 1.57]

# Acciones del behavior_server que el BT usa como recuperación.
RECUPERACIONES = ['spin', 'backup', 'wait', 'drive_on_heading']

LADO_CAJA = 0.5      # caja sobre el plan
LADO_BLOQUEO = 1.0   # caja sobre la meta: con 0,5 m de tolerancia del planner no queda hueco
ALTO_CAJA = 0.6
SDF_CAJA = """<?xml version="1.0"?>
<sdf version="1.9">
  <model name="{nombre}">
    <static>true</static>
    <link name="link">
      <pose>0 0 {z} 0 0 0</pose>
      <collision name="c"><geometry><box><size>{l} {l} {h}</size></box></geometry></collision>
      <visual name="v"><geometry><box><size>{l} {l} {h}</size></box></geometry>
        <material><ambient>0.85 0.2 0.2 1</ambient><diffuse>0.85 0.2 0.2 1</diffuse></material>
      </visual>
    </link>
  </model>
</sdf>"""

NOMBRES_RESULTADO = {
    TaskResult.SUCCEEDED: 'exito',
    TaskResult.FAILED: 'fallo',
    TaskResult.CANCELED: 'cancelada',
    TaskResult.UNKNOWN: 'desconocido',
}


def yaw_de(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def angulo(a):
    return math.atan2(math.sin(a), math.cos(a))


def largo(puntos):
    return sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(puntos, puntos[1:]))


def submuestrear(puntos, paso=0.1):
    """Deja un punto cada `paso` metros (para no llenar el JSON)."""
    if not puntos:
        return []
    salida = [puntos[0]]
    for p in puntos[1:]:
        if math.hypot(p[0] - salida[-1][0], p[1] - salida[-1][1]) >= paso:
            salida.append(p)
    if salida[-1] != puntos[-1]:
        salida.append(puntos[-1])
    return [[round(x, 3), round(y, 3)] for x, y in salida]


class Bodega:
    """Obstáculos fijos del modelo 'estructura' de bodega.sdf, para medir holguras."""

    def __init__(self, ruta_sdf):
        self.cajas = []      # (cx, cy, yaw, media_x, media_y)
        self.cilindros = []  # (cx, cy, radio)
        raiz = ET.parse(ruta_sdf).getroot()
        for modelo in raiz.iter('model'):
            if modelo.get('name') != 'estructura':
                continue
            for link in modelo.iter('link'):
                pose = [float(v) for v in (link.findtext('pose') or '0 0 0 0 0 0').split()]
                geo = link.find('collision/geometry')
                if geo is None:
                    continue
                if geo.find('box') is not None:
                    sx, sy, _ = [float(v) for v in geo.findtext('box/size').split()]
                    self.cajas.append((pose[0], pose[1], pose[5], sx / 2, sy / 2))
                elif geo.find('cylinder') is not None:
                    self.cilindros.append((pose[0], pose[1], float(geo.findtext('cylinder/radius'))))

    def holgura(self, x, y):
        """Distancia al obstáculo fijo más cercano (negativa si el punto está dentro)."""
        d = math.inf
        for cx, cy, yaw, mx, my in self.cajas:
            c, s = math.cos(yaw), math.sin(yaw)
            dx, dy = x - cx, y - cy
            ex, ey = abs(c * dx + s * dy) - mx, abs(-s * dx + c * dy) - my
            d = min(d, math.hypot(max(ex, 0.0), max(ey, 0.0)) if max(ex, ey) > 0 else max(ex, ey))
        for cx, cy, r in self.cilindros:
            d = min(d, math.hypot(x - cx, y - cy) - r)
        return d


def cargar_bodega(ruta):
    if not ruta:
        try:
            from ament_index_python.packages import get_package_share_directory
            ruta = os.path.join(get_package_share_directory('dif_bot'), 'worlds', 'bodega.sdf')
        except Exception:
            return None
    return Bodega(ruta) if os.path.isfile(ruta) else None


class ProbarNav(BasicNavigator):
    def __init__(self):
        super().__init__('probar_nav')
        self.set_parameters([Parameter('use_sim_time', Parameter.Type.BOOL, True)])
        self.x0 = float(self.declare_parameter('x0', 0.0).value)
        self.y0 = float(self.declare_parameter('y0', 0.0).value)
        self.yaw0 = float(self.declare_parameter('yaw0', 0.0).value)
        # Por defecto la pose real de Gazebo; x0, y0, yaw0 solo con pose_inicial_real:=false
        # o si /ground_truth/odom no llega.
        self.pose_inicial_real = bool(self.declare_parameter('pose_inicial_real', True).value)
        valores = [float(v) for v in self.declare_parameter('metas', METAS).value]
        self.metas = [tuple(valores[i:i + 3]) for i in range(0, len(valores) - 2, 3)]
        self.obstaculo = bool(self.declare_parameter('obstaculo', False).value)
        self.bloquear_meta = bool(self.declare_parameter('bloquear_meta', False).value)
        self.lado_bloqueo = float(self.declare_parameter('lado_bloqueo', LADO_BLOQUEO).value)
        self.modo_caja = 'meta' if self.bloquear_meta else ('camino' if self.obstaculo else None)
        self.meta_obstaculo = int(self.declare_parameter('meta_obstaculo', 2).value)
        self.mundo_gz = self.declare_parameter('mundo_gz', 'bodega').value
        self.timeout = float(self.declare_parameter('timeout', 240.0).value)
        etiqueta = self.declare_parameter('etiqueta', '').value
        por_defecto = {'meta': 'meta_bloqueada', 'camino': 'con_obstaculo', None: 'sin_obstaculo'}
        self.etiqueta = etiqueta or por_defecto[self.modo_caja]
        self.salida = self.declare_parameter(
            'salida', os.path.expanduser('~/proyecto_final_ws/resultados')).value
        self.bodega = cargar_bodega(self.declare_parameter('mundo_sdf', '').value)

        self.real = None          # pose real (x, y, yaw)
        self.tramo = None         # datos de la meta en curso
        self.ultimo = None        # último punto guardado del recorrido
        self.ultimo_plan = None   # puntos del último /plan
        self.filas = []           # recorrido: meta, t, x, y
        self.resultados = []
        self.eventos = []
        self.caja = None
        self.proceso_caja = None
        self.vistos = set()       # goals de recuperación ya contados
        self.t0 = None

        self.create_subscription(Odometry, '/ground_truth/odom', self.cb_real, 50)
        self.create_subscription(Path, '/plan', self.cb_plan, 10)
        for nombre in RECUPERACIONES:
            self.create_subscription(GoalStatusArray, f'/{nombre}/_action/status',
                                     lambda m, n=nombre: self.cb_recuperacion(n, m), 10)

    # ---------- utilidades ----------
    def ahora(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def pose(self, x, y, yaw):
        p = PoseStamped()
        p.header.frame_id = 'map'
        p.header.stamp = self.get_clock().now().to_msg()
        p.pose.position.x, p.pose.position.y = float(x), float(y)
        p.pose.orientation.z, p.pose.orientation.w = math.sin(yaw / 2), math.cos(yaw / 2)
        return p

    def esperar(self, segundos):
        fin = time.monotonic() + segundos
        while time.monotonic() < fin:
            rclpy.spin_once(self, timeout_sec=0.1)

    def evento(self, texto):
        t = round(self.ahora() - self.t0, 2) if self.t0 is not None else 0.0
        e = {'t': t, 'meta': self.tramo['meta'] if self.tramo else None, 'evento': texto}
        if self.real is not None:
            e['x'], e['y'] = round(self.real[0], 3), round(self.real[1], 3)
        self.eventos.append(e)
        self.info(f'[t={t:.1f} s] {texto}')

    # ---------- callbacks ----------
    def cb_real(self, m):
        p = m.pose.pose
        self.real = (p.position.x, p.position.y, yaw_de(p.orientation))
        if self.tramo is None:
            return
        x, y = self.real[0], self.real[1]
        if self.ultimo is not None:
            paso = math.hypot(x - self.ultimo[0], y - self.ultimo[1])
            if paso < 0.01:  # se suma cada centímetro para no integrar ruido de reposo
                return
            self.tramo['recorrido'] += paso
        self.ultimo = (x, y)
        self.filas.append([self.tramo['meta'], round(self.ahora() - self.t0, 3), round(x, 4), round(y, 4)])

    def cb_plan(self, m):
        if self.tramo is None or not m.poses:
            return
        puntos = [(p.pose.position.x, p.pose.position.y) for p in m.poses]
        self.ultimo_plan = puntos
        t = self.ahora() - self.tramo['t0']
        self.tramo['planes'].append([round(t, 2), round(largo(puntos), 3)])
        # Primer plan que ya rodea la caja (pasa a más de media caja + medio robot).
        # Se cuenta desde que la caja existe en Gazebo, no desde que se pidió crearla.
        caja = self.caja
        if (caja and caja.get('tipo') == 'camino' and caja['creada'] is True
                and caja['meta'] == self.tramo['meta'] and caja['esquiva_s'] is None):
            d = min(math.hypot(x - caja['x'], y - caja['y']) for x, y in puntos)
            if d > LADO_CAJA / 2 + 0.20:
                caja['esquiva_s'] = round(self.ahora() - caja['t_creada'], 2)
                self.evento(f'el plan global ya rodea la caja ({caja["esquiva_s"]} s después de aparecer '
                            f'en Gazebo, plan de {largo(puntos):.2f} m)')

    def cb_recuperacion(self, nombre, m):
        for estado in m.status_list:
            uid = tuple(int(b) for b in estado.goal_info.goal_id.uuid)
            if uid in self.vistos:
                continue
            self.vistos.add(uid)
            if self.tramo is not None:
                cuenta = self.tramo['comportamientos']
                cuenta[nombre] = cuenta.get(nombre, 0) + 1
                self.evento(f'recuperación: {nombre}')

    # ---------- obstáculo ----------
    def elegir_punto(self, puntos):
        """Punto del plan a 1,3 m o más del robot, lejos de la meta y con espacio para rodearlo."""
        rx, ry = self.real[0], self.real[1]
        avance = [0.0]
        for a, b in zip(puntos, puntos[1:]):
            avance.append(avance[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
        total = avance[-1]
        mejor = None
        for (x, y), s in zip(puntos, avance):
            if s < 1.3 or s > total - 1.5 or math.hypot(x - rx, y - ry) < 1.2:
                continue
            h = self.bodega.holgura(x, y) if self.bodega else 1.2
            if h >= 1.2:  # queda paso de sobra a ambos lados de la caja
                return x, y, h
            if mejor is None or h > mejor[2]:
                mejor = (x, y, h)
        return mejor if mejor and mejor[2] >= 0.8 else None

    def revisar_obstaculo(self, k, inicio, meta):
        if self.modo_caja is None or k != self.meta_obstaculo:
            return
        if self.caja is None:
            if self.real is None or inicio is None:
                return
            if math.hypot(self.real[0] - inicio[0], self.real[1] - inicio[1]) < 0.5:
                return  # se espera a que el robot ya vaya en camino
            if self.modo_caja == 'meta':
                # Lejos del robot para no aparecer encima de él.
                lado = self.lado_bloqueo
                lejos = math.hypot(meta[0] - self.real[0], meta[1] - self.real[1]) >= lado / 2 + 1.5
                punto = (meta[0], meta[1], None) if lejos else None
                motivo = 'el robot ya está muy cerca de la meta'
            else:
                if self.ultimo_plan is None:
                    return
                lado = LADO_CAJA
                punto = self.elegir_punto(self.ultimo_plan)
                motivo = 'no hay sitio libre en el plan'
            if punto is None:
                self.caja = {'meta': k, 'tipo': self.modo_caja, 'creada': False, 'detalle': motivo}
                self.evento(f'no se puso la caja: {motivo}')
                return
            self.poner_caja(k, *punto, lado)
        elif self.proceso_caja is not None and self.proceso_caja.poll() is not None:
            self.cerrar_proceso_caja()

    def poner_caja(self, k, x, y, h, lado):
        nombre = f'caja_p5_{int(time.time())}'
        sdf = SDF_CAJA.format(nombre=nombre, l=lado, h=ALTO_CAJA, z=ALTO_CAJA / 2)
        cmd = ['ros2', 'run', 'ros_gz_sim', 'create', '-world', self.mundo_gz, '-name', nombre,
               '-string', sdf, '-x', f'{x:.3f}', '-y', f'{y:.3f}', '-z', '0.0']
        self.proceso_caja = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                             stderr=subprocess.STDOUT, text=True)
        self.caja = {'meta': k, 'tipo': self.modo_caja, 'nombre': nombre,
                     'x': round(x, 3), 'y': round(y, 3), 'lado': lado, 'alto': ALTO_CAJA,
                     'holgura_m': None if h is None else round(h, 2),
                     't': self.ahora(), 't_s': round(self.ahora() - self.t0, 2),
                     'robot': [round(self.real[0], 3), round(self.real[1], 3)],
                     'largo_plan_antes_m': round(largo(self.ultimo_plan), 3) if self.ultimo_plan else None,
                     'creada': None, 'creacion_s': None, 'esquiva_s': None}
        donde = 'encima de la meta' if self.modo_caja == 'meta' else 'sobre el plan'
        self.evento(f'caja de {lado:.2f} m en ({x:.2f}, {y:.2f}) {donde}, robot a '
                    f'{math.hypot(x - self.real[0], y - self.real[1]):.2f} m')

    def cerrar_proceso_caja(self, espera=None):
        proc, self.proceso_caja = self.proceso_caja, None
        try:
            texto, _ = proc.communicate(timeout=espera)
        except subprocess.TimeoutExpired:
            proc.kill()
            texto, _ = proc.communicate()
        lineas = [ln for ln in (texto or '').splitlines() if ln.strip()]
        self.caja['creada'] = proc.returncode == 0
        self.caja['detalle'] = lineas[-1] if lineas else ''
        if self.caja['creada']:
            # create sale apenas Gazebo acepta la caja: desde aquí ya existe en el mundo.
            # creacion_s es lo que tardó el comando (arranque de ros2 run + servicio de gz).
            self.caja['t_creada'] = self.ahora()
            self.caja['creacion_s'] = round(self.caja['t_creada'] - self.caja['t'], 2)
        tardo = f' a los {self.caja["creacion_s"]} s' if self.caja['creada'] else ''
        self.evento(f'ros_gz_sim create terminó{tardo} (código {proc.returncode}): {self.caja["detalle"]}')

    # ---------- prueba ----------
    def tomar_pose_real(self):
        if self.pose_inicial_real and self.real is not None:
            self.x0, self.y0, self.yaw0 = self.real

    def correr(self):
        if self.pose_inicial_real:
            fin = time.monotonic() + 20.0
            while self.real is None and time.monotonic() < fin:
                rclpy.spin_once(self, timeout_sec=0.1)
            if self.real is None:
                self.warn(f'No llega /ground_truth/odom: AMCL arranca en x0, y0, yaw0 = '
                          f'{self.x0}, {self.y0}, {self.yaw0}.')
        self.tomar_pose_real()
        self.setInitialPose(self.pose(self.x0, self.y0, self.yaw0))
        self.waitUntilNav2Active(localizer='amcl')
        # Si AMCL ya tenía pose (la del launch), el envío anterior pudo perderse: se repite.
        self.tomar_pose_real()
        self.setInitialPose(self.pose(self.x0, self.y0, self.yaw0))
        self.esperar(2.0)
        if self.real is None:
            self.warn('No llega /ground_truth/odom: no se podrá medir recorrido ni error.')
        self.t0 = self.ahora()

        for k, (x, y, yaw) in enumerate(self.metas, start=1):
            if self.bodega is not None:
                h = self.bodega.holgura(x, y)
                if h < 0.5:
                    self.warn(f'Meta {k} ({x}, {y}) está a {h:.2f} m de un obstáculo (< 0,5 m).')
            self.navegar(k, x, y, yaw)

    def navegar(self, k, x, y, yaw):
        meta = self.pose(x, y, yaw)
        self.tramo = {'meta': k, 't0': self.ahora(), 'recorrido': 0.0, 'planes': [],
                      'comportamientos': {}}
        self.ultimo = None
        self.ultimo_plan = None
        inicio = self.real

        # Primer plan global, pedido al planner antes de mandar la meta.
        camino = self.getPath(PoseStamped(), meta)
        plan = [(p.pose.position.x, p.pose.position.y) for p in camino.poses] if camino else []

        self.feedback = None
        tarea = self.goToPose(meta)
        recuperaciones, cancelada = 0, False
        t_inicio = self.ahora()
        if tarea is not None:
            while not self.isTaskComplete(tarea):
                fb = self.getFeedback()
                if fb is not None and fb.number_of_recoveries > recuperaciones:
                    recuperaciones = fb.number_of_recoveries
                    self.evento(f'el BT lleva {recuperaciones} recuperación(es)')
                self.revisar_obstaculo(k, inicio, (x, y))
                if not cancelada and self.ahora() - t_inicio > self.timeout:
                    self.evento(f'meta {k}: tiempo agotado ({self.timeout:.0f} s), se cancela')
                    self.cancelTask()
                    cancelada = True
            resultado = 'tiempo_agotado' if cancelada else NOMBRES_RESULTADO[self.getResult()]
        else:
            resultado = 'rechazada'
        tiempo = self.ahora() - t_inicio
        codigo, mensaje = self.getTaskError()

        self.esperar(0.5)  # que el robot termine de frenar
        if self.proceso_caja is not None:
            self.cerrar_proceso_caja(espera=15.0)

        fila = {
            'meta': k, 'x': x, 'y': y, 'yaw': yaw,
            'holgura_m': round(self.bodega.holgura(x, y), 2) if self.bodega else None,
            'resultado': resultado,
            'codigo_error': int(codigo), 'mensaje_error': mensaje,
            'tiempo_s': round(tiempo, 2),
            'recuperaciones': recuperaciones,
            'comportamientos': self.tramo['comportamientos'],
            'largo_plan_m': round(largo(plan), 3) if plan else (
                self.tramo['planes'][0][1] if self.tramo['planes'] else None),
            'distancia_recorrida_m': round(self.tramo['recorrido'], 3),
            'plan_inicial': submuestrear(plan),
            'planes': self.tramo['planes'],
        }
        if self.real is not None:
            fila['pose_final'] = [round(v, 3) for v in self.real]
            fila['error_final_m'] = round(math.hypot(self.real[0] - x, self.real[1] - y), 3)
            fila['error_yaw_deg'] = round(abs(math.degrees(angulo(self.real[2] - yaw))), 2)
        self.resultados.append(fila)
        self.info(f'Meta {k}: {resultado} en {tiempo:.1f} s, recorrido {fila["distancia_recorrida_m"]:.2f} m, '
                  f'plan {fila["largo_plan_m"]} m, recuperaciones {recuperaciones}, '
                  f'error {fila.get("error_final_m")} m')
        self.tramo = None

    def reportar(self):
        os.makedirs(self.salida, exist_ok=True)
        base = os.path.join(self.salida, f'p5_{self.etiqueta}')
        with open(base + '.csv', 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['meta', 't', 'x', 'y'])
            w.writerows(self.filas)

        caja = dict(self.caja) if self.caja else None
        if caja:
            caja.pop('t', None)
            caja.pop('t_creada', None)
        hechas = self.resultados
        comportamientos = {}
        for r in hechas:
            for nombre, n in r['comportamientos'].items():
                comportamientos[nombre] = comportamientos.get(nombre, 0) + n
        res = {
            'etiqueta': self.etiqueta,
            'obstaculo': self.obstaculo,
            'bloquear_meta': self.bloquear_meta,
            'pose_inicial': [round(v, 3) for v in (self.x0, self.y0, self.yaw0)],
            'metas': hechas,
            'caja': caja,
            'eventos': self.eventos,
            'totales': {
                'exitos': sum(r['resultado'] == 'exito' for r in hechas),
                'metas': len(hechas),
                'tiempo_s': round(sum(r['tiempo_s'] for r in hechas), 2),
                'distancia_m': round(sum(r['distancia_recorrida_m'] for r in hechas), 3),
                'recuperaciones': sum(r['recuperaciones'] for r in hechas),
                'comportamientos': comportamientos,
            },
        }
        with open(base + '.json', 'w', encoding='utf-8') as f:
            json.dump(res, f, indent=2, ensure_ascii=False)

        print(f'\nResumen ({self.etiqueta}):')
        for r in hechas:
            print(f"  meta {r['meta']}: {r['resultado']:<14} {r['tiempo_s']:7.1f} s  "
                  f"plan {r['largo_plan_m'] or 0:5.2f} m  recorrido {r['distancia_recorrida_m']:5.2f} m  "
                  f"error {r.get('error_final_m', float('nan')):.3f} m  recuperaciones {r['recuperaciones']}")
        if comportamientos:
            print('  comportamientos: ' + ', '.join(f'{n} x{c}' for n, c in comportamientos.items()))
        if caja:
            print(f"  caja ({caja.get('tipo')}): {caja.get('x')}, {caja.get('y')}  creada={caja.get('creada')} "
                  f"en {caja.get('creacion_s')} s  plan la rodea a los {caja.get('esquiva_s')} s de aparecer")
        print(f'Guardado en {base}.json / .csv')


def main():
    rclpy.init()
    nodo = ProbarNav()
    try:
        nodo.correr()
    except (KeyboardInterrupt, ExternalShutdownException):
        print('Interrumpido: se guarda lo que alcanzó a medirse.')
    finally:
        if nodo.proceso_caja is not None:
            nodo.proceso_caja.kill()
        if nodo.resultados:  # no pisa resultados anteriores si no se midió nada
            nodo.reportar()
        nodo.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
