# Práctica 4 – Localización con AMCL

## Cómo se corrió

```bash
ros2 launch dif_bot localizacion.launch.py                    # EKF + map_server (maps/bodega.yaml) + AMCL + RViz
ros2 launch dif_bot localizacion.launch.py ruido_laser:=0.15  # láser 15 veces más ruidoso
# Experimento: da la pose inicial, recorre una ruta corta y compara AMCL con la pose real de Gazebo
ros2 run dif_bot evaluar_amcl.py --ros-args -p use_sim_time:=true -p etiqueta:=pose_correcta
ros2 run dif_bot evaluar_amcl.py --ros-args -p use_sim_time:=true -p etiqueta:=pose_incorrecta \
    -p x0:=1.0 -p y0:=-0.8 -p yaw0:=0.6
# Localización global (partículas en todo el mapa)
ros2 service call /reinitialize_global_localization std_srvs/srv/Empty "{}"
```

`config/amcl.yaml`: modelo diferencial, 500 a 3000 partículas, láser `likelihood_field` hasta 12 m.
El robot arranca siempre en (0, 0, 0). Se considera que AMCL converge cuando el error baja de 0.15 m y de 5°
durante 2 s seguidos.

## Resultados

| Experimento | Error inicial | ¿Converge? | Tiempo / recorrido | Error RMS después | Error final |
|---|---|---|---|---|---|
| Pose correcta, ruido 0.01 m | 2 cm | sí | inmediato | 3.5 cm / 0.6° | 3 cm |
| Pose incorrecta (1.3 m, 34°) | 1.28 m / 34° | sí | 8.2 s / 1.1 m | 3.2 cm / 0.6° | 2.6 cm |
| Pose muy lejos (4.1 m, 143°) | 4.07 m / 143° | no | – | – | 3.5 m / 134° |
| Ruido del láser 0.15 m | 0.5 cm | sí | inmediato | 4.3 cm / 1.1° | 3.7 cm / 1.6° |
| Localización global | partículas en todo el mapa | sí | 1 vuelta + 1.2 m | – | 3 cm / 0.5° |

Gráficas: `p4_pose_inicial.png`, `p4_pose_muy_lejos.png`, `p4_ruido.png`. Datos: `resultados/`.

## Respuestas

**¿Qué ocurre si la pose inicial es incorrecta?**
Depende de qué tan lejos esté.
- Con un error pequeño (1.3 m y 34°) las partículas, que se reparten alrededor de la pose dada, alcanzan a cubrir
  la pose real. Al moverse el robot, el láser va descartando las que no coinciden con el mapa y AMCL corrige solo:
  en 8 s y 1.1 m quedó con 3 cm de error.
- Con un error grande (4 m, otro cuarto de la bodega y 143° de giro) ninguna partícula queda cerca de la pose
  real. AMCL se queda en un lugar falso y termina con 3.5 m de error.
- Para ese caso hay que dar la pose de nuevo con "2D Pose Estimate" o pedir localización global
  (`/reinitialize_global_localization`). Con eso las partículas se reparten por todo el mapa y con una vuelta en el
  sitio más 1.2 m de recorrido se ubicó con 3 cm de error (`p4_global_particulas_repartidas.png`).

**¿Cómo afecta el ruido del láser?**
Con 15 veces más ruido (0.15 m de desviación) AMCL sigue localizado, pero con más error: el de orientación se
duplica (RMS 1.1° contra 0.6°) y el de posición sube de 3.5 a 4.3 cm. Las medidas ruidosas encajan peor con el
mapa, los pesos de las partículas se parecen más entre sí y la nube queda más dispersa. Con ruido aún mayor, o
con una pose inicial dudosa, tardaría más en converger y sería más fácil que se pierda.

## Evidencias

- `p4_pose_inicial.png`: error de AMCL en el tiempo con pose correcta y con pose incorrecta.
- `p4_pose_muy_lejos.png`: AMCL perdido cuando la pose inicial está en otra zona.
- `p4_ruido.png`: error con ruido del láser de 0.01 m y 0.15 m.
- `p4_global_particulas_repartidas.png`: RViz justo después de pedir la localización global.
- `p4_pose_incorrecta_convergida.png`: RViz con AMCL ya corregido (el láser cae sobre las paredes del mapa).
- `pose_correcta/`, `pose_incorrecta/`, `pose_muy_lejos/`, `ruido_alto/`, `global/`: nodos, tópicos y árbol TF
  (map → odom de AMCL, odom → base_footprint del EKF).
- `resultados/`: CSV y JSON de cada experimento. La localización global se hizo moviendo el robot a mano y sus
  números están en `p4_global_manual.json`.
