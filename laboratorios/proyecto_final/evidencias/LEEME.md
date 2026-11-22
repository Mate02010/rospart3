# Evidencias del proyecto final

Cada carpeta trae un `RESPUESTAS_*.md` con los comandos, la tabla de resultados, las respuestas a las preguntas de
la guía y la lista de archivos.

| Carpeta | Contenido principal |
|---|---|
| `p1/` | plugin de Gazebo vs ros2_control: latencia, jitter, error de odometría; capturas de Gazebo y RViz |
| `p2/` | EKF con y sin IMU: `p2_comparacion_ekf.png`, RViz con las dos odometrías |
| `p3/` | SLAM a 3 velocidades: mapas con los obstáculos reales encima, capturas de RViz |
| `p4/` | AMCL: pose correcta, incorrecta, muy lejos, ruido del láser y localización global |
| `p5/` | Nav2: 3 metas sin obstáculo, con caja en el camino y con la meta bloqueada |
| `final/` | misión de 6 waypoints iniciada por servicio: ruta, estado y capturas |

En cada experimento también está `info_nodos_topicos.txt` (`ros2 node list` y `ros2 topic info -v`) y
`arbol_tf.pdf` (`view_frames`).

Los scripts con los que se corrieron las pruebas en WSL están en `../herramientas/`.
