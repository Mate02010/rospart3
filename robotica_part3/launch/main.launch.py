from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo, RegisterEventHandler
from launch.event_handlers import OnShutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    namespace_argument = DeclareLaunchArgument(
        'namespace', default_value='turtle_params',
        description='Namespace de la TurtleSim creada por el launch secundario.',
    )
    background_argument = DeclareLaunchArgument(
        'background_r', default_value='180',
        description='Componente roja del fondo de TurtleSim (0 a 255).',
    )
    spawn_argument = DeclareLaunchArgument(
        'spawn_extra_turtle', default_value='false',
        description='Crea una segunda tortuga después del inicio cuando vale true.',
    )

    secondary_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare('robotica_part3'),
                'launch',
                'subs_events.launch.py',
            ])
        ),
        launch_arguments={
            'namespace': LaunchConfiguration('namespace'),
            'background_r': LaunchConfiguration('background_r'),
            'spawn_extra_turtle': LaunchConfiguration('spawn_extra_turtle'),
        }.items(),
    )

    startup_message = LogInfo(
        msg=['Iniciando main.launch.py con namespace: ', LaunchConfiguration('namespace')]
    )

    shutdown_event = RegisterEventHandler(
        OnShutdown(
            on_shutdown=[
                LogInfo(msg='Launch jerárquico finalizado correctamente.'),
            ]
        )
    )

    return LaunchDescription([
        namespace_argument,
        background_argument,
        spawn_argument,
        startup_message,
        shutdown_event,
        secondary_launch,
    ])
