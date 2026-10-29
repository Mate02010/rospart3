# Herramientas auxiliares

- `ajustar_moveit.py`: conserva los ajustes posteriores a Setup Assistant (controladores, estados nombrados, límites y OMPL). No es necesario ejecutarlo para usar la configuración entregada; revisar cambios antes de regenerarla.
- `grabar_pruebas.py`: permite repetir la grabación de las rutinas con Gazebo visible, las señales digitales y MoveIt ya activos. Requiere activar primero `/opt/ros/kilted/setup.bash`, `install/setup.bash` y `ROS_DOMAIN_ID=74`. Utiliza FFmpeg y xdotool, ya presentes en el entorno de prueba.

Estas herramientas generan sus archivos en `ejecuciones_locales/` para no sustituir las grabaciones y mediciones históricas de `evidencias/`.
