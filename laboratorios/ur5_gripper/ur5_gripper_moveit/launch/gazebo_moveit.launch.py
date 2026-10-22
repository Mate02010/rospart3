"""MoveIt y RViz sobre Gazebo ya activo; comparte sus estados y controladores."""
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from moveit_configs_utils import MoveItConfigsBuilder


def generate_launch_description():
    config = MoveItConfigsBuilder('ur', package_name='ur5_gripper_moveit').planning_pipelines(
        pipelines=['ompl']).to_moveit_configs()
    return LaunchDescription([
        DeclareLaunchArgument('rviz', default_value='true'),
        Node(package='moveit_ros_move_group', executable='move_group', output='screen',
             parameters=[config.to_dict(), {'use_sim_time': True,
                'publish_robot_description_semantic': True,
                'publish_robot_description': False,
                'trajectory_execution.allowed_execution_duration_scaling': 3.0,
                'trajectory_execution.allowed_goal_duration_margin': 5.0}]),
        Node(package='rviz2', executable='rviz2', name='rviz2', output='log',
             condition=IfCondition(LaunchConfiguration('rviz')),
             arguments=['-d', str(config.package_path / 'config/moveit.rviz')],
             parameters=[config.robot_description, config.robot_description_semantic,
                         config.robot_description_kinematics, config.planning_pipelines,
                         config.joint_limits, {'use_sim_time': True}]),
    ])
