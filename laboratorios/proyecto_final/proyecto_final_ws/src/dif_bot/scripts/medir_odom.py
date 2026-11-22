#!/usr/bin/env python3
"""Práctica 1: mide cómo responde la odometría a un escalón de velocidad.

Manda v (y w) constante durante 'duracion' segundos y luego cero, y compara la
odometría del controlador contra la pose real que da Gazebo (/ground_truth/odom).

Uso (con la simulación corriendo):
  ros2 run dif_bot medir_odom.py --ros-args -p use_sim_time:=true -p modo:=gz
  ros2 run dif_bot medir_odom.py --ros-args -p use_sim_time:=true -p modo:=ros2_control
"""
import json
import math
import os
import statistics

import rclpy
from geometry_msgs.msg import Twist, TwistStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node


def yaw_de(q):
    return math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z))


class MedirOdom(Node):
    def __init__(self):
        super().__init__('medir_odom')
        self.modo = self.declare_parameter('modo', 'gz').value
        self.v = float(self.declare_parameter('v', 0.3).value)
        self.w = float(self.declare_parameter('w', 0.0).value)
        self.duracion = float(self.declare_parameter('duracion', 4.0).value)
        self.salida = self.declare_parameter('salida', os.path.expanduser('~/proyecto_final_ws/resultados')).value

        if self.modo == 'ros2_control':
            self.pub = self.create_publisher(TwistStamped, '/diff_drive_controller/cmd_vel', 10)
            topico_odom = '/diff_drive_controller/odom'
        else:
            self.pub = self.create_publisher(Twist, '/cmd_vel', 10)
            topico_odom = '/odom'
        self.topico_odom = topico_odom

        self.odom = []   # (t_llegada, t_mensaje, x, y, yaw, vx, wz)
        self.real = []   # (t_llegada, x, y, yaw)
        self.create_subscription(Odometry, topico_odom, self.cb_odom, 50)
        self.create_subscription(Odometry, '/ground_truth/odom', self.cb_real, 50)

        self.fase = 'esperando'
        self.t_fase = None
        self.t_inicio = None
        self.create_timer(0.02, self.paso)  # comando a 50 Hz

    def ahora(self):
        return self.get_clock().now().nanoseconds * 1e-9

    def cb_odom(self, m):
        t = self.ahora()
        stamp = m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
        p = m.pose.pose
        self.odom.append((t, stamp, p.position.x, p.position.y, yaw_de(p.orientation),
                          m.twist.twist.linear.x, m.twist.twist.angular.z))

    def cb_real(self, m):
        p = m.pose.pose
        self.real.append((self.ahora(), p.position.x, p.position.y, yaw_de(p.orientation)))

    def publicar(self, v, w):
        if self.modo == 'ros2_control':
            msg = TwistStamped()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = 'base_footprint'
            msg.twist.linear.x, msg.twist.angular.z = v, w
        else:
            msg = Twist()
            msg.linear.x, msg.angular.z = v, w
        self.pub.publish(msg)

    def paso(self):
        t = self.ahora()
        if self.fase == 'esperando':
            self.publicar(0.0, 0.0)
            if len(self.odom) > 20 and len(self.real) > 20:
                self.fase, self.t_fase = 'quieto', t
                self.get_logger().info(f'Recibiendo {self.topico_odom}. Midiendo...')
        elif self.fase == 'quieto':
            self.publicar(0.0, 0.0)
            if t - self.t_fase > 1.0:
                self.fase, self.t_fase, self.t_inicio = 'moviendo', t, t
                self.odom0 = self.odom[-1]
                self.real0 = self.real[-1]
        elif self.fase == 'moviendo':
            self.publicar(self.v, self.w)
            if t - self.t_fase > self.duracion:
                self.fase, self.t_fase = 'frenando', t
        elif self.fase == 'frenando':
            self.publicar(0.0, 0.0)
            if t - self.t_fase > 2.0:
                self.fase = 'fin'
                self.reportar()
                raise SystemExit

    def reportar(self):
        t0, t1 = self.t_inicio, self.t_inicio + self.duracion
        en_mov = [o for o in self.odom if t0 <= o[0] <= t1]
        estable = [o for o in en_mov if o[0] >= t1 - 2.0]
        stamps = [o[1] for o in self.odom if o[0] >= t0 - 1.0]
        dts = [b - a for a, b in zip(stamps, stamps[1:]) if b > a]

        def primer_cruce(frac):
            for o in en_mov:
                if abs(self.v) > 0 and o[5] >= frac * self.v:
                    return o[0] - t0
                if abs(self.v) == 0 and abs(o[6]) >= frac * abs(self.w):
                    return o[0] - t0
            return None

        of, rf = self.odom[-1], self.real[-1]
        o0, r0 = self.odom0, self.real0
        d_odom = math.hypot(of[2] - o0[2], of[3] - o0[3])
        d_real = math.hypot(rf[1] - r0[1], rf[2] - r0[2])

        def giro_acumulado(yaws):
            # Suma los cambios de ángulo muestra a muestra para no perder vueltas de ±180°.
            total = 0.0
            for a, b in zip(yaws, yaws[1:]):
                total += math.atan2(math.sin(b - a), math.cos(b - a))
            return math.degrees(total)

        giro_odom = giro_acumulado([o[4] for o in self.odom if o[0] >= o0[0]])
        giro_real = giro_acumulado([r[3] for r in self.real if r[0] >= r0[0]])

        res = {
            'modo': self.modo,
            'topico_odom': self.topico_odom,
            'comando': {'v': self.v, 'w': self.w, 'duracion_s': self.duracion},
            'frecuencia_odom_hz': round(1.0 / statistics.mean(dts), 1) if dts else None,
            'jitter_odom_ms': round(1000 * statistics.pstdev(dts), 2) if len(dts) > 1 else None,
            'latencia_50_s': primer_cruce(0.5),
            'latencia_90_s': primer_cruce(0.9),
            'ruido_vx_estable': round(statistics.pstdev([o[5] for o in estable]), 5) if len(estable) > 1 else None,
            'vx_media_estable': round(statistics.mean([o[5] for o in estable]), 4) if estable else None,
            'distancia_odom_m': round(d_odom, 4),
            'distancia_real_m': round(d_real, 4),
            'error_distancia_m': round(d_odom - d_real, 4),
            'giro_odom_deg': round(giro_odom, 2),
            'giro_real_deg': round(giro_real, 2),
        }
        os.makedirs(self.salida, exist_ok=True)
        nombre = os.path.join(self.salida, f'p1_{self.modo}_v{self.v}_w{self.w}.json')
        with open(nombre, 'w', encoding='utf-8') as f:
            json.dump(res, f, indent=2, ensure_ascii=False)
        self.get_logger().info(json.dumps(res, ensure_ascii=False))
        self.get_logger().info(f'Guardado en {nombre}')


def main():
    rclpy.init()
    nodo = MedirOdom()
    try:
        rclpy.spin(nodo)
    except SystemExit:
        pass
    finally:
        nodo.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
