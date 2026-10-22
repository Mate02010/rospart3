"""Entrada y salida digitales simuladas con ROS, independientes del robot."""
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from std_msgs.msg import Bool
from std_srvs.srv import SetBool


class DigitalIO(Node):
    def __init__(self):
        super().__init__('digital_io_simulado')
        self.declare_parameter('auto_confirm', False)
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.publisher = self.create_publisher(Bool, '/lab/digital_input', qos)
        self.value = False
        self.deadline = None
        self.publisher.publish(Bool(data=False))
        self.create_service(SetBool, '/lab/set_digital_input', self.set_input)
        self.create_subscription(Bool, '/lab/waiting_input', self.waiting, qos)
        self.create_subscription(Bool, '/lab/digital_output', self.output, qos)
        self.create_timer(0.1, self.tick)

    def set_input(self, request, response):
        self.value = request.data
        self.publisher.publish(Bool(data=self.value))
        response.success = True
        response.message = f'Entrada digital simulada = {self.value}'
        self.get_logger().info(response.message)
        return response

    def waiting(self, msg):
        if msg.data and self.get_parameter('auto_confirm').value:
            self.value = False
            self.publisher.publish(Bool(data=False))
            self.deadline = time.monotonic() + 1.5

    def output(self, msg):
        self.get_logger().info(f'Salida digital simulada = {msg.data}')

    def tick(self):
        if self.deadline is not None and time.monotonic() >= self.deadline:
            self.value = True
            self.publisher.publish(Bool(data=True))
            self.deadline = None
            self.get_logger().info('Pulsador automatico de demostracion: entrada ALTA')


def main():
    rclpy.init()
    node = DigitalIO()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
