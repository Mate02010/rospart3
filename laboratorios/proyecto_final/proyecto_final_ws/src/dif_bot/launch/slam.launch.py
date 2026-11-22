"""Práctica 3: mapeo con SLAM Toolbox (modo online asíncrono).

Arranca la simulación con el EKF de la práctica 2 (TF odom -> base_footprint),
slam_toolbox (publica /map y el TF map -> odom) y RViz con el mapa.
El marco map queda donde arranca el robot: con x = y = yaw = 0 coincide con world.

Uso:
  ros2 launch dif_bot slam.launch.py
  ros2 launch dif_bot slam.launch.py gui:=false      # sin ventana de Gazebo
Recorrido automático (otra terminal):
  ros2 run dif_bot explorar.py --ros-args -p use_sim_time:=true -p v:=0.15 -p w_max:=0.4 -p etiqueta:=lento
Teleoperación, si se prefiere:
  ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true -r /cmd_vel:=/diff_drive_controller/cmd_vel
Guardar el mapa:
  ros2 run nav2_map_server map_saver_cli -f <paquete>/maps/bodega --ros-args -p use_sim_time:=true
"""

from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, EmitEvent, GroupAction, IncludeLaunchDescription,
                            LogInfo, RegisterEventHandler)
from launch.conditions import IfCondition
from launch.events import matches_action
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import LifecycleNode, Node
from launch_ros.event_handlers import OnStateTransition
from launch_ros.events.lifecycle import ChangeState
from launch_ros.substitutions import FindPackageShare
from lifecycle_msgs.msg import Transition


def generate_launch_description():
    pkg = FindPackageShare('dif_bot')

    # Simulación + EKF. El grupo evita que rviz:=false se filtre a este archivo
    # (los argumentos de un include quedan globales si no se agrupan).
    sim_ekf = GroupAction([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([pkg, 'launch', 'ekf.launch.py'])),
            launch_arguments={
                'gui': LaunchConfiguration('gui'),
                'rviz': 'false',  # el RViz de esta práctica se abre abajo
                'x': LaunchConfiguration('x'),
                'y': LaunchConfiguration('y'),
                'yaw': LaunchConfiguration('yaw'),
            }.items(),
        ),
    ])

    # slam_toolbox es un nodo con ciclo de vida: se configura y luego se activa,
    # igual que en online_async_launch.py del paquete slam_toolbox.
    slam = LifecycleNode(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        namespace='',
        output='screen',
        parameters=[LaunchConfiguration('slam_params'),
                    {'use_sim_time': True, 'use_lifecycle_manager': False}],
    )
    configurar = EmitEvent(event=ChangeState(
        lifecycle_node_matcher=matches_action(slam),
        transition_id=Transition.TRANSITION_CONFIGURE,
    ))
    activar = RegisterEventHandler(OnStateTransition(
        target_lifecycle_node=slam,
        start_state='configuring',
        goal_state='inactive',
        entities=[
            LogInfo(msg='[dif_bot] slam_toolbox configurado, activando.'),
            EmitEvent(event=ChangeState(
                lifecycle_node_matcher=matches_action(slam),
                transition_id=Transition.TRANSITION_ACTIVATE,
            )),
        ],
    ))

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        arguments=['-d', PathJoinSubstitution([pkg, 'rviz', 'slam.rviz'])],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(LaunchConfiguration('rviz')),
    )

    return LaunchDescription([
        DeclareLaunchArgument('gui', default_value='true', description='Abrir la ventana de Gazebo'),
        DeclareLaunchArgument('rviz', default_value='true', description='Abrir RViz con el mapa'),
        DeclareLaunchArgument('slam_params',
                              default_value=PathJoinSubstitution([pkg, 'config', 'slam_toolbox.yaml']),
                              description='Parámetros de slam_toolbox'),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        sim_ekf,
        slam,
        configurar,
        activar,
        rviz,
    ])
