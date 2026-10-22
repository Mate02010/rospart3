# Comandos ROS del laboratorio

Preparar cada terminal dentro de la carpeta de la práctica, después de compilar:

```bash
source /opt/ros/kilted/setup.bash
source install/setup.bash
export ROS_DOMAIN_ID=74
ros2 control list_controllers
ros2 topic list -t
ros2 action list -t
```

## Brazo

`/scaled_joint_trajectory_controller/joint_trajectory` utiliza `trajectory_msgs/msg/JointTrajectory`. Las posiciones son radianes y el orden de las articulaciones debe coincidir con `joint_names`.

```bash
ros2 topic pub --once /scaled_joint_trajectory_controller/joint_trajectory \
trajectory_msgs/msg/JointTrajectory \
"{joint_names: [shoulder_pan_joint, shoulder_lift_joint, elbow_joint, wrist_1_joint, wrist_2_joint, wrist_3_joint], points: [{positions: [0.0, -1.57, 1.57, -1.57, -1.57, 0.0], time_from_start: {sec: 3}}]}"
```

## Pinza

El controlador adaptado recibe `JointTrajectory` en `/gripper_controller/joint_trajectory`, con posiciones prismáticas en metros. Los dos comandos siguientes abren y cierran, respectivamente:

```bash
ros2 topic pub --once /gripper_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory \
"{joint_names: [gripper_finger_joint, right_finger_joint], points: [{positions: [0.04, 0.04], time_from_start: {sec: 1}}]}"

ros2 topic pub --once /gripper_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory \
"{joint_names: [gripper_finger_joint, right_finger_joint], points: [{positions: [0.004, 0.004], time_from_start: {sec: 1}}]}"
```

Estos comandos sustituyen el tópico `commands` del controlador original. No enviar órdenes manuales mientras esté ejecutándose la rutina.

## Entrada y salida digitales

Los tópicos `/lab/digital_input`, `/lab/digital_output` y `/lab/waiting_input` son `std_msgs/msg/Bool`; `/lab/status` es `std_msgs/msg/String` con eventos JSON.

Para demostrar la espera manual, iniciar `bash ejecutar.sh io false`. Al llegar a Entrega, enviar una entrada BAJA y luego una nueva ALTA:

```bash
ros2 service call /lab/set_digital_input std_srvs/srv/SetBool "{data: false}"
ros2 service call /lab/set_digital_input std_srvs/srv/SetBool "{data: true}"
```

La secuencia no continúa por un ALTO anterior a la espera. El modo `io true`, usado en los videos, genera la misma transición automáticamente después de 1.5 s. Ninguna de estas señales representa una conexión eléctrica de hardware.
