source "/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/video/mostrar.sh"
nota "Práctica 1: control con ros2_control (use_ros2_control:=true). Se activan los controladores a mano."
mostrar ros2 control load_controller --set-state active joint_state_broadcaster
mostrar ros2 control load_controller --set-state active diff_drive_controller
mostrar ros2 control list_controllers
nota "La odometría la publica el diff_drive_controller:"
mostrar "ros2 topic info /diff_drive_controller/odom -v | grep -E 'Node name|Publisher count'"
nota "Comando en arco (TwistStamped) durante 8 s:"
mostrar "timeout 8 ros2 topic pub -r 20 /diff_drive_controller/cmd_vel geometry_msgs/msg/TwistStamped '{twist: {linear: {x: 0.3}, angular: {z: 0.4}}}' > /dev/null"
mostrar "ros2 topic echo /diff_drive_controller/odom --once --field pose.pose.position 2>/dev/null | grep -av -E 'lost|total count'"
touch /tmp/guion_listo
