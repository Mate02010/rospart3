"""Práctica 5: navegación autónoma con Nav2 en la bodega.

Arranca la simulación con el EKF (ekf.launch.py), Nav2 completo con el mapa de la
Práctica 3 (map_server + AMCL, planner, controller, behaviors y bt_navigator) y RViz.
La cadena de velocidad termina en /cmd_vel (TwistStamped), que es lo que escucha el
diff_drive_controller con cmd_vel_global:=true:
  controller_server -> /cmd_vel_nav -> velocity_smoother -> /cmd_vel_smoothed
  -> collision_monitor -> /cmd_vel

Uso:
  ros2 launch dif_bot navegacion.launch.py
  ros2 launch dif_bot navegacion.launch.py gui:=false            # sin ventana de Gazebo
  ros2 launch dif_bot navegacion.launch.py x:=-4.0 y:=0.25 yaw:=3.14
Las metas se envían desde RViz con "Nav2 Goal" (y "2D Pose Estimate" si AMCL se pierde).
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from nav2_common.launch import RewrittenYaml


def generate_launch_description():
    pkg = FindPackageShare('dif_bot')
    x = LaunchConfiguration('x')
    y = LaunchConfiguration('y')
    yaw = LaunchConfiguration('yaw')

    # Simulación + ros2_control + EKF. RViz va aparte con la vista de Nav2.
    # El grupo evita que rviz:=false se filtre a este archivo (los argumentos de un
    # include quedan globales si no se agrupan y el RViz de abajo no arrancaría).
    sim_ekf = GroupAction([
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(PathJoinSubstitution([pkg, 'launch', 'ekf.launch.py'])),
            launch_arguments={
                'cmd_vel_global': 'true',
                'gui': LaunchConfiguration('gui'),
                'rviz': 'false',
                'x': x,
                'y': y,
                'yaw': yaw,
            }.items(),
        ),
    ])

    # AMCL arranca en la misma pose en que aparece el robot (mapa = marco world).
    # float() evita que "2" llegue como entero a un parámetro double.
    def como_float(valor):
        return PythonExpression(['str(float(', valor, '))'])

    params = RewrittenYaml(
        source_file=LaunchConfiguration('params_file'),
        param_rewrites={
            'amcl.ros__parameters.initial_pose.x': como_float(x),
            'amcl.ros__parameters.initial_pose.y': como_float(y),
            'amcl.ros__parameters.initial_pose.yaw': como_float(yaw),
        },
        convert_types=True,
    )

    # bringup_launch.py evalúa este valor con PythonExpression: debe ser True/False.
    composicion = PythonExpression(
        ["'True' if '", LaunchConfiguration('use_composition'), "'.lower() == 'true' else 'False'"])

    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([FindPackageShare('nav2_bringup'), 'launch', 'bringup_launch.py'])),
        launch_arguments={
            'map': LaunchConfiguration('map'),
            'params_file': params,
            'use_sim_time': 'true',
            'autostart': 'true',
            'slam': 'False',
            'use_localization': 'True',
            # Sin zonas prohibidas ni de velocidad: no hay máscaras para la bodega.
            'use_keepout_zones': 'False',
            'use_speed_zones': 'False',
            'use_composition': composicion,
            'use_respawn': 'False',
            'log_level': 'info',
        }.items(),
    )

    # Nav2 espera unos segundos a que Gazebo, los controladores y el EKF estén arriba.
    # También va en grupo para que sus argumentos no se mezclen con los de este archivo.
    nav2_con_espera = TimerAction(period=LaunchConfiguration('espera_nav2'),
                                  actions=[GroupAction([nav2])])

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        arguments=['-d', PathJoinSubstitution([pkg, 'rviz', 'navegacion.rviz'])],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(LaunchConfiguration('rviz')),
    )

    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=PathJoinSubstitution([pkg, 'maps', 'bodega.yaml']),
                              description='Mapa de la Práctica 3'),
        DeclareLaunchArgument('params_file',
                              default_value=PathJoinSubstitution([pkg, 'config', 'nav2_params.yaml']),
                              description='Parámetros de Nav2'),
        DeclareLaunchArgument('gui', default_value='true', description='Abrir la ventana de Gazebo'),
        DeclareLaunchArgument('rviz', default_value='true', description='Abrir RViz'),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        DeclareLaunchArgument('use_composition', default_value='True',
                              description='Nav2 en un solo contenedor (menos procesos en WSL)'),
        DeclareLaunchArgument('espera_nav2', default_value='20.0',
                              description='Segundos antes de arrancar Nav2'),
        sim_ekf,
        nav2_con_espera,
        rviz,
    ])
