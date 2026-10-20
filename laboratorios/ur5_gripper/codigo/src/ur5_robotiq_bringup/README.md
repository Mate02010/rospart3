# ur5_robotiq_bringup

Descripción
- Paquete ROS 2 para lanzar en Gazebo una simulación del brazo UR5 equipado con un gripper paralelo simple. Este paquete contiene archivos de lanzamiento, configuración y recursos para visualizar y simular el robot; depende de `ur5_robotiq_description` para el URDF/XACRO y las mallas.

Requisitos
- ROS 2 (versión compatible con su stack).
- Gazebo (o el bridge correspondiente entre ROS y Gazebo).
- Paquete dependiente: `ur5_robotiq_description` (debe estar presente en el workspace de ROS).
- Paquetes ROS habituales: `robot_state_publisher`, `ros2_control`, `controller_manager`, `gazebo_ros`.

Estructura del repositorio (referencia)
El árbol del paquete es el siguiente:

ur5_robotiq_bringup/
├── config
│   └── controllers_sg.yaml
├── launch
│   ├── sim_gz_sgb.launch.py
│   └── view_rviz_ur_robotiq.launch.py
├── package.xml
├── README.md
├── resource
│   └── ur5_robotiq_bringup
├── rviz
│   ├── view_robot.rviz
│   └── view_robot_ur_robotiq.rviz
├── setup.cfg
├── setup.py
├── test
│   ├── test_copyright.py
│   ├── test_flake8.py
│   ├── test_mypy.py
│   ├── test_pep257.py
│   └── test_xmllint.py
├── ur5_robotiq_bringup
│   ├── __init__.py
│   └── py.typed
└── worlds
    └── empty.sdf

Nota: la estructura anterior refleja los nombres de archivos y carpetas reales en este paquete. Se deben ajustar las rutas si usase usan overrides locales.

Archivos y propósitos importantes
- `launch/sim_gz_sgb.launch.py` — Lanzador principal para iniciar la simulación en Gazebo con el mundo incluido (`worlds/empty.sdf`) y spawn del robot (según configuración del paquete `ur5_robotiq_description`).
- `launch/view_rviz_ur_robotiq.launch.py` — Lanzador para abrir RViz con configuraciones específicas para visualizar el URDF y los tópicos del robot.
- `config/controllers_sg.yaml` — Configuración de controladores para `ros2_control` (control del brazo y del gripper simple).
- `rviz/view_robot.rviz` y `rviz/view_robot_ur_robotiq.rviz` — Configuraciones de RViz usadas por el lanzador de visualización.
- `resource/ur5_robotiq_bringup` — Recursos adicionales empaquetados con el package (p.ej. iconos, descriptores).
- `worlds/empty.sdf` — Mundo SDF de prueba ligero usado para simulación.
- `package.xml`, `setup.py`, `setup.cfg` — Metadatos y configuración para instalación/packaging del paquete Python/ROS.
- `ur5_robotiq_bringup/__init__.py` y `py.typed` — Módulo Python vacío y marcado de tipado.
- `test/` — Suite de checks (flake8, mypy, pep257, xmllint, copyright) para calidad del paquete.

Uso rápido
1. Asegúrarse de que las dependencias están instaladas y que `ur5_robotiq_description` está presente en el mismo workspace.
2. Compila el workspace (desde la raíz del workspace ROS 2):

```bash
# desde la raíz del workspace que contiene este paquete
colcon build --packages-select ur5_robotiq_bringup
```

3. Para lanzar la simulación en Gazebo (método típico):

```bash
source install/setup.bash
ros2 launch ur5_robotiq_bringup sim_gz_sgb.launch.py
```

4. Para abrir RViz con la configuración incluida:

```bash
source install/setup.bash
ros2 launch ur5_robotiq_bringup view_rviz_ur_robotiq.launch.py
```
## 5. Enviar trayectoria al brazo:
```
ros2 topic pub /scaled_joint_trajectory_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "
joint_names: ['shoulder_pan_joint','shoulder_lift_joint','elbow_joint','wrist_1_joint','wrist_2_joint','wrist_3_joint']
points:
- positions: [0.0, -1.57, 1.57, -1.57, -1.57, 0.0]
  time_from_start: {sec: 2, nanosec: 0}
"
```

## Mover Griper.
### Posición intermedia
```
ros2 topic pub /gripper_controller/commands \
  std_msgs/msg/Float64MultiArray "{data: [0.02, 0.02]}"
```
### Posición cerrada.
```
ros2 topic pub /gripper_controller/commands \
  std_msgs/msg/Float64MultiArray "{data: [0.004, 0.004]}"
```

### Posición abierta.
```
ros2 topic pub /gripper_controller/commands \
  std_msgs/msg/Float64MultiArray "{data: [0.04, 0.04]}"
```

## 6. Notas y recomendaciones
- Este paquete asume que la descripción del robot (URDF/XACRO y meshes) está disponible en `ur5_robotiq_description` u otro paquete instalado en el workspace.
- Los nombres de archivos de `launch/` y `config/` son los reales en este repo; si añades nuevos lanzadores o parámetros, actualiza este README.

---
Pequeño checklist de verificación local (opcional):

```bash
# compilar
colcon build
# comprobar tests (rápido):
pytest -q
```