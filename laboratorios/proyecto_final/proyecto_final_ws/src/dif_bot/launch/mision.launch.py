"""Proyecto final: Nav2 en la bodega + nodo de misión por waypoints.

Arranca navegacion.launch.py (simulación, EKF, AMCL, Nav2 y RViz) y el nodo
mision.py, que espera a que Nav2 esté activo y deja la misión lista. La misión
no arranca sola: se inicia con el servicio.

Uso:
  ros2 launch dif_bot mision.launch.py
  ros2 launch dif_bot mision.launch.py waypoints:=/ruta/otra_mision.yaml gui:=false
En otra terminal:
  ros2 service call /iniciar_mision std_srvs/srv/Trigger
  ros2 topic echo /estado_mision
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = FindPackageShare('dif_bot')
    x = LaunchConfiguration('x')
    y = LaunchConfiguration('y')
    yaw = LaunchConfiguration('yaw')

    navegacion = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([pkg, 'launch', 'navegacion.launch.py'])),
        launch_arguments={
            'gui': LaunchConfiguration('gui'),
            'rviz': LaunchConfiguration('rviz'),
            'x': x,
            'y': y,
            'yaw': yaw,
        }.items(),
    )

    # La pose inicial que publica el nodo es la misma donde aparece el robot.
    # Sin name=: launch_ros lo pasa como __node:= global y también renombraría al
    # BasicNavigator del mismo proceso; el script ya llama a su nodo 'mision'.
    mision = Node(
        package='dif_bot',
        executable='mision.py',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'waypoints_file': LaunchConfiguration('waypoints'),
            'x0': ParameterValue(x, value_type=float),
            'y0': ParameterValue(y, value_type=float),
            'yaw0': ParameterValue(yaw, value_type=float),
        }],
    )

    return LaunchDescription([
        DeclareLaunchArgument('waypoints',
                              default_value=PathJoinSubstitution([pkg, 'config', 'waypoints.yaml']),
                              description='YAML con los waypoints de la misión'),
        DeclareLaunchArgument('gui', default_value='true', description='Abrir la ventana de Gazebo'),
        DeclareLaunchArgument('rviz', default_value='true', description='Abrir RViz'),
        DeclareLaunchArgument('x', default_value='0.0', description='Pose inicial del robot [m]'),
        DeclareLaunchArgument('y', default_value='0.0', description='Pose inicial del robot [m]'),
        DeclareLaunchArgument('yaw', default_value='0.0', description='Orientación inicial [rad]'),
        navegacion,
        mision,
    ])
