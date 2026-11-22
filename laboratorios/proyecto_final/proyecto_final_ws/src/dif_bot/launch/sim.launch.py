"""Simulación del dif_bot en Gazebo con dos formas de control.

Uso:
  ros2 launch dif_bot sim.launch.py use_ros2_control:=false   # plugin DiffDrive de Gazebo
  ros2 launch dif_bot sim.launch.py use_ros2_control:=true    # ros2_control

Con ros2_control los controladores se activan a mano (como pide la guía):
  ros2 control load_controller --set-state active joint_state_broadcaster
  ros2 control load_controller --set-state active diff_drive_controller
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.conditions import IfCondition, UnlessCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, LaunchConfiguration, PathJoinSubstitution, PythonExpression
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg = FindPackageShare('dif_bot')
    use_ros2_control = LaunchConfiguration('use_ros2_control')
    world = LaunchConfiguration('world')
    rviz = LaunchConfiguration('rviz')
    gui = LaunchConfiguration('gui')
    camara = LaunchConfiguration('camara')
    controladores = LaunchConfiguration('controladores')
    x = LaunchConfiguration('x')
    y = LaunchConfiguration('y')
    yaw = LaunchConfiguration('yaw')
    activar_controladores = LaunchConfiguration('activar_controladores')
    rviz_config = LaunchConfiguration('rviz_config')
    ruido_laser = LaunchConfiguration('ruido_laser')
    cmd_vel_global = LaunchConfiguration('cmd_vel_global')

    # URDF generado desde Xacro; el argumento escoge el sistema de control.
    robot_description = ParameterValue(
        Command([
            'xacro ', PathJoinSubstitution([pkg, 'description', 'robot.urdf.xacro']),
            ' use_ros2_control:=', use_ros2_control,
            ' camara:=', camara,
            ' ruido_laser:=', ruido_laser,
            ' controllers_file:=', controladores,
        ]),
        value_type=str,
    )

    gz_launch = PathJoinSubstitution([FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py'])
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gz_launch),
        launch_arguments={'gz_args': ['-r -v 2 ', world], 'on_exit_shutdown': 'true'}.items(),
        condition=IfCondition(gui),
    )
    # Sin ventana de Gazebo (más rápido para mediciones).
    gazebo_sin_gui = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(gz_launch),
        launch_arguments={'gz_args': ['-r -s --headless-rendering -v 2 ', world],
                          'on_exit_shutdown': 'true'}.items(),
        condition=UnlessCondition(gui),
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description, 'use_sim_time': True}],
    )

    spawn = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=['-topic', 'robot_description', '-name', 'dif_bot',
                   '-x', x, '-y', y, '-z', '0.02', '-Y', yaw],
    )

    # El puente cambia según quién controla el robot.
    bridge_gz = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        output='screen',
        parameters=[{'config_file': PathJoinSubstitution([pkg, 'config', 'bridge_gz_control.yaml']),
                     'use_sim_time': True}],
        condition=UnlessCondition(use_ros2_control),
    )
    bridge_ros2_control = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        output='screen',
        parameters=[{'config_file': PathJoinSubstitution([pkg, 'config', 'bridge_ros2_control.yaml']),
                     'use_sim_time': True}],
        condition=IfCondition(use_ros2_control),
    )

    # En P1 los controladores se activan a mano; desde P2 los activa el spawner.
    spawner = Node(
        package='controller_manager',
        executable='spawner',
        output='screen',
        arguments=['joint_state_broadcaster', 'diff_drive_controller',
                   # Con la CPU cargada la activación tarda: se le da margen al cambio de estado.
                   '--controller-manager-timeout', '120', '--switch-timeout', '30', '--service-call-timeout', '30'],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(PythonExpression(
            ["'", use_ros2_control, "' == 'true' and '", activar_controladores, "' == 'true' and '",
             cmd_vel_global, "' != 'true'"])),
    )
    # Con Nav2 el controlador escucha /cmd_vel (TwistStamped), que es donde Nav2 publica.
    spawner_cmd_vel_global = Node(
        package='controller_manager',
        executable='spawner',
        output='screen',
        arguments=['joint_state_broadcaster', 'diff_drive_controller',
                   '--controller-manager-timeout', '120', '--switch-timeout', '30', '--service-call-timeout', '30',
                   '--controller-ros-args', '-r /diff_drive_controller/cmd_vel:=/cmd_vel'],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(PythonExpression(
            ["'", use_ros2_control, "' == 'true' and '", activar_controladores, "' == 'true' and '",
             cmd_vel_global, "' == 'true'"])),
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        arguments=['-d', rviz_config],
        parameters=[{'use_sim_time': True}],
        condition=IfCondition(rviz),
    )

    aviso_ros2_control = LogInfo(
        condition=IfCondition(use_ros2_control),
        msg=('[dif_bot] Modo ros2_control. Activa los controladores en otra terminal:\n'
             '  ros2 control load_controller --set-state active joint_state_broadcaster\n'
             '  ros2 control load_controller --set-state active diff_drive_controller\n'
             'Teleoperación: ros2 run teleop_twist_keyboard teleop_twist_keyboard '
             '--ros-args -p stamped:=true -r /cmd_vel:=/diff_drive_controller/cmd_vel'),
    )
    aviso_gz = LogInfo(
        condition=UnlessCondition(use_ros2_control),
        msg=('[dif_bot] Modo plugin de Gazebo (DiffDrive). '
             'Teleoperación: ros2 run teleop_twist_keyboard teleop_twist_keyboard'),
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_ros2_control', default_value='false',
                              description='true: ros2_control | false: plugin DiffDrive de Gazebo'),
        DeclareLaunchArgument('world', default_value=PathJoinSubstitution([pkg, 'worlds', 'bodega.sdf']),
                              description='Mundo de Gazebo'),
        DeclareLaunchArgument('rviz', default_value='true', description='Abrir RViz'),
        DeclareLaunchArgument('gui', default_value='true', description='Abrir la ventana de Gazebo'),
        DeclareLaunchArgument('camara', default_value='false', description='Simular la cámara'),
        DeclareLaunchArgument('controladores',
                              default_value=PathJoinSubstitution([pkg, 'config', 'controllers.yaml']),
                              description='YAML de ros2_control'),
        DeclareLaunchArgument('x', default_value='0.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        DeclareLaunchArgument('activar_controladores', default_value='false',
                              description='true: activa los controladores con el spawner'),
        DeclareLaunchArgument('rviz_config',
                              default_value=PathJoinSubstitution([pkg, 'rviz', 'dif_bot.rviz']),
                              description='Configuración de RViz'),
        DeclareLaunchArgument('ruido_laser', default_value='0.01',
                              description='Desviación estándar del ruido del LiDAR [m]'),
        DeclareLaunchArgument('cmd_vel_global', default_value='false',
                              description='true: el diff_drive_controller escucha /cmd_vel (para Nav2)'),
        gazebo,
        gazebo_sin_gui,
        robot_state_publisher,
        spawn,
        bridge_gz,
        bridge_ros2_control,
        spawner,
        spawner_cmd_vel_global,
        rviz_node,
        aviso_ros2_control,
        aviso_gz,
    ])
