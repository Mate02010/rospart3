from launch import LaunchDescription
from launch.substitutions import Command, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    # Rutas del modelo y de la configuración guardadas dentro del paquete.
    robot_file = PathJoinSubstitution([
        FindPackageShare('robotica_part3'),
        'description',
        'simple_diff_robot.urdf.xacro',
    ])
    rviz_file = PathJoinSubstitution([
        FindPackageShare('robotica_part3'),
        'config',
        'simple_diff_robot.rviz',
    ])

    # xacro convierte el modelo a URDF antes de enviarlo a ROS.
    robot_description = ParameterValue(
        Command(['xacro ', robot_file]),
        value_type=str,
    )

    return LaunchDescription([
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            parameters=[{'robot_description': robot_description}],
            output='screen',
        ),
        Node(
            package='joint_state_publisher',
            executable='joint_state_publisher',
            parameters=[{'robot_description': robot_description}],
            output='screen',
        ),
        Node(
            package='rviz2',
            executable='rviz2',
            arguments=['-d', rviz_file],
            output='screen',
        ),
    ])
