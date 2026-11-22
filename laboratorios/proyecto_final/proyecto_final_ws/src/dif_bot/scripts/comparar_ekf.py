#!/usr/bin/env python3
"""Práctica 2: compara la odometría de las ruedas, el EKF y la pose real.

Hace un cuadrado (rectas y giros en el sitio) en lazo abierto y guarda, a 50 Hz,
la pose de las tres fuentes expresada desde donde arrancó el robot:
  /diff_drive_controller/odom  -> odometría de las ruedas
  /odom_filtered               -> salida del EKF
  /ground_truth/odom           -> pose real de Gazebo

Uso (con ekf.launch.py corriendo):
  ros2 run dif_bot comparar_ekf.py --ros-args -p use_sim_time:=true -p etiqueta:=con_imu
"""
import csv
import json
import math
import os

import rclpy
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node


def yaw_de(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


def angulo(a):
    return math.atan2(math.sin(a), math.cos(a))


class Pose:
    """Última pose de una fuente y su pose inicial para medir desde el arranque."""

    def __init__(self):
        self.actual = None
        self.inicio = None

    def relativa(self):
        x, y, th = self.actual
        x0, y0, th0 = self.inicio
        dx, dy = x - x0, y - y0
        c, s = math.cos(-th0), math.sin(-th0)
        return c * dx - s * dy, s * dx + c * dy, angulo(th - th0)


class CompararEkf(Node):
    def __init__(self):
        super().__init__('comparar_ekf')
        self.etiqueta = self.declare_parameter('etiqueta', 'con_imu').value
        self.lado = float(self.declare_parameter('lado', 1.0).value)
        self.v = float(self.declare_parameter('v', 0.3).value)
        self.w = float(self.declare_parameter('w', 0.6).value)
        self.vueltas = int(self.declare_parameter('vueltas', 2).value)
        self.salida = self.declare_parameter('salida', os.path.expanduser('~/proyecto_final_ws/resultados')).value

        self.pub = self.create_publisher(TwistStamped, '/diff_drive_controller/cmd_vel', 10)
        self.fuentes = {'ruedas': Pose(), 'ekf': Pose(), 'real': Pose()}
        self.create_subscription(Odometry, '/diff_drive_controller/odom', lambda m: self.guardar('ruedas', m), 50)
        self.create_subscription(Odometry, '/odom_filtered', lambda m: self.guardar('ekf', m), 50)
        self.create_subscription(Odometry, '/ground_truth/odom', self.cb_real, 50)

        # Cuadrado en sentido horario: recta, giro de -90°, repetido.
        t_recta = self.lado / self.v
        t_giro = (math.pi / 2) / self.w
        # Cada tramo es (duración [s], v [m/s], w [rad/s]).
        self.tramos = [(1.0, 0.0, 0.0)]  # 1 s quieto
        for _ in range(4 * self.vueltas):
            self.tramos += [(t_recta, self.v, 0.0), (0.5, 0.0, 0.0), (t_giro, 0.0, -self.w), (0.5, 0.0, 0.0)]
        self.tramos.append((2.0, 0.0, 0.0))

        self.filas = []
        self.i_tramo = -1
        self.t_tramo = None
        self.create_timer(0.02, self.paso)

    def ahora(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def guardar(self, nombre, m):
        p = m.pose.pose
        self.fuentes[nombre].actual = (p.position.x, p.position.y, yaw_de(p.orientation))

    def cb_real(self, m):
        self.guardar('real', m)
        if self.i_tramo < 1:
            return
        fila = [round(self.ahora() - self.t0, 3)]
        for nombre in ('real', 'ruedas', 'ekf'):
            fila += [round(v, 5) for v in self.fuentes[nombre].relativa()]
        self.filas.append(fila)

    def publicar(self, v, w):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_footprint'
        msg.twist.linear.x, msg.twist.angular.z = v, w
        self.pub.publish(msg)

    def paso(self):
        t = self.ahora()
        if self.i_tramo == -1:
            self.publicar(0.0, 0.0)
            if all(f.actual is not None for f in self.fuentes.values()):
                self.i_tramo, self.t_tramo = 0, t
                self.get_logger().info('Llegan las tres fuentes. Arranca el cuadrado.')
            return
        dur, v, w = self.tramos[self.i_tramo]
        if t - self.t_tramo >= dur:
            self.i_tramo += 1
            self.t_tramo = t
            if self.i_tramo == 1:
                # Fin del tiempo quieto: se fija el origen de las tres fuentes.
                self.t0 = t
                for f in self.fuentes.values():
                    f.inicio = f.actual
            if self.i_tramo >= len(self.tramos):
                self.publicar(0.0, 0.0)
                self.reportar()
                raise SystemExit
            dur, v, w = self.tramos[self.i_tramo]
        self.publicar(v, w)

    def reportar(self):
        os.makedirs(self.salida, exist_ok=True)
        base = os.path.join(self.salida, f'p2_{self.etiqueta}')
        with open(base + '.csv', 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['t', 'x_real', 'y_real', 'yaw_real', 'x_ruedas', 'y_ruedas', 'yaw_ruedas',
                        'x_ekf', 'y_ekf', 'yaw_ekf'])
            w.writerows(self.filas)

        def errores(i):
            pos = [math.hypot(r[1 + i] - r[1], r[2 + i] - r[2]) for r in self.filas]
            ang = [abs(math.degrees(angulo(r[3 + i] - r[3]))) for r in self.filas]
            return {
                'error_final_m': round(pos[-1], 3),
                'error_max_m': round(max(pos), 3),
                'error_rms_m': round(math.sqrt(sum(e * e for e in pos) / len(pos)), 3),
                'error_yaw_final_deg': round(ang[-1], 2),
                'error_yaw_max_deg': round(max(ang), 2),
            }

        res = {
            'etiqueta': self.etiqueta,
            'trayectoria': f'cuadrado de {self.lado} m, {self.vueltas} vueltas, v={self.v} m/s, w={self.w} rad/s',
            'muestras': len(self.filas),
            'ruedas': errores(3),
            'ekf': errores(6),
        }
        with open(base + '.json', 'w', encoding='utf-8') as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
        self.get_logger().info(json.dumps(res, ensure_ascii=False))
        self.get_logger().info(f'Guardado en {base}.csv / .json')


def main():
    rclpy.init()
    nodo = CompararEkf()
    try:
        rclpy.spin(nodo)
    except SystemExit:
        pass
    finally:
        nodo.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
