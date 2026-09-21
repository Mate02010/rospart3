"""Nombre de launch solicitado por la guía; reutiliza la visualización del robot."""

from launch import LaunchDescription
from launch.substitutions import Command, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    package_share = FindPackageShare('robotica_part3')
    robot_file = PathJoinSubstitution([package_share, 'description', 'simple_diff_robot.urdf.xacro'])
    rviz_file = PathJoinSubstitution([package_share, 'config', 'urdf_config.rviz'])
    robot_description = ParameterValue(Command(['xacro ', robot_file]), value_type=str)

    return LaunchDescription([
        Node(
            package='robot_state_publisher', executable='robot_state_publisher',
            parameters=[{'robot_description': robot_description}], output='screen',
        ),
        Node(
            package='joint_state_publisher', executable='joint_state_publisher',
            parameters=[{'robot_description': robot_description}], output='screen',
        ),
        Node(package='rviz2', executable='rviz2', arguments=['-d', rviz_file], output='screen'),
    ])
