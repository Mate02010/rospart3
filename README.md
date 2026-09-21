# ROS 2 Parte 3: robot diferencial con Launch, TF2, URDF/Xacro, RViz y Gazebo Sim

**Curso:** Robótica, Escuela Colombiana de Ingeniería Julio Garavito\
**Autor:** Brayan Mateo Bravo L.\
**Entorno:** Ubuntu 24.04 (WSL2), ROS 2 Kilted, Gazebo Sim (Ionic)

Paquete ROS 2 `robotica_part3` desarrollado para la *Guía ROS 2 Parte 3* y su
mini-proyecto. El paquete construye un robot diferencial completo: geometría,
colisiones, inercias calculadas con macros, sensores (LiDAR, IMU y cámara),
visualización en RViz y simulación en Gazebo Sim con puente de tópicos a ROS 2.

---

## Video de demostración

<details>
<summary><b>▶ Ver video: el robot en RViz y en Gazebo Sim</b> (clic para abrir o cerrar)</summary>
<br>

<!-- VIDEO: reemplazar la línea siguiente por el enlace del video -->
*Video pendiente: se agregará en esta sección.*

</details>

---

## Contenido del repositorio

```
rospart3/
├── README.md
└── robotica_part3/                  Paquete ROS 2 (ament_cmake)
    ├── CMakeLists.txt
    ├── package.xml
    ├── launch/
    │   ├── turtle_mimic.launch.py        Actividad 1
    │   ├── main.launch.py                Actividad 2 (launch principal)
    │   ├── subs_events.launch.py         Actividad 2 (launch secundario)
    │   ├── display.launch.py             Actividad 7 (RViz)
    │   ├── gazebo_urdf_spawn.launch.py   Actividad 8 (URDF en Gazebo)
    │   ├── gazebo_sim.launch.py          Movimiento y sensores con puente ROS-GZ
    │   ├── display_rviz.launch.py        Auxiliar: RViz con configuración simple
    │   └── turtlesim_pair.launch.py      Auxiliar: dos TurtleSim (base de la Act. 1)
    ├── description/
    │   ├── simple_diff_robot.urdf.xacro  Actividad 4 (modelo principal)
    │   ├── inertials.xacro               Actividad 5 (macros de inercia)
    │   └── sensors.xacro                 Actividad 6 (LiDAR, IMU y cámara)
    ├── config/
    │   ├── urdf_config.rviz              Actividad 7
    │   ├── turtlesim_tf.rviz             Actividad 3 (frames de TurtleSim)
    │   └── simple_diff_robot.rviz
    └── worlds/
        ├── empty_world.sdf               Mundo vacío para ros_gz_sim create
        └── simple_diff_world.sdf         Robot SDF con diff-drive y sensores
```

> **Equivalencia de nombres con la guía:** la guía llama al paquete
> `dif_bot_description`, al modelo `dif_bot_description.urdf.xacro` y al launch
> `display_launch.py`. Aquí el paquete es `robotica_part3`, el modelo es
> `simple_diff_robot.urdf.xacro` y los launch siguen la convención de ROS 2
> `*.launch.py`.

## Actividades y archivos

| Actividad | Tema | Archivos |
|---|---|---|
| 1 | Launch, namespaces y remapeos | `launch/turtle_mimic.launch.py` |
| 2 | Argumentos, launch jerárquico, condiciones y eventos | `launch/main.launch.py`, `launch/subs_events.launch.py` |
| 3 | Exploración de TF2 | `config/turtlesim_tf.rviz` |
| 4 | Robot en URDF/Xacro con macro de ruedas | `description/simple_diff_robot.urdf.xacro` |
| 5 | Colisiones y macros de inercia (caja, cilindro y esfera) | `description/inertials.xacro` |
| 6 | Sensores (IMU, LiDAR y cámara) | `description/sensors.xacro` |
| 7 | Visualización en RViz | `launch/display.launch.py`, `config/urdf_config.rviz` |
| 8 | Integración con Gazebo Sim | `launch/gazebo_urdf_spawn.launch.py`, `worlds/empty_world.sdf` |
| Mini-proyecto | Movimiento y sensores con `ros_gz_bridge` | `launch/gazebo_sim.launch.py`, `worlds/simple_diff_world.sdf` |

## Árbol TF del robot

Salida de `check_urdf` sobre el URDF generado desde Xacro:

```
base_footprint
└── base_link                 chasis 0.45 x 0.30 x 0.12 m
    ├── left_wheel_link       rueda (joint continuous, eje Y)
    ├── right_wheel_link      rueda (joint continuous, eje Y)
    ├── caster_link           rueda loca (esfera)
    ├── laser_frame           LiDAR
    ├── imu_link              IMU
    └── camera_link           cámara
```

## Requisitos

```bash
sudo apt install ros-kilted-turtlesim ros-kilted-xacro \
  ros-kilted-robot-state-publisher ros-kilted-joint-state-publisher \
  ros-kilted-rviz2 ros-kilted-ros-gz \
  ros-kilted-turtle-tf2-py ros-kilted-tf2-tools
```

## Compilación

```bash
mkdir -p ~/robotica_ws/src && cd ~/robotica_ws/src
git clone https://github.com/Mate02010/rospart3.git
cd ~/robotica_ws
source /opt/ros/kilted/setup.bash
colcon build --packages-select robotica_part3 --symlink-install
source install/setup.bash
```

## Ejecución

**Actividad 1: dos TurtleSim y el nodo `mimic`**

```bash
ros2 launch robotica_part3 turtle_mimic.launch.py
# En otra terminal, mover la primera tortuga:
ros2 run turtlesim turtle_teleop_key --ros-args -r __ns:=/turtle1
```

**Actividad 2: launch jerárquico con argumentos, condición y eventos**

```bash
ros2 launch robotica_part3 main.launch.py \
  namespace:=turtle_params background_r:=200 spawn_extra_turtle:=true
```

**Actividad 3: TF2**

```bash
ros2 launch turtle_tf2_py turtle_tf2_demo.launch.py
ros2 run tf2_ros tf2_echo world turtle2
ros2 run tf2_tools view_frames
rviz2 -d $(ros2 pkg prefix robotica_part3)/share/robotica_part3/config/turtlesim_tf.rviz
```

**Actividades 4 a 7: el robot en RViz**

```bash
ros2 launch robotica_part3 display.launch.py
```

En RViz, desactivar *Visual Enabled* y activar *Collision Enabled* en el display
*RobotModel* para ver las colisiones.

**Actividad 8: el URDF en Gazebo Sim**

```bash
ros2 launch robotica_part3 gazebo_urdf_spawn.launch.py
```

El launch expande el Xacro a `/tmp/simple_diff_robot.urdf` y luego ejecuta:

```bash
ros2 run ros_gz_sim create -world default -file /tmp/simple_diff_robot.urdf \
  -name simple_diff_robot_urdf -x 0 -y 0 -z 0.15
```

**Mini-proyecto: movimiento y sensores**

```bash
ros2 launch robotica_part3 gazebo_sim.launch.py
# En otra terminal:
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.25}, angular: {z: 0.40}}"
ros2 topic list
ros2 topic echo /scan --once
```

Tópicos del puente (`]` va de ROS 2 a Gazebo y `[` de Gazebo a ROS 2):\
`/cmd_vel`, `/clock`, `/odom`, `/scan`, `/imu` y `/camera/image`.
