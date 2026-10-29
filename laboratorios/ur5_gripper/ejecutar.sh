#!/usr/bin/env bash
set -e -o pipefail
LAB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export ROS_DOMAIN_ID=74
source /opt/ros/kilted/setup.bash
mkdir -p "$LAB_ROOT/ejecuciones_locales/logs"
cd "$LAB_ROOT"
case "${1:-}" in
  build) colcon build --base-paths lab_manipulador ur5_robotiq_description ur5_robotiq_bringup ur5_gripper_moveit --symlink-install --event-handlers console_direct+ --cmake-args -DBUILD_TESTING=OFF ;;
  sim) source install/setup.bash; ros2 launch ur5_robotiq_bringup sim_gz_sgb.launch.py launch_rviz:=false gazebo_gui:="${2:-true}" 2>&1 | tee "$LAB_ROOT/ejecuciones_locales/logs/gazebo.log" ;;
  setup) source install/setup.bash; ros2 launch moveit_setup_assistant setup_assistant.launch.py 2>&1 | tee "$LAB_ROOT/ejecuciones_locales/logs/setup_assistant.log" ;;
  io) source install/setup.bash; ros2 run lab_manipulador digital_io --ros-args -p auto_confirm:="${2:-false}" 2>&1 | tee "$LAB_ROOT/ejecuciones_locales/logs/digital_io.log" ;;
  planificador) source install/setup.bash; ros2 launch ur5_gripper_moveit gazebo_moveit.launch.py 2>&1 | tee "$LAB_ROOT/ejecuciones_locales/logs/moveit.log" ;;
  topics|moveit) source install/setup.bash; ros2 run lab_manipulador pick_place --ros-args -p mode:="$1" -p use_sim_time:=true -p output_dir:="$LAB_ROOT/ejecuciones_locales" 2>&1 | tee "$LAB_ROOT/ejecuciones_locales/logs/rutina_$1.log" ;;
  *) echo 'Uso: ejecutar.sh build|sim [true/false]|setup|io [true/false]|planificador|topics|moveit'; exit 2 ;;
esac
