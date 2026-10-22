"""Ajustes de integracion posteriores a la generacion real en Setup Assistant."""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT
CONFIG = SRC / 'ur5_gripper_moveit/config'
controllers_file = CONFIG / 'moveit_controllers.yaml'
controllers = yaml.safe_load(controllers_file.read_text())
manager = controllers['moveit_simple_controller_manager']
if 'arm_controller' in manager:
    manager['scaled_joint_trajectory_controller'] = manager.pop('arm_controller')
manager['controller_names'] = ['scaled_joint_trajectory_controller', 'gripper_controller']
for name in manager['controller_names']:
    manager[name].update(action_ns='follow_joint_trajectory', default=True)
controllers_file.write_text(yaml.safe_dump(controllers, sort_keys=False))

limits_file = CONFIG / 'joint_limits.yaml'
limits = yaml.safe_load(limits_file.read_text())
for name, item in limits['joint_limits'].items():
    item['has_acceleration_limits'] = True
    item['max_acceleration'] = 0.2 if 'finger' in name else 1.0
limits_file.write_text(yaml.safe_dump(limits, sort_keys=False))

sys.path.insert(0, str(SRC / 'lab_manipulador'))
from lab_manipulador.pick_place import ARM, GRIPPER, POSES
srdf_file = CONFIG / 'ur.srdf'
tree = ET.parse(srdf_file)
robot = tree.getroot()
for old in robot.findall('group_state'):
    robot.remove(old)
for name, values in POSES.items():
    state = ET.SubElement(robot, 'group_state', name=name, group='arm')
    for joint, value in zip(ARM, values):
        ET.SubElement(state, 'joint', name=joint, value=str(value))
for name, value in [('Open', 0.04), ('Close', 0.004)]:
    state = ET.SubElement(robot, 'group_state', name=name, group='gripper')
    for joint in GRIPPER:
        ET.SubElement(state, 'joint', name=joint, value=str(value))
robot.find('end_effector').set('parent_group', 'arm')
ET.indent(tree, space='  ')
tree.write(srdf_file, encoding='utf-8', xml_declaration=True)

from ament_index_python.packages import get_package_share_directory
default = Path(get_package_share_directory('moveit_configs_utils')) / 'default_configs/ompl_planning.yaml'
ompl = yaml.safe_load(default.read_text())
default_planners = Path(get_package_share_directory('moveit_configs_utils')) / 'default_configs/ompl_defaults.yaml'
if 'planner_configs' not in ompl:
    ompl.update(yaml.safe_load(default_planners.read_text()))
for group in ['arm', 'gripper']:
    ompl[group] = {'planner_configs': ['RRTConnect'],
                   'longest_valid_segment_fraction': 0.01}
(CONFIG / 'ompl_planning.yaml').write_text(yaml.safe_dump(ompl, sort_keys=False))
print('Configuracion integrada con controladores de Gazebo, poses y limites de aceleracion.')
