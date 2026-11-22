# Práctica 3 – Mapeo con SLAM

## Cómo se corrió

```bash
ros2 launch dif_bot slam.launch.py                      # EKF + slam_toolbox (online async) + RViz
# Recorrido automático por la bodega (reemplaza la teleoperación para poder repetirlo igual)
ros2 run dif_bot explorar.py --ros-args -p use_sim_time:=true -p v:=0.15 -p w_max:=0.4 -p etiqueta:=lento
# Guardar el mapa
ros2 run nav2_map_server map_saver_cli -f <paquete>/maps/bodega --ros-args -p use_sim_time:=true
# Comparar el mapa con la geometría real del mundo
python3 scripts/evaluar_mapa.py maps/bodega.yaml worlds/bodega.sdf ~/proyecto_final_ws/resultados --etiqueta lento
```

La misma ruta (15 puntos, 53.5 m, recorre todos los pasillos) se hizo a tres velocidades, cada una con un SLAM nuevo.
El mapa que usan las prácticas 4 y 5 es `maps/bodega.yaml` (corrida lenta).

## Resultados

| Corrida | v máx / w máx | Tiempo | Error medio | Error p95 | Bordes mapeados | Celdas espurias |
|---|---|---|---|---|---|---|
| Lenta | 0.15 m/s / 0.4 rad/s | 436 s | 3.0 cm | 6.0 cm | 100 % | 0 |
| Rápida | 0.45 m/s / 1.2 rad/s | 193 s | 2.7 cm | 5.7 cm | 100 % | 0 |
| Muy rápida | 1.0 m/s / 2.5 rad/s | 144 s | 2.6 cm | 4.9 cm | 100 % | 0 |

Error = distancia de cada celda ocupada del mapa a la superficie real más cercana (sacada del SDF).

## Respuestas

**¿Qué resolución tiene el mapa?**
0.05 m por celda (`resolution: 0.05` en `slam_toolbox.yaml` y en `maps/bodega.yaml`). El mapa queda de
239 × 160 celdas (11.95 × 8.0 m), que es la bodega completa.

**¿Qué errores se observan en el mapa?**
- Los bordes quedan en promedio 3 cm (media celda) corridos y a veces con una celda de más hacia afuera.
- Los muros interiores, de 15 cm de grosor, salen punteados: el láser los ve casi de canto y el muro cae entre celdas.
- Las cajas giradas quedan con bordes escalonados por la rejilla de 5 cm.
- Cerca del 2 % del piso queda desconocido: son las zonas que el láser no alcanza a ver detrás de los obstáculos.

No aparecieron paredes dobles ni obstáculos falsos (0 celdas espurias).

**¿Cómo afecta la velocidad del robot?**
En simulación casi no se nota: a 1.0 m/s el mapa quedó tan bien como a 0.15 m/s, y en menos de la tercera parte
del tiempo. Hay tres razones:
- El LiDAR de Gazebo toma cada barrido de forma instantánea, así que no se deforma con el movimiento.
- La odometría del EKF con IMU casi no deriva.
- slam_toolbox solo agrega un barrido cada 0.3 m o 0.3 rad, y a 10 Hz siempre hay barridos de sobra.

En un robot real sí afecta. Un barrido dura 0.1 s, y a 1 m/s el robot avanza 10 cm (o gira 14° a 2.5 rad/s) mientras lo
toma. Las paredes salen torcidas o dobles y el scan matching y el cierre de lazo fallan más. Además, a más velocidad
hay más deslizamiento de las ruedas. Por eso conviene mapear despacio y, sobre todo, girar despacio.

## Evidencias

- `p3_slam_en_progreso.png`, `p3_slam_final_lento.png`, `p3_slam_final_rapido.png`: RViz durante y al final del mapeo.
- `resultados/p3_mapa_*.png`: cada mapa con los obstáculos reales encima (azul) y la ruta del robot (verde).
- `resultados/p3_mapa_*.json`, `resultados/p3_ruta_*.json/csv`: métricas del mapa y de la ruta.
- `lento/`, `rapido/`, `muy_rapido/`: nodos, tópicos y árbol TF con SLAM (map → odom → base_footprint).
- Mapas: `proyecto_final_ws/src/dif_bot/maps/bodega*.yaml/.pgm`.
