# Laboratorio: UR5 con gripper, ROS 2 y MoveIt 2

**Autor:** Brayan Mateo Bravo Losada. Robótica, Ingeniería Electrónica, Escuela Colombiana de Ingeniería Julio Garavito.

Implementación basada en [DanielPalominoS/ur5_gripper_packages](https://github.com/DanielPalominoS/ur5_gripper_packages), commit `87a547dfde78df811fd5964c7f6ff4882630c9f8`. La referencia original se conserva sin modificar en la carpeta de trabajo. La entrega incluye sus dos paquetes adaptados, un paquete de aplicación y la configuración generada mediante la interfaz gráfica de MoveIt Setup Assistant.

## Entorno

Ubuntu 24.04 en WSL2, ROS 2 Kilted, Gazebo Sim Ionic 9.5.0, MoveIt 2 y `gz_ros2_control`. Se reutilizó el entorno instalado; no hay un instalador que reinstale ROS, Gazebo o MoveIt. FFmpeg y xdotool son herramientas auxiliares para producir evidencia, no requisitos del nodo Pick and Place.

## Archivos

Código, configuración, reporte y videos del laboratorio: [abrir carpeta en GitHub](https://github.com/Mate02010/rospart3/tree/main/laboratorios/ur5_gripper). El PDF de `output/pdf` enlaza los recursos públicos. La copia local conserva los mismos archivos; extraer el ZIP completo para abrir las evidencias directamente desde sus carpetas.

- [Reporte PDF](output/pdf/Reporte_Laboratorio_UR5_Gripper.pdf).
- [Índice de los cuatro videos](evidencias/videos/README.md).
- [Configuración MoveIt generada con Setup Assistant](codigo/src/ur5_gripper_moveit).

- `codigo/src/ur5_robotiq_description`: modelo UR5 y pinza paralela de dos dedos prismáticos.
- `codigo/src/ur5_robotiq_bringup`: Gazebo y controladores.
- `codigo/src/lab_manipulador`: nodos `pick_place` y `digital_io`.
- `codigo/src/ur5_gripper_moveit`: SRDF, cinemática, colisiones, OMPL, controladores y RViz.
- `evidencias/resultado_topics.json` y `resultado_moveit.json`: objetivos, eventos y mediciones de `/joint_states`.
- `evidencias/videos`: grabaciones de configuración y funcionamiento.
- `output/pdf`: reporte de resultados.

## Ejecutar

Para obtener esta versión desde GitHub, sin instalar programas:

```bash
git clone https://github.com/Mate02010/rospart3.git
cd rospart3/laboratorios/ur5_gripper
bash ejecutar.sh build
```

En Ubuntu, situarse en la carpeta que contiene este README y `ejecutar.sh`. Puede ser cualquier ubicación donde hayas extraído el ZIP; esta es la ruta de la copia de entrega en el equipo de desarrollo:

```bash
cd "/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 2/Practica_2_UR5_Gripper/entrega"
bash ejecutar.sh build
```

Mantener abiertas terminales independientes para estos procesos:

```bash
# Terminal 1: simulacion completa. Usar false para funcionar sin GUI.
bash ejecutar.sh sim true

# Terminal 2: entrada digital simulada; true activa el pulsador automatico de demostracion.
bash ejecutar.sh io true

# Terminal 3: MoveIt + RViz sobre los mismos estados y controladores de Gazebo.
bash ejecutar.sh planificador
```

Ejecutar **una sola rutina a la vez** en una cuarta terminal:

```bash
# Actividades de control por topicos y rutina Pick and Place.
bash ejecutar.sh topics

# Actividad de planificacion y ejecucion desde un nodo MoveIt.
bash ejecutar.sh moveit
```

El script activa `/opt/ros/kilted/setup.bash`, el overlay local y `ROS_DOMAIN_ID=74`. No iniciar otra simulación en ese dominio mientras esta esté en uso. Terminar cada proceso con Ctrl+C en su terminal. Las carpetas `build`, `install` y `log` se regeneran con colcon y no forman parte del código entregable.

## Comandos ROS verificables

Para comandos manuales, preparar **cada terminal**:

```bash
source /opt/ros/kilted/setup.bash
source codigo/install/setup.bash
export ROS_DOMAIN_ID=74
ros2 control list_controllers
ros2 topic list -t
ros2 action list -t
```

Ejemplo de posición del brazo:

```bash
ros2 topic pub --once /scaled_joint_trajectory_controller/joint_trajectory \
trajectory_msgs/msg/JointTrajectory \
"{joint_names: [shoulder_pan_joint, shoulder_lift_joint, elbow_joint, wrist_1_joint, wrist_2_joint, wrist_3_joint], points: [{positions: [0.0, -1.57, 1.57, -1.57, -1.57, 0.0], time_from_start: {sec: 3}}]}"
```

Apertura y cierre de los dos dedos, respectivamente:

```bash
ros2 topic pub --once /gripper_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory \
"{joint_names: [gripper_finger_joint, right_finger_joint], points: [{positions: [0.04, 0.04], time_from_start: {sec: 1}}]}"

ros2 topic pub --once /gripper_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory \
"{joint_names: [gripper_finger_joint, right_finger_joint], points: [{positions: [0.004, 0.004], time_from_start: {sec: 1}}]}"
```

Se sustituyó el `JointGroupPositionController` de la pinza original por `JointTrajectoryController`; por eso se utiliza `JointTrajectory`, y no el tópico `/gripper_controller/commands` del README del profesor. Ambos controladores exponen acciones `FollowJointTrajectory` para MoveIt.

## Secuencia de la aplicación

| Punto | Objetivo articular, rad | Operación |
|---|---|---|
| Preparación | 0, -1.57, 1.57, -1.57, -1.57, 0 | Mensaje de inicio y apertura |
| Recogida | 0.35, -1.45, 1.80, -1.92, -1.57, 0 | Cierre y cambio del estado lógico de pieza |
| Intermedio | 0, -1.20, 1.40, -1.77, -1.57, 0 | Activación de salida digital |
| Entrega | -0.40, -1.45, 1.80, -1.92, -1.57, 0 | Apertura y espera de entrada digital |

Después de observar una entrada BAJA seguida de una nueva entrada ALTA, el brazo regresa a Preparación. Son cuatro puntos distintos, más el retorno. Cada transición se verifica mediante los estados articulares medidos; publicar el comando por sí solo no se considera éxito.

## Entrada y salida digitales

- `/lab/digital_input`, `/lab/digital_output` y `/lab/waiting_input`: `std_msgs/msg/Bool`.
- `/lab/status`: `std_msgs/msg/String`, eventos de la rutina en JSON.
- `/lab/set_digital_input`: servicio `std_srvs/srv/SetBool` del nodo de simulación.

Para demostrar el bloqueo manual, usar `bash ejecutar.sh io false`. Al llegar a Entrega, ejecutar en otra terminal preparada:

```bash
ros2 service call /lab/set_digital_input std_srvs/srv/SetBool "{data: false}"
ros2 service call /lab/set_digital_input std_srvs/srv/SetBool "{data: true}"
```

El modo automático genera ese mismo cambio de mensajes después de 1.5 segundos para que la grabación sea repetible. La señal es simulada; no representa una entrada eléctrica de hardware.

## Configuración MoveIt y pruebas en RViz

Setup Assistant generó el paquete desde `ur_with_gripper_moveit.urdf.xacro`: matriz con 10 000 muestras, grupo `arm` como cadena `base_link` a `tool0` con KDL, grupo `gripper` con los dos dedos, efector `eef` montado en `tool0` y controladores `FollowJointTrajectory` para ambos grupos. El URDF ya fija el robot a `world`; no se agregó otro virtual joint redundante.

Tras la generación se añadieron estados nombrados, límites de aceleración y el launch `gazebo_moveit.launch.py`, y se ajustó `arm_controller` al nombre real `scaled_joint_trajectory_controller`. `completar_configuracion.py` documenta esos ajustes. No regenerar el paquete sobre estos cambios sin revisarlos.

En el panel MotionPlanning de RViz:

1. Seleccionar `arm`, inicio `<current>` y objetivo `Recogida`.
2. Pulsar **Plan**, revisar la trayectoria y pulsar **Execute**.
3. Seleccionar `gripper`, objetivo `Close`, **Plan** y **Execute**.

Las pruebas de ambos grupos están grabadas. Para revisar la configuración existente con el asistente:

```bash
ros2 launch ur5_gripper_moveit setup_assistant.launch.py
```

El nodo utiliza el servicio `/plan_kinematic_path` (`moveit_msgs/srv/GetMotionPlan`) y la acción `/execute_trajectory` (`moveit_msgs/action/ExecuteTrajectory`), con OMPL/RRTConnect. Se comprueba tanto el resultado de MoveIt como el estado final observado.

## Alcance y dificultades resueltas

Los dedos sí son articulaciones simuladas en Gazebo; la pieza recogida se representa mediante un estado lógico. No se afirma agarre físico por contacto, ni emulación del protocolo propietario de Robotiq, ni ejecución sobre un robot real.

Se corrigieron la incompatibilidad entre el controlador original de pinza y la guía `GripperCommand`, el argumento `-z` de inserción, la ruta explícita del mundo, la geometría de suelo de espesor cero, los estados iniciales, las rutas con espacios y el nombre de configuración del planificador. El aviso de OctoMap sin sensor 3D y el servicio de reconocimiento de objetos no disponible corresponden a funciones no utilizadas en este escenario de planificación estática.

Se adaptó `demo.launch.py` para abrir Gazebo y `gazebo_moveit.launch.py` juntos, usando los mismos controladores. Es una alternativa al arranque de las terminales 1 y 3; no debe ejecutarse además de una simulación que ya esté activa.

## Fuentes

- [Repositorio base del profesor](https://github.com/DanielPalominoS/ur5_gripper_packages).
- [Guía del profesor para Setup Assistant](https://github.com/DanielPalominoS/ur5_gripper_packages/blob/main/MoveitSetupAssConfig.md).
- [ROS 2 Kilted: instalación en Ubuntu](https://docs.ros.org/en/kilted/Installation/Ubuntu-Install-Debs.html).
- [Combinaciones de ROS y Gazebo](https://gazebosim.org/docs/fortress/ros_installation/).
- [Distribuciones ROS 2](https://docs.ros.org/en/kilted/Releases.html).

Las versiones y resultados descritos pertenecen a la instalación de prueba. La existencia del reporte o del repositorio no implica entrega en el campus virtual.

## Resultado de la validación

Los cuatro paquetes compilaron. Las rutinas por tópicos y por MoveIt completaron ocho movimientos cada una, recorriendo cuatro objetivos distintos del brazo y verificando la transición de entrada digital. Se guardaron los resultados medidos en JSON y cuatro videos reales; los dos videos de interfaz indican su aceleración. El PDF contiene las mediciones y los hallazgos. `MANIFIESTO_SHA256.txt` permite comprobar la integridad de los archivos recibidos.

## Videos de evidencia

- [01_setup_assistant_resumen.mp4](evidencias/videos/01_setup_assistant_resumen.mp4) (117.7 s).
- [02_rviz_grupos_resumen.mp4](evidencias/videos/02_rviz_grupos_resumen.mp4) (112.6 s).
- [03_topics_gazebo.mp4](evidencias/videos/03_topics_gazebo.mp4) (99.0 s).
- [04_moveit_gazebo.mp4](evidencias/videos/04_moveit_gazebo.mp4) (81.6 s).

Los videos de Setup Assistant y RViz indican su aceleracion. Las rutinas mantienen el tiempo real; su encuadre se amplió a partir de las grabaciones originales de Gazebo.

### Comprobación desde el ZIP

Se extrajo el ZIP en otra carpeta y se verificaron los SHA256 del manifiesto. Allí se compilaron los cuatro paquetes con el entorno ROS base, sin cargar el workspace anterior. Se comprobaron ambos lanzadores, la carga del URDF/SRDF y la configuración de controladores desde esa copia. También se verificó el filtro del grabador con una ruta que contiene espacios. El registro está en `evidencias/verificacion_portabilidad.json`.

El grabador auxiliar utiliza su propia carpeta de evidencias; `ejecutar.sh` no requiere el alias temporal `/tmp/ur5_lab` usado al producir las pruebas iniciales.
