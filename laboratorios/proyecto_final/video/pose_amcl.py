"""Imprime la pose de AMCL, la real de Gazebo y el error entre las dos."""
import math
import time

import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy

rclpy.init()
n = Node('pose_amcl')
d = {}
q = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL, reliability=ReliabilityPolicy.RELIABLE)
n.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', lambda m: d.__setitem__('amcl', m), q)
n.create_subscription(Odometry, '/ground_truth/odom', lambda m: d.__setitem__('real', m), 10)
t = time.time()
while time.time() - t < 15 and len(d) < 2:
    rclpy.spin_once(n, timeout_sec=0.2)


def yaw(o):
    return math.degrees(math.atan2(2 * (o.w * o.z + o.x * o.y), 1 - 2 * (o.y * o.y + o.z * o.z)))


a, r = d['amcl'].pose.pose, d['real'].pose.pose
print(f"AMCL : x={a.position.x:6.2f}  y={a.position.y:6.2f}  yaw={yaw(a.orientation):7.1f} deg")
print(f"Real : x={r.position.x:6.2f}  y={r.position.y:6.2f}  yaw={yaw(r.orientation):7.1f} deg")
print(f"Error: {math.hypot(a.position.x - r.position.x, a.position.y - r.position.y):.2f} m")
