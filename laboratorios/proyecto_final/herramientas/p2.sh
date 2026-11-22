#!/bin/bash
# Uso: p2.sh <etiqueta>  (la simulación con ekf.launch.py ya debe estar corriendo)
source /opt/ros/kilted/setup.bash
source ~/proyecto_final_ws/install/setup.bash
cd ~/proyecto_final_ws
ok=0
for i in $(seq 1 12); do
  if timeout 15 ros2 topic echo /odom_filtered --once >/dev/null 2>&1; then ok=1; echo "odom_filtered listo ($i)"; break; fi
  sleep 2
done
[ $ok = 1 ] || { echo "NO llega /odom_filtered"; tail -30 ~/proyecto_final_ws/logs/p2_$1.log; exit 1; }
ros2 control list_controllers 2>&1 | head -5
bash "/mnt/c/Users/BRAYAN MATEO BRAVO L/AppData/Local/Temp/claude/50ac824fe08f93e3/fb118709-910e-49e3-94da-4587ba8cc395/scratchpad/evid.sh" p2/$1 /odom_filtered /diff_drive_controller/odom /imu /tf > /dev/null 2>&1
grep -A3 "odom_filtered" ~/proyecto_final_ws/evidencias/p2/$1/info_nodos_topicos.txt | head -8
grep -o '"odom" -> "base_footprint"\[label="[^"]*' ~/proyecto_final_ws/evidencias/p2/$1/arbol_tf.gv | head -2
timeout 120 ros2 run dif_bot comparar_ekf.py --ros-args -p use_sim_time:=true -p etiqueta:=$1 2>&1 | tail -3
