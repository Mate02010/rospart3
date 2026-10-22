"""Secuencia verificada por joint_states; modos topicos ROS y planificacion MoveIt."""
import json
import time
from pathlib import Path
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.qos import QoSProfile, DurabilityPolicy
from sensor_msgs.msg import JointState
from std_msgs.msg import Bool, String
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from moveit_msgs.msg import Constraints, JointConstraint, MoveItErrorCodes
from moveit_msgs.srv import GetMotionPlan, GetStateValidity
from moveit_msgs.action import ExecuteTrajectory

ARM = ['shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
       'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint']
GRIPPER = ['gripper_finger_joint', 'right_finger_joint']
POSES = {
    'Preparacion': [0.0, -1.57, 1.57, -1.57, -1.57, 0.0],
    'Recogida': [0.35, -1.45, 1.80, -1.92, -1.57, 0.0],
    'Intermedio': [0.0, -1.20, 1.40, -1.77, -1.57, 0.0],
    'Entrega': [-0.40, -1.45, 1.80, -1.92, -1.57, 0.0],
}


class PickPlace(Node):
    def __init__(self):
        super().__init__('pick_place_ur5')
        self.declare_parameter('mode', 'topics')
        self.declare_parameter('output_dir', '/tmp/ur5_lab_evidence')
        self.mode = self.get_parameter('mode').value
        if self.mode not in ('topics', 'moveit'):
            raise ValueError('mode debe ser topics o moveit')
        self.current = None
        self.last_state = 0.0
        self.digital = None
        self.input_sequence = 0
        self.events = []
        self.samples = []
        self.create_subscription(JointState, '/joint_states', self.joints, 20)
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.create_subscription(Bool, '/lab/digital_input', self.input, qos)
        self.digital_out = self.create_publisher(Bool, '/lab/digital_output', qos)
        self.waiting_out = self.create_publisher(Bool, '/lab/waiting_input', qos)
        self.status = self.create_publisher(String, '/lab/status', qos)
        self.arm_pub = self.create_publisher(JointTrajectory,
            '/scaled_joint_trajectory_controller/joint_trajectory', 10)
        self.grip_pub = self.create_publisher(JointTrajectory,
            '/gripper_controller/joint_trajectory', 10)
        self.planner = self.create_client(GetMotionPlan, '/plan_kinematic_path')
        self.validity = self.create_client(GetStateValidity, '/check_state_validity')
        self.execute_client = ActionClient(self, ExecuteTrajectory, '/execute_trajectory')

    def joints(self, msg):
        self.current = msg
        self.last_state = time.monotonic()
        if not self.samples or time.time() - self.samples[-1]['time'] > 0.15:
            self.samples.append({'time': time.time(), 'joints': dict(zip(msg.name, msg.position))})

    def input(self, msg):
        self.digital = msg.data
        self.input_sequence += 1

    def event(self, kind, **values):
        item = {'time': time.time(), 'kind': kind, **values}
        self.events.append(item)
        self.get_logger().info(json.dumps(item, ensure_ascii=False))
        self.status.publish(String(data=json.dumps(item, ensure_ascii=False)))

    def until(self, condition, timeout, message):
        deadline = time.monotonic() + timeout
        while rclpy.ok() and time.monotonic() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            if condition():
                return
        raise TimeoutError(message)

    def wait(self, future, timeout=45):
        self.until(future.done, timeout, 'Sin respuesta de MoveIt')
        result = future.result()
        if result is None:
            raise RuntimeError('Respuesta vacia')
        return result

    def error(self, names, positions):
        if self.current is None or time.monotonic() - self.last_state > 2:
            return float('inf')
        state = dict(zip(self.current.name, self.current.position))
        return max(abs(state.get(name, float('inf')) - value) for name, value in zip(names, positions))

    def move(self, group, names, positions, label):
        self.event('motion_start', group=group, point=label, target=positions, mode=self.mode)
        if self.mode == 'topics':
            publisher = self.arm_pub if group == 'arm' else self.grip_pub
            self.until(lambda: publisher.get_subscription_count() > 0, 20, 'Controlador sin suscriptor')
            trajectory = JointTrajectory(joint_names=names)
            point = JointTrajectoryPoint(positions=[float(value) for value in positions])
            point.time_from_start.sec = 3 if group == 'arm' else 1
            trajectory.points = [point]
            publisher.publish(trajectory)
        else:
            if not self.planner.wait_for_service(timeout_sec=30) or not self.execute_client.wait_for_server(timeout_sec=30):
                raise RuntimeError('MoveIt no esta disponible')
            request = GetMotionPlan.Request()
            plan = request.motion_plan_request
            plan.group_name = group
            plan.pipeline_id = 'ompl'
            plan.planner_id = 'RRTConnect'
            plan.allowed_planning_time = 5.0
            plan.num_planning_attempts = 5
            plan.max_velocity_scaling_factor = 0.3
            plan.max_acceleration_scaling_factor = 0.3
            plan.start_state.joint_state = self.current
            goal = Constraints()
            goal.joint_constraints = [JointConstraint(joint_name=name, position=float(value),
                tolerance_above=0.001, tolerance_below=0.001, weight=1.0)
                for name, value in zip(names, positions)]
            plan.goal_constraints = [goal]
            result = self.wait(self.planner.call_async(request)).motion_plan_response
            if result.error_code.val != MoveItErrorCodes.SUCCESS:
                raise RuntimeError(f'Planificacion {label}: {result.error_code.val}')
            self.event('plan_success', point=label, group=group,
                trajectory_points=len(result.trajectory.joint_trajectory.points))
            handle = self.wait(self.execute_client.send_goal_async(ExecuteTrajectory.Goal(trajectory=result.trajectory)))
            if not handle.accepted:
                raise RuntimeError('MoveIt rechazo ejecutar la trayectoria')
            execution = self.wait(handle.get_result_async(), 120).result
            if execution.error_code.val != MoveItErrorCodes.SUCCESS:
                raise RuntimeError(f'Ejecucion {label}: {execution.error_code.val}')
        tolerance = 0.02 if group == 'arm' else 0.002
        stable = [0]

        def settled():
            stable[0] = stable[0] + 1 if self.error(names, positions) < tolerance else 0
            return stable[0] >= 4

        self.until(settled, 100, f'No alcanzo {label}')
        self.event('motion_success', point=label, group=group, max_error=self.error(names, positions))

    def gripper(self, opened):
        self.move('gripper', GRIPPER, [0.04, 0.04] if opened else [0.004, 0.004],
                  'Pinza abierta' if opened else 'Pinza cerrada')

    def run(self):
        self.until(lambda: self.current is not None and set(ARM + GRIPPER) <= set(self.current.name),
                   40, 'No llegan los ocho estados articulares')
        self.digital_out.publish(Bool(data=False))
        self.waiting_out.publish(Bool(data=False))
        self.move('arm', ARM, POSES['Preparacion'], 'Preparacion')
        self.event('info', point='Preparacion', message='Inicio de rutina Pick and Place')
        self.gripper(True)
        self.move('arm', ARM, POSES['Recogida'], 'Recogida')
        self.gripper(False)
        self.event('logical_pick', point='Recogida', message='Pieza representada por estado logico')
        self.move('arm', ARM, POSES['Intermedio'], 'Intermedio')
        self.digital_out.publish(Bool(data=True))
        self.event('digital_output', point='Intermedio', value=True)
        self.move('arm', ARM, POSES['Entrega'], 'Entrega')
        self.gripper(True)
        self.event('logical_place', point='Entrega')
        self.waiting_out.publish(Bool(data=True))
        self.event('wait_input', point='Entrega', message='Esperando entrada BAJA seguida de ALTA')
        self.until(lambda: self.digital is False, 90, 'Entrada no fue BAJA')
        baseline = self.input_sequence
        self.until(lambda: self.digital is True and self.input_sequence > baseline,
                   90, 'No se recibio confirmacion digital ALTA')
        self.event('digital_input_confirmed', point='Entrega', value=True)
        self.waiting_out.publish(Bool(data=False))
        self.digital_out.publish(Bool(data=False))
        self.move('arm', ARM, POSES['Preparacion'], 'Preparacion final')
        self.event('completed', distinct_arm_points=len(POSES))

    def save(self, success, error=None):
        directory = Path(self.get_parameter('output_dir').value)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / f'resultado_{self.mode}.json').write_text(json.dumps({
            'success': success, 'error': error, 'mode': self.mode,
            'poses': POSES, 'events': self.events, 'joint_samples': self.samples,
            'scope': 'Simulacion de brazo y dedos; pieza logica sin agarre fisico por contacto',
        }, indent=2, ensure_ascii=False))


def main():
    rclpy.init()
    node = PickPlace()
    success = False
    error = None
    try:
        node.run()
        success = True
    except Exception as exc:
        error = str(exc)
        node.get_logger().error(error)
        raise
    finally:
        node.save(success, error)
        node.destroy_node()
        rclpy.shutdown()
