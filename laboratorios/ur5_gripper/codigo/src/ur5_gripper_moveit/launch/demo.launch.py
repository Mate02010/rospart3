"""Demostracion completa usando los controladores reales de la simulacion Gazebo."""
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
from pathlib import Path


def generate_launch_description():
    simulation = Path(get_package_share_directory('ur5_robotiq_bringup')) / 'launch/sim_gz_sgb.launch.py'
    planning = Path(get_package_share_directory('ur5_gripper_moveit')) / 'launch/gazebo_moveit.launch.py'
    return LaunchDescription([
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(simulation)),
                                 launch_arguments={'launch_rviz': 'false'}.items()),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(str(planning))),
    ])
