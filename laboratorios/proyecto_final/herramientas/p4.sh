#!/bin/bash
# Uso: p4.sh <etiqueta> [parametros extra de evaluar_amcl...]   (localizacion.launch.py ya corriendo)
source /opt/ros/kilted/setup.bash
source ~/proyecto_final_ws/install/setup.bash
cd ~/proyecto_final_ws
E=$1; shift
ok=0
for i in $(seq 1 20); do
  if timeout 15 ros2 topic echo /odom_filtered --once >/dev/null 2>&1; then ok=1; break; fi
  sleep 3
done
[ $ok = 1 ] || { echo "NO llega /odom_filtered"; tail -20 logs/p4_$E.log; exit 1; }
sleep 5
bash "/mnt/c/Users/BRAYAN MATEO BRAVO L/AppData/Local/Temp/claude/50ac824fe08f93e3/fb118709-910e-49e3-94da-4587ba8cc395/scratchpad/evid.sh" p4/$E /amcl_pose /particle_cloud /map /scan /tf > /dev/null 2>&1
date +%T
timeout 900 ros2 run dif_bot evaluar_amcl.py --ros-args -p use_sim_time:=true -p etiqueta:=$E "$@" 2>&1 | grep -av "^\s*$" | tail -6 | cut -c1-700
date +%T
