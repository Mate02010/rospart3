"""Abre un mundo vacío e inserta el robot generado desde Xacro/URDF."""

from launch import LaunchDescription
from launch.actions import ExecuteProcess, IncludeLaunchDescription, RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    package_share = FindPackageShare('robotica_part3')
    ros_gz_share = FindPackageShare('ros_gz_sim')
    xacro_file = PathJoinSubstitution([package_share, 'description', 'simple_diff_robot.urdf.xacro'])
    world_file = PathJoinSubstitution([package_share, 'worlds', 'empty_world.sdf'])

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([ros_gz_share, 'launch', 'gz_sim.launch.py'])
        ),
        launch_arguments={'gz_args': ['-r -v 3 ', world_file]}.items(),
    )

    # Primero se expande Xacro. El archivo temporal es el URDF que usa Gazebo.
    generate_urdf = ExecuteProcess(
        cmd=['bash', '-c', ['xacro ', xacro_file, ' > /tmp/simple_diff_robot.urdf']],
        output='screen',
    )

    spawn_robot = Node(
        package='ros_gz_sim', executable='create', output='screen',
        arguments=[
            '-world', 'default',
            '-file', '/tmp/simple_diff_robot.urdf',
            '-name', 'simple_diff_robot_urdf',
            '-x', '0', '-y', '0', '-z', '0.15',
        ],
    )

    return LaunchDescription([
        gazebo,
        generate_urdf,
        RegisterEventHandler(
            OnProcessExit(
                target_action=generate_urdf,
                on_exit=[TimerAction(period=5.0, actions=[spawn_robot])],
            )
        ),
    ])
