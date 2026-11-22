"""Práctica 4: localización con AMCL sobre el mapa de la Práctica 3.

Arranca la simulación con el EKF (ekf.launch.py), el map_server con el mapa guardado,
AMCL y el lifecycle manager de Nav2 que los activa, y RViz con las partículas.
AMCL publica map -> odom; odom -> base_footprint sigue siendo del EKF.

Uso:
  ros2 launch dif_bot localizacion.launch.py                    # mapa maps/bodega.yaml
  ros2 launch dif_bot localizacion.launch.py ruido_laser:=0.15  # láser más ruidoso
  ros2 launch dif_bot localizacion.launch.py gui:=false map:=/ruta/otro_mapa.yaml

La pose inicial se da con "2D Pose Estimate" en RViz o con evaluar_amcl.py.
El mapa por defecto se lee de share/dif_bot/maps: después de guardar maps/bodega.yaml
y bodega.pgm hay que compilar otra vez (colcon build) o pasar map:= con la ruta en src.
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = FindPackageShare('dif_bot')
    params = LaunchConfiguration('params')

    # Simulación + ros2_control + EKF; su RViz se apaga porque aquí se abre otro.
    # El grupo evita que rviz:=false se filtre a este archivo, como en slam.launch.py.
    ekf = GroupAction([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([pkg, 'launch', 'ekf.launch.py'])),
            launch_arguments={
                'gui': LaunchConfiguration('gui'),
                'rviz': 'false',
                'x': LaunchConfiguration('x'),
                'y': LaunchConfiguration('y'),
                'yaw': LaunchConfiguration('yaw'),
                'ruido_laser': LaunchConfiguration('ruido_laser'),
            }.items(),
        ),
    ])

    map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[params, {'yaml_filename': LaunchConfiguration('map'), 'use_sim_time': True}],
    )

    amcl = Node(
        package='nav2_amcl',
        executable='amcl',
        name='amcl',
        output='screen',
        parameters=[params, {'use_sim_time': True}],
    )

    # map_server y amcl son nodos con ciclo de vida: este nodo los configura y activa.
    lifecycle = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_localization',
        output='screen',
        parameters=[{
            'use_sim_time': True,
            'autostart': True,
            'node_names': ['map_server', 'amcl'],
            'bond_timeout': 10.0,  # holgura por si WSL se pone lento (por defecto 4 s)
        }],
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        arguments=['-d', PathJoinSubstitution([pkg, 'rviz', 'localizacion.rviz'])],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(LaunchConfiguration('rviz')),
    )

    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=PathJoinSubstitution([pkg, 'maps', 'bodega.yaml']),
                              description='YAML del mapa (Práctica 3)'),
        DeclareLaunchArgument('params', default_value=PathJoinSubstitution([pkg, 'config', 'amcl.yaml']),
                              description='Parámetros de amcl y map_server'),
        DeclareLaunchArgument('gui', default_value='true', description='Abrir la ventana de Gazebo'),
        DeclareLaunchArgument('rviz', default_value='true', description='Abrir RViz'),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        DeclareLaunchArgument('ruido_laser', default_value='0.01',
                              description='Desviación del ruido gaussiano del lidar [m]'),
        ekf,
        map_server,
        amcl,
        lifecycle,
        rviz,
    ])
