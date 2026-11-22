#!/bin/bash
# Repite las mediciones de P1 con el robot corregido (sin ventanas).
source /opt/ros/kilted/setup.bash
source ~/proyecto_final_ws/install/setup.bash
cd ~/proyecto_final_ws
PARAR="/mnt/c/Users/BRAYAN MATEO BRAVO L/AppData/Local/Temp/claude/50ac824fe08f93e3/fb118709-910e-49e3-94da-4587ba8cc395/scratchpad/parar.sh"
for modo in gz ros2_control; do
  bash "$PARAR" >/dev/null 2>&1
  if [ $modo = gz ]; then
    ros2 launch dif_bot sim.launch.py use_ros2_control:=false gui:=false rviz:=false > logs/p1_med_$modo.log 2>&1 &
    TOP=/odom
  else
    ros2 launch dif_bot sim.launch.py use_ros2_control:=true activar_controladores:=true gui:=false rviz:=false > logs/p1_med_$modo.log 2>&1 &
    TOP=/diff_drive_controller/odom
  fi
  for i in $(seq 1 12); do
    if timeout 15 ros2 topic echo $TOP --once >/dev/null 2>&1; then break; fi
    sleep 2
  done
  sleep 2
  for vw in "0.3 0.0" "0.0 0.8"; do
    set -- $vw
    timeout 60 ros2 run dif_bot medir_odom.py --ros-args -p use_sim_time:=true -p modo:=$modo -p v:=$1 -p w:=$2 2>&1 | grep -a '"modo"' | sed 's/.*\] //'
  done
done
bash "$PARAR" >/dev/null 2>&1
