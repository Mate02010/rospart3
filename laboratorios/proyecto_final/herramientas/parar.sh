pkill -INT -f "ros2 launch" 2>/dev/null; sleep 3
pkill -f "gz sim" 2>/dev/null; pkill -f rviz2 2>/dev/null; pkill -f parameter_bridge 2>/dev/null; pkill -f robot_state_publisher 2>/dev/null; pkill -f "ruby.*gz" 2>/dev/null
pkill -f ekf_node 2>/dev/null; pkill -f slam_toolbox 2>/dev/null; pkill -f nav2 2>/dev/null; pkill -f "component_container" 2>/dev/null; pkill -f teleop 2>/dev/null
sleep 2; pgrep -fa "gz sim|rviz2|ros2 launch" | head -5 || true; echo parado
