# Resultados registrados

Datos procedentes de `resultados/resultado_topics.json` y `resultados/resultado_moveit.json`. Son los mismos registros que sustentaron los videos originales; la reorganización de carpetas no representa una nueva ejecución de las rutinas.

| Medida | Tópicos ROS | Nodo MoveIt |
|---|---:|---:|
| Movimientos completados | 8/8 | 8/8 |
| Objetivos distintos del brazo | 4 | 4 |
| Planes MoveIt exitosos | No aplica | 8/8 |
| Máximo error final del brazo | 0.019704 rad | 0.000937 rad |
| Máximo error final de los dedos | 0.001949 m | 0.000949 m |
| Tiempo entre primer y último evento | 70.9 s | 53.5 s |
| Confirmación digital | Recibida | Recibida |

El error es el máximo absoluto entre articulaciones del grupo al registrar `motion_success`; no es el pico instantáneo de error durante toda la trayectoria. Se exige error menor que 0.02 rad o 0.002 m durante cuatro actualizaciones consecutivas. Los tiempos son de pared e incluyen la espera digital, y no coinciden con la duración de la grabación completa.

## Pruebas de interfaz

- Setup Assistant: generación del paquete, grupos y matriz de colisiones documentados en el video 01 y en las figuras del proyecto LaTeX.
- RViz: `arm` hacia `Recogida`, Plan y Execute, planificación aproximada de 0.079 s; `gripper` hacia `Close`, aproximadamente 0.062 s. Ambas ejecuciones correctas, documentadas en el video 02.
- Las rutinas completas se muestran en los videos 03 y 04 a tiempo real.

`resultados/verificacion_portabilidad.json` conserva la comprobación histórica de la estructura anterior. `resultados/validacion_estructura.json` registra la validación de la nueva organización: los cuatro paquetes compilaron, ambos lanzadores se analizaron correctamente y el URDF/SRDF y los controladores se cargaron desde la nueva ubicación.
