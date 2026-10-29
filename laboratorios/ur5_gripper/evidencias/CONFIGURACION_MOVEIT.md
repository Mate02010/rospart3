# Configuración de MoveIt

El paquete `ur5_gripper_moveit` se generó desde la interfaz gráfica de MoveIt Setup Assistant 2.14.3, cargando `ur_with_gripper_moveit.urdf.xacro`. El video 01 documenta la generación y el video 02 las pruebas de ambos grupos en RViz.

| Elemento | Configuración |
|---|---|
| Autocolisiones | Matriz generada con 10 000 muestras |
| Brazo | Grupo `arm`, cadena `base_link` a `tool0`, KDL |
| Pinza | Grupo `gripper`, joints `gripper_finger_joint` y `right_finger_joint` |
| Efector | `eef`, grupo de pinza, montaje `tool0`, padre `arm` |
| Referencia | El URDF ya contiene `world` fijo |
| Acciones | `FollowJointTrajectory` en brazo y pinza |
| Pipeline | OMPL con `RRTConnect` |

Después de generar el paquete se alineó `arm_controller` con el controlador real `scaled_joint_trajectory_controller`, se añadieron estados nombrados, límites de aceleración y el launch de integración. `herramientas/ajustar_moveit.py` conserva estos ajustes; no es necesario ejecutarlo para utilizar la configuración entregada.

## RViz

Con Gazebo activo y `bash ejecutar.sh planificador`:

1. En MotionPlanning, seleccionar grupo `arm`, inicio `<current>` y objetivo `Recogida`.
2. Pulsar **Plan**, revisar la trayectoria y pulsar **Execute**.
3. Seleccionar grupo `gripper`, objetivo `Close`, **Plan** y **Execute**.

Las dos pruebas terminaron correctamente. Para abrir la configuración existente:

```bash
source /opt/ros/kilted/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=74
ros2 launch ur5_gripper_moveit setup_assistant.launch.py
```

La aplicación usa `/plan_kinematic_path` (`moveit_msgs/srv/GetMotionPlan`) y `/execute_trajectory` (`moveit_msgs/action/ExecuteTrajectory`). Comprueba las respuestas de MoveIt y el error final medido en `/joint_states`.

`demo.launch.py` permite iniciar Gazebo y el planificador juntos. Es una alternativa al arranque separado de las terminales 1 y 3, y no debe ejecutarse junto a una simulación ya activa.
