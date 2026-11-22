#!/bin/bash
# Uso: p3.sh <etiqueta> <v> <w_max> <nombre_mapa>  (slam.launch.py ya corriendo)
source /opt/ros/kilted/setup.bash
source ~/proyecto_final_ws/install/setup.bash
cd ~/proyecto_final_ws
WIN_PKG="/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/proyecto_final_ws/src/dif_bot"
ok=0
for i in $(seq 1 20); do
  if timeout 15 ros2 topic echo /map --once --qos-durability transient_local --field info.resolution >/dev/null 2>&1; then ok=1; echo "mapa publicado ($i)"; break; fi
  sleep 3
done
[ $ok = 1 ] || { echo "NO llega /map"; grep -ai "error\|slam" logs/p3_$1.log | tail -20; exit 1; }
bash "/mnt/c/Users/BRAYAN MATEO BRAVO L/AppData/Local/Temp/claude/50ac824fe08f93e3/fb118709-910e-49e3-94da-4587ba8cc395/scratchpad/evid.sh" p3/$1 /map /scan /odom_filtered /tf > /dev/null 2>&1
date +%T
timeout 1500 ros2 run dif_bot explorar.py --ros-args -p use_sim_time:=true -p v:=$2 -p w_max:=$3 -p etiqueta:=$1 2>&1 | grep -av "^\s*$" | tail -4
date +%T
sleep 6
mkdir -p "$WIN_PKG/maps"
ros2 run nav2_map_server map_saver_cli -f "$WIN_PKG/maps/$4" --ros-args -p use_sim_time:=true 2>&1 | tail -3
cat "$WIN_PKG/maps/$4.yaml"
