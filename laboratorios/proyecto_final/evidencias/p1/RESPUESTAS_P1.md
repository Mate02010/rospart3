# Práctica 1 – Control y odometría

## Cómo se corrió

```bash
# Plugin DiffDrive de Gazebo
ros2 launch dif_bot sim.launch.py use_ros2_control:=false
# ros2_control
ros2 launch dif_bot sim.launch.py use_ros2_control:=true
ros2 control load_controller --set-state active joint_state_broadcaster
ros2 control load_controller --set-state active diff_drive_controller
# Medición (escalón de velocidad y comparación con la pose real de Gazebo)
ros2 run dif_bot medir_odom.py --ros-args -p use_sim_time:=true -p modo:=gz -p v:=0.3 -p w:=0.0
ros2 run dif_bot medir_odom.py --ros-args -p use_sim_time:=true -p modo:=ros2_control -p v:=0.0 -p w:=0.8
```

`medir_odom.py` manda una velocidad constante por 4 s, frena y compara la odometría con `/ground_truth/odom`
(pose real que publica Gazebo con el plugin OdometryPublisher).

## Resultados

| | Plugin de Gazebo | ros2_control |
|---|---|---|
| Recta 0.3 m/s × 4 s (odom / real) | 1.156 / 1.156 m | 1.200 / 1.200 m |
| Latencia al 50 % / 90 % (recta) | 0.20 / 0.32 s | 0.28 / 0.42 s |
| Latencia al 50 % / 90 % (giro) | 0.26 / 0.42 s | 0.34 / 0.50 s |
| Frecuencia / jitter de la odometría | 50 Hz / 0 ms | 50 Hz / 2.8 ms |
| Ruido en vx con velocidad constante | 0 | 0.005 m/s |
| Giro 0.8 rad/s × 4 s (odom / real) | 175.2° / 179.4° | 184.4° / 192.2° |

Datos completos en `resultados/*.json`. Antes de medir se corrigió el centro de masa del robot: estaba
delante del eje de las ruedas y el robot se apoyaba en la nariz (la IMU marcaba 15° de inclinación en reposo).

## Respuestas

**¿Qué controlador genera la odometría?**
Con el plugin la calcula el sistema DiffDrive dentro de Gazebo y el `ros_gz_bridge` la pasa a `/odom` y `/tf`.
Con ros2_control la calcula el `diff_drive_controller` (dentro del `controller_manager`) a partir de la posición
de las ruedas que entrega `GazeboSimSystem`; publica `/diff_drive_controller/odom` y el TF `odom → base_footprint`.
Se ve en `modo_*/info_nodos_topicos.txt` y en `modo_*/arbol_tf.pdf`.

**¿Qué diferencias hay en estabilidad y latencia?**
El plugin responde unos 80 ms antes y su odometría no tiene ruido ni jitter porque sale directo del estado del
simulador. Con ros2_control el comando pasa por el ciclo del `controller_manager` (50 Hz) y la velocidad se
deriva de los encoders, por eso aparece un poco de ruido (0.005 m/s) y 2.8 ms de jitter. En línea recta los dos
aciertan casi exacto. En el giro sobre su eje los dos se quedan cortos frente al giro real (4° con el plugin y
8° con ros2_control en media vuelta) porque las ruedas patinan de lado al girar; ese error de orientación es
el que luego corrige la IMU en el EKF (práctica 2).

**¿Cuál es más adecuado para un robot real?**
ros2_control. El controlador, la odometría y los tópicos son los mismos en simulación y en el robot; solo se
cambia el plugin de hardware (`GazeboSimSystem` por el driver de los motores). El plugin DiffDrive solo existe
dentro de Gazebo. Por eso las prácticas siguientes usan ros2_control.

## Evidencias

- `p1_plugin_gazebo.png`, `p1_plugin_rviz.png`: modo plugin (bodega, láser, cámara y odometría en RViz).
- `p1_ros2_control_gazebo.png`, `p1_ros2_control_rviz.png`: modo ros2_control.
- `modo_plugin_gazebo/`, `modo_ros2_control/`: nodos, tópicos (`ros2 topic info -v`) y árbol TF.
- `modo_ros2_control/activar_controladores.txt`: salida de `ros2 control load_controller`.
