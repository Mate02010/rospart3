from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='turtlesim',
            executable='turtlesim_node',
            namespace='turtle1',
            name='sim',
            output='screen',
        ),
        Node(
            package='turtlesim',
            executable='turtlesim_node',
            namespace='turtle2',
            name='sim',
            output='screen',
        ),
        Node(
            package='turtlesim',
            executable='mimic',
            name='mimic',
            remappings=[
                ('/input/pose', '/turtle1/turtle1/pose'),
                ('/output/cmd_vel', '/turtle2/turtle1/cmd_vel'),
            ],
            output='screen',
        ),
    ])
