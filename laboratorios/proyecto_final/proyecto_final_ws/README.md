# Proyecto final de Robótica – robot diferencial en una bodega

Robot diferencial simulado en Gazebo con ROS 2. El proyecto pasa por control y odometría, fusión de sensores con
EKF, mapeo con SLAM, localización con AMCL y navegación con Nav2, y termina en una misión autónoma por waypoints
que se inicia con un servicio.

Probado en Ubuntu 24.04 (WSL2), ROS 2 Kilted y Gazebo Sim 9 (Ionic).

## Paquete `dif_bot`

```
src/dif_bot/
├── description/   robot (xacro): ruedas, rueda loca, LiDAR, IMU, cámara opcional
│                  gz_control.xacro (plugin DiffDrive de Gazebo) / ros2_control.xacro
├── worlds/        bodega.sdf: bodega de 12 × 8 m con muros, estanterías, cajas y columnas
├── config/        controladores, ekf.yaml, slam_toolbox.yaml, amcl.yaml, nav2_params.yaml, waypoints.yaml
├── launch/        sim, ekf, slam, localizacion, navegacion, mision
├── maps/          mapa de la bodega hecho con SLAM (bodega.yaml/.pgm)
├── rviz/          una configuración por práctica
└── scripts/       nodo de la misión y scripts de medición y gráficas
```

## Dependencias y compilación

```bash
sudo apt install ros-kilted-ros-gz ros-kilted-gz-ros2-control ros-kilted-ros2-controllers \
  ros-kilted-robot-localization ros-kilted-slam-toolbox ros-kilted-navigation2 ros-kilted-nav2-bringup \
  ros-kilted-teleop-twist-keyboard ros-kilted-xacro python3-matplotlib
source /opt/ros/kilted/setup.bash
cd proyecto_final_ws
colcon build --symlink-install
source install/setup.bash
```

## Prácticas

| Práctica | Comando | Qué se ve |
|---|---|---|
| 1. Control y odometría | `ros2 launch dif_bot sim.launch.py use_ros2_control:=false` (o `:=true`) | plugin DiffDrive de Gazebo vs `diff_drive_controller` |
| 2. EKF | `ros2 launch dif_bot ekf.launch.py` (`usar_imu:=false` para la prueba sin IMU) | `/odom_filtered` y TF `odom → base_footprint` |
| 3. SLAM | `ros2 launch dif_bot slam.launch.py` | mapa con slam_toolbox; guardar con `map_saver_cli` |
| 4. AMCL | `ros2 launch dif_bot localizacion.launch.py` (`ruido_laser:=0.15`) | partículas sobre `maps/bodega.yaml` |
| 5. Nav2 | `ros2 launch dif_bot navegacion.launch.py` | metas con "Nav2 Goal" en RViz |
| Final | `ros2 launch dif_bot mision.launch.py` | misión por waypoints |

En la práctica 1 con `use_ros2_control:=true` los controladores se activan a mano:

```bash
ros2 control load_controller --set-state active joint_state_broadcaster
ros2 control load_controller --set-state active diff_drive_controller
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args -p stamped:=true -r /cmd_vel:=/diff_drive_controller/cmd_vel
```

Argumentos útiles en todos los launch: `gui:=false` (Gazebo sin ventana) y `rviz:=false`.

## Misión final

```bash
ros2 launch dif_bot mision.launch.py
ros2 topic echo /estado_mision                            # otra terminal
ros2 service call /iniciar_mision std_srvs/srv/Trigger    # arranca la misión
ros2 service call /cancelar_mision std_srvs/srv/Trigger   # la detiene
```

Los waypoints están en `src/dif_bot/config/waypoints.yaml`. Se pueden cambiar sin recompilar el código:
`ros2 launch dif_bot mision.launch.py waypoints:=/ruta/otra_mision.yaml`.

## Scripts de medición

| Script | Práctica | Qué mide |
|---|---|---|
| `medir_odom.py` | 1 | latencia, jitter, ruido y error de la odometría contra la pose real de Gazebo |
| `comparar_ekf.py`, `graficar_p2.py` | 2 | ruedas vs EKF vs pose real en un cuadrado |
| `explorar.py`, `evaluar_mapa.py` | 3 | recorrido automático para SLAM y error del mapa contra el SDF |
| `evaluar_amcl.py`, `graficar_p4.py` | 4 | convergencia de AMCL con pose correcta, incorrecta y con ruido |
| `probar_nav.py`, `graficar_p5.py` | 5 | metas seguidas, caja sobre el camino y meta bloqueada |
| `graficar_mision.py` | final | ruta de la misión sobre el mapa |

La pose real sale de `/ground_truth/odom` (plugin OdometryPublisher de Gazebo). Se usa para medir y para
manejar el robot en los recorridos automáticos de las prácticas 3 y 4, que reemplazan la teleoperación para que
cada prueba se pueda repetir igual. SLAM, AMCL y Nav2 no la leen; el nodo `mision` la lee solo para registrar la
distancia recorrida y el error de llegada, no para navegar.
