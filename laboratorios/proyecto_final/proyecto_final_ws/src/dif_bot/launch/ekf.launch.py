"""Práctica 2: EKF de robot_localization (odometría de ruedas + IMU).

Arranca la simulación con ros2_control (controladores activados por el spawner)
y el nodo ekf_filter_node, que publica /odom_filtered y el TF odom -> base_footprint.

Uso:
  ros2 launch dif_bot ekf.launch.py                  # ruedas + IMU
  ros2 launch dif_bot ekf.launch.py usar_imu:=false  # solo ruedas (prueba sin IMU)
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = FindPackageShare('dif_bot')
    usar_imu = LaunchConfiguration('usar_imu')

    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([pkg, 'launch', 'sim.launch.py'])),
        launch_arguments={
            'use_ros2_control': 'true',
            'activar_controladores': 'true',
            'controladores': PathJoinSubstitution([pkg, 'config', 'controllers_ekf.yaml']),
            'world': LaunchConfiguration('world'),
            'gui': LaunchConfiguration('gui'),
            'rviz': LaunchConfiguration('rviz'),
            'rviz_config': LaunchConfiguration('rviz_config'),
            'camara': LaunchConfiguration('camara'),
            'x': LaunchConfiguration('x'),
            'y': LaunchConfiguration('y'),
            'yaw': LaunchConfiguration('yaw'),
            'ruido_laser': LaunchConfiguration('ruido_laser'),
            'cmd_vel_global': LaunchConfiguration('cmd_vel_global'),
        }.items(),
    )

    # Sin IMU: el filtro escucha un tópico que nadie publica y solo usa las ruedas.
    topico_imu = PythonExpression(["'/imu' if '", usar_imu, "' == 'true' else '/imu_desactivada'"])

    ekf = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[PathJoinSubstitution([pkg, 'config', 'ekf.yaml']),
                    {'use_sim_time': True, 'imu0': topico_imu}],
        remappings=[('odometry/filtered', '/odom_filtered')],
    )

    return LaunchDescription([
        DeclareLaunchArgument('usar_imu', default_value='true', description='Fusionar la IMU'),
        DeclareLaunchArgument('world', default_value=PathJoinSubstitution([pkg, 'worlds', 'bodega.sdf'])),
        DeclareLaunchArgument('gui', default_value='true'),
        DeclareLaunchArgument('rviz', default_value='true'),
        DeclareLaunchArgument('rviz_config', default_value=PathJoinSubstitution([pkg, 'rviz', 'dif_bot.rviz'])),
        DeclareLaunchArgument('camara', default_value='false'),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        DeclareLaunchArgument('ruido_laser', default_value='0.01', description='Ruido del LiDAR [m]'),
        DeclareLaunchArgument('cmd_vel_global', default_value='false',
                              description='true: el controlador escucha /cmd_vel (Nav2)'),
        sim,
        ekf,
    ])
