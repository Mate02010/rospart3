# Práctica 2 – EKF con robot_localization

## Cómo se corrió

```bash
ros2 launch dif_bot ekf.launch.py                   # ruedas + IMU
ros2 launch dif_bot ekf.launch.py usar_imu:=false   # solo ruedas
# Prueba: cuadrado de 1 m, 2 vueltas (v = 0.3 m/s, giros de 90° a 0.6 rad/s)
ros2 run dif_bot comparar_ekf.py --ros-args -p use_sim_time:=true -p etiqueta:=con_imu
```

`config/ekf.yaml`: filtro a 50 Hz en modo 2D, `world_frame: odom`.
`comparar_ekf.py` guarda la pose de las ruedas, del EKF y la real de Gazebo, medidas desde donde arrancó el robot.

## Resultados (cuadrado, 2 vueltas)

| | Error final posición | Error RMS posición | Error final yaw | Error máx. yaw |
|---|---|---|---|---|
| Odometría ruedas | 5.8 cm | 3.9 cm | 3.5° | 7.7° |
| EKF con IMU | 1.2 cm | 3.3 cm | 0.0° | 0.8° |
| EKF sin IMU | 20.1 cm | 9.4 cm | 15.3° | 15.3° |

Gráfica: `p2_comparacion_ekf.png`. Datos: `resultados/p2_con_imu.*`, `resultados/p2_sin_imu.*`.

## Respuestas

**¿Qué sensores se fusionan?**
La odometría de las ruedas (`/diff_drive_controller/odom`: velocidad lineal vx, vy y velocidad angular) y la IMU
(`/imu`: orientación yaw y velocidad angular en z). De las ruedas se toman velocidades y no la posición, para que
el filtro las integre y la orientación absoluta venga solo de la IMU.

**¿Qué frame publica el EKF?**
Publica `/odom_filtered` en el frame `odom` con `child_frame_id: base_footprint`, y el TF `odom → base_footprint`.
Para que no haya dos nodos publicando la misma transformación se apagó el TF del controlador
(`enable_odom_tf: false` en `controllers_ekf.yaml`; el controlador sigue apareciendo como publicador de `/tf`
pero ya no envía esa transformación). Se ve en `con_imu/info_nodos_topicos.txt` (publicador de `/odom_filtered`:
`ekf_filter_node`) y en `con_imu/arbol_tf.pdf`.

**¿Qué ocurre si se desactiva la IMU?**
El filtro queda solo con la velocidad de las ruedas y nada corrige el rumbo: el error de orientación crece en
cada giro (15° al final, contra 0° con IMU) y eso lleva el error de posición a 20 cm. Sin IMU el EKF quedó incluso
peor que la odometría sola, porque integra la velocidad que publica el controlador (promediada y con 2.8 ms de
jitter) y no la posición de los encoders; en una corrida con el PC cargado llegó a 35°
(`resultados/p2_sin_imu_corrida1.json`). Con la IMU el yaw queda amarrado a una medida absoluta y el error ya no
se acumula.

## Evidencias

- `p2_comparacion_ekf.png`: trayectorias (real, ruedas, EKF) y error de yaw en el tiempo, con y sin IMU.
- `p2_rviz_ekf.png`: RViz con las flechas de la odometría de ruedas (azul) y del EKF (verde) en el cuadrado.
- `p2_gazebo.png`: robot en la bodega.
- `con_imu/`, `sin_imu/`: nodos, tópicos (`ros2 topic info -v`) y árbol TF de cada caso.
- `resultados/`: CSV y JSON de cada corrida (incluye las dos corridas sin IMU con el filtro a 30 Hz).
