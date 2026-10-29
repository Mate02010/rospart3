# Organización de la práctica

La práctica está en `rospart3/laboratorios/ur5_gripper`. Los cuatro paquetes separan la aplicación, el modelo del robot, la simulación/controladores y la configuración de MoveIt.

| Carpeta | Contenido |
| --- | --- |
| `lab_manipulador/` | Nodos Pick and Place y señales digitales |
| `ur5_robotiq_description/` | Modelo del brazo y la pinza |
| `ur5_robotiq_bringup/` | Simulación y controladores |
| `ur5_gripper_moveit/` | Configuración generada con Setup Assistant |
| `evidencias/videos/` | Cuatro grabaciones de las actividades |
| `evidencias/capturas/` | Capturas de las interfaces y de Gazebo |
| `evidencias/resultados/` | Registros y comprobaciones de las ejecuciones |
| `herramientas/` | Ajustes y grabación |

El informe académico, su PDF y sus fuentes LaTeX/Overleaf se conservan fuera de la publicación de GitHub, por petición expresa del autor. No deben incorporarse a futuros commits.

Para compilar, ejecutar `bash ejecutar.sh build` desde la carpeta de la práctica. Los archivos nuevos de ejecución se guardan en `ejecuciones_locales/`, excluida de Git, para proteger los videos y registros históricos. Se mantienen las dos prácticas del repositorio y sus paquetes.
