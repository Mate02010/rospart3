# Práctica 5 – Navegación con Nav2

## Cómo se corrió

```bash
ros2 launch dif_bot navegacion.launch.py      # EKF + AMCL (maps/bodega.yaml) + Nav2 + RViz
# Metas desde RViz con "Nav2 Goal", o la prueba automática (3 metas seguidas):
ros2 run dif_bot probar_nav.py --ros-args -p use_sim_time:=true
ros2 run dif_bot probar_nav.py --ros-args -p use_sim_time:=true -p obstaculo:=true      # caja sobre el camino
ros2 run dif_bot probar_nav.py --ros-args -p use_sim_time:=true -p bloquear_meta:=true  # caja encima de la meta
# Plugins activos
ros2 param get /planner_server GridBased.plugin
ros2 param get /controller_server FollowPath.plugin
ros2 param get /bt_navigator default_nav_to_pose_bt_xml
```

`config/nav2_params.yaml` parte de los parámetros de `nav2_bringup` en Kilted. Lo que se cambió:
- Huella rectangular del robot, inflado de 0.45 m y odometría `/odom_filtered`.
- Controlador Regulated Pure Pursuit a 0.35 m/s.
- La cadena de velocidad termina en `/cmd_vel` (TwistStamped), que escucha el `diff_drive_controller`.

Metas: M1 (3.5, −2.0), M2 (−4.0, 0.25), M3 (−2.3, 2.9).

## Resultados

| Corrida | Metas logradas | Distancia | Tiempo | Recuperaciones | Error final |
|---|---|---|---|---|---|
| Sin obstáculo | 3/3 | 16.0 m | 57 s | 0 | 12–13 cm |
| Caja sobre el camino a M2 | 3/3 | 16.0 m | 55 s | 0 | 13–18 cm |
| Caja de 1 m encima de M2 | 2/3 | 60.6 m | 268 s | 14 (1 spin) | M2 sin lograr |

El error final se mide contra la pose real de Gazebo. Suma la tolerancia del goal checker (0.15 m, aplicada a la
estimación de AMCL) y el error de AMCL, por eso algunas metas quedan un poco por encima de 0.15 m.
Gráfica: `p5_trayectorias.png` (plan global y recorrido real sobre el mapa).

## Respuestas

**¿Qué planificador se usa por defecto?**
NavFn (`nav2_navfn_planner::NavfnPlanner`, plugin `GridBased`). Calcula el camino más corto sobre el costmap
global con Dijkstra (`use_astar: false`), y deja de 0.5 m de tolerancia si la meta cae en una celda ocupada.
Lo mismo se ve con `ros2 param get` en `sin_obstaculo/plugins_nav2.txt`.

El controlador por defecto de Kilted es MPPI. Se cambió por Regulated Pure Pursuit porque es más liviano (en WSL
la CPU ya va cargada con Gazebo) y sirve bien para un robot diferencial.

**¿Qué comportamientos de recuperación hay y qué pasa cuando el robot se bloquea?**
El BT por defecto es `navigate_to_pose_w_replanning_and_recovery.xml`. Recalcula el plan a 1 Hz y, si el
planificador o el controlador fallan, limpia el costmap correspondiente y reintenta. Si sigue fallando, hace por
turnos (RoundRobin) estas recuperaciones, hasta 6 reintentos:
1. Limpiar los costmaps local y global.
2. Spin de 90°.
3. Wait de 5 s.
4. BackUp de 0.30 m.

El `behavior_server` tiene cargados `spin`, `backup`, `drive_on_heading`, `wait` y `assisted_teleop`.

En las pruebas pasó esto:
- **Caja sobre el camino:** no hizo falta recuperar. La caja apareció cuando el robot iba hacia M2, el costmap la
  marcó con el láser y el plan global la rodeó 0.65 s después. El robot la esquivó y llegó.
- **Caja encima de la meta:** no hay ningún punto libre cerca de M2, así que el plan falla. El BT limpia los
  costmaps, y al borrar el obstáculo el planificador vuelve a encontrar camino hasta que el láser ve la caja otra vez.
  Por eso el robot le dio vueltas a la caja (52 m) con 14 recuperaciones, entre ellas un spin, hasta que la prueba
  canceló la meta a los 240 s.
- Después siguió con M3 sin problema.

## Evidencias

- `p5_trayectorias.png`: plan global y recorrido de las tres corridas.
- `sin_obstaculo/`, `con_obstaculo/`, `meta_bloqueada/`: nodos, tópicos de la cadena de velocidad
  (`/cmd_vel_nav` → `/cmd_vel_smoothed` → `/cmd_vel`), árbol TF y `plugins_nav2.txt`.
- `resultados/`: JSON y CSV de cada corrida (resultado por meta, tiempos, recuperaciones y eventos).
- `resultados/p5_sin_obstaculo_tolerancia_0.1.*`: primera corrida, con la tolerancia de TF de 0.1 s. M3 falló
  por TF atrasado con la CPU cargada; por eso se subió la tolerancia a 0.5 s.
