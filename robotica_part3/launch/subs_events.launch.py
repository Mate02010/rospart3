"""Launch secundario: parámetros, condición y eventos sencillos de TurtleSim."""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, LogInfo, RegisterEventHandler, TimerAction
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit, OnProcessStart
from launch.substitutions import FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node


def generate_launch_description():
    namespace = LaunchConfiguration('namespace')
    background_r = LaunchConfiguration('background_r')
    spawn_extra_turtle = LaunchConfiguration('spawn_extra_turtle')

    turtlesim_node = Node(
        package='turtlesim',
        executable='turtlesim_node',
        namespace=namespace,
        name='sim',
        parameters=[{
            'background_r': background_r,
            'background_g': 90,
            'background_b': 120,
        }],
        output='screen',
    )

    spawn_turtle = ExecuteProcess(
        condition=IfCondition(spawn_extra_turtle),
        cmd=[
            FindExecutable(name='ros2'), 'service', 'call',
            PathJoinSubstitution(['/', namespace, 'spawn']),
            'turtlesim_msgs/srv/Spawn',
            '{x: 2.0, y: 2.0, theta: 0.0, name: turtle_extra}',
        ],
        output='screen',
    )

    started_event = RegisterEventHandler(
        OnProcessStart(
            target_action=turtlesim_node,
            on_start=[
                LogInfo(msg=['TurtleSim iniciada en /', namespace, '/sim.']),
                TimerAction(period=2.0, actions=[spawn_turtle]),
            ],
        )
    )
    stopped_event = RegisterEventHandler(
        OnProcessExit(
            target_action=turtlesim_node,
            on_exit=[LogInfo(msg='El proceso de TurtleSim terminó.')],
        )
    )

    return LaunchDescription([
        DeclareLaunchArgument('namespace', default_value='turtle_params'),
        DeclareLaunchArgument('background_r', default_value='180'),
        DeclareLaunchArgument('spawn_extra_turtle', default_value='false'),
        turtlesim_node,
        started_event,
        stopped_event,
    ])
