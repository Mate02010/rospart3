# Proyecto final – Misión autónoma por waypoints

## Qué hace

`scripts/mision.py` (nodo `mision`, Python):
- Lee la misión de `config/waypoints.yaml`: nombre, frame y una lista de puntos con nombre, x, y, orientación y
  tiempo de espera.
- Publica la pose inicial de AMCL, espera a que Nav2 esté activo y deja la misión lista. No arranca sola.
- Servicio `/iniciar_mision` (`std_srvs/srv/Trigger`): arranca la misión en un hilo aparte y responde de
  inmediato. Si ya hay una misión corriendo o Nav2 no está activo, responde `success: false`.
- Servicio `/cancelar_mision` (`std_srvs/srv/Trigger`): cancela la meta actual.
- Va a cada punto con `BasicNavigator.goToPose()` de `nav2_simple_commander`, mide tiempo y distancia, espera lo
  indicado y sigue con el siguiente.
- Publica el avance en `/estado_mision` (`std_msgs/String`) y los puntos en `/waypoints_mision` (marcadores de RViz).
- Al final guarda un JSON con el resultado de cada punto y un CSV con la ruta.

## Cómo se corre

```bash
ros2 launch dif_bot mision.launch.py                       # simulación + EKF + AMCL + Nav2 + RViz + nodo mision
ros2 topic echo /estado_mision                             # otra terminal: avance
ros2 service call /iniciar_mision std_srvs/srv/Trigger     # otra terminal: arranca la misión
```

Respuesta del servicio (`llamada_servicio.txt`):
`success=True, message="Misión iniciada: 'recorrido_bodega' con 6 waypoints"`

## Resultado

| # | Waypoint | Resultado | Tiempo | Recorrido | Error posición | Recuperaciones |
|---|---|---|---|---|---|---|
| 1 | Estante 3 (3.5, 2.0) | logrado | 13.8 s | 3.9 m | 24 cm | 0 |
| 2 | Carga sureste (3.5, −3.0) | logrado | 25.4 s | 4.9 m | 11 cm | 1 |
| 3 | Carga sur (0.5, −2.6) | logrado | 24.1 s | 5.8 m | 14 cm | 0 |
| 4 | Estante 2 (−4.0, −2.6) | logrado | 21.8 s | 4.9 m | 12 cm | 0 |
| 5 | Estante 1 (−4.0, 3.1) | logrado | 27.8 s | 7.8 m | 9 cm | 0 |
| 6 | Base (0, 0) | logrado | 18.8 s | 5.3 m | 24 cm | 0 |

**Total:** 6/6 waypoints, 32.6 m en 148 s de simulación (con 3 s de espera en cada punto) y una sola recuperación.

El error de posición se midió con la pose real de Gazebo. Suma la tolerancia de llegada de Nav2 (15 cm) y el error
de AMCL en ese momento (2 a 15 cm). El JSON guarda entre 13° y 24° de error de orientación porque lo toma cuando Nav2
da la meta por cumplida y el robot todavía está girando. Ya quieto, durante la espera de 3 s, quedó entre 0.8° y 6.6°
del yaw pedido en los puntos 1 a 5 (la base no tiene espera).

## Evidencias

- `mision_trayectoria.png`: ruta real y estimación de AMCL sobre el mapa, con los 6 waypoints.
- `mision_rviz_1.png`, `mision_rviz_2.png`, `mision_rviz_final.png`: RViz durante la misión. Se ven los costmaps,
  el plan, los waypoints numerados y el panel de Nav2.
- `estado_mision.txt`: todo lo que publicó `/estado_mision`, hasta `COMPLETADA: 6/6 waypoints en 147.8 s, 32.64 m`.
- `llamada_servicio.txt`, `servicios.txt`: llamada a `/iniciar_mision` y servicios del nodo.
- `info_nodos_topicos.txt`, `arbol_tf.pdf`: nodos, tópicos y árbol TF con todo corriendo.
- `resultados/`: JSON y CSV de la misión.

## Para el video (Gazebo + RViz + terminal)

1. Terminal 1: `ros2 launch dif_bot mision.launch.py` (abre Gazebo y RViz).
2. Terminal 2: `ros2 topic echo /estado_mision`.
3. Terminal 3: `ros2 service call /iniciar_mision std_srvs/srv/Trigger`.
4. Grabar las ventanas de Gazebo y RViz y las terminales mientras el robot pasa por los 6 puntos. Son unos 2.5 min,
   más largo si el PC va lento.
