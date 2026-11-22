#!/bin/bash
# Uso: p5.sh <etiqueta> [parametros de probar_nav...]   (navegacion.launch.py ya corriendo)
source /opt/ros/kilted/setup.bash
source ~/proyecto_final_ws/install/setup.bash
cd ~/proyecto_final_ws
E=$1; shift
ok=0
for i in $(seq 1 30); do
  if timeout 15 ros2 topic echo /odom_filtered --once >/dev/null 2>&1; then ok=1; break; fi
  sleep 3
done
[ $ok = 1 ] || { echo "NO llega /odom_filtered"; exit 1; }
# Nav2 debe terminar de activarse; si no, se aborta para relanzar.
ok=0
for i in $(seq 1 50); do
  grep -aq "lifecycle_manager_navigation.*Managed nodes are active" logs/p5_$E.log && { ok=1; break; }
  sleep 3
done
[ $ok = 1 ] || { echo "NAV2 NO ACTIVO tras 150 s"; exit 1; }
# El controlador debe estar activo y escuchando /cmd_vel antes de mandar metas.
for i in $(seq 1 20); do
  n=$(timeout 15 ros2 topic info /cmd_vel 2>/dev/null | grep -a "Subscription count" | awk '{print $3}')
  [ "$n" = "1" ] && break
  sleep 3
done
[ "$n" = "1" ] || { echo "CONTROLADOR NO ACTIVO: nadie escucha /cmd_vel"; grep -a spawner logs/navegacion_actual.log 2>/dev/null | tail -3; exit 1; }
bash "/mnt/c/Users/BRAYAN MATEO BRAVO L/AppData/Local/Temp/claude/50ac824fe08f93e3/fb118709-910e-49e3-94da-4587ba8cc395/scratchpad/evid.sh" p5/$E /cmd_vel /cmd_vel_nav /cmd_vel_smoothed /plan /amcl_pose /tf > /dev/null 2>&1
{
  echo "### planner_server planner_plugins / GridBased.plugin"; timeout 30 ros2 param get /planner_server planner_plugins; timeout 30 ros2 param get /planner_server GridBased.plugin
  echo "### controller_server controller_plugins / FollowPath.plugin"; timeout 30 ros2 param get /controller_server controller_plugins; timeout 30 ros2 param get /controller_server FollowPath.plugin
  echo "### bt_navigator default_nav_to_pose_bt_xml"; timeout 30 ros2 param get /bt_navigator default_nav_to_pose_bt_xml
  echo "### behavior_server behavior_plugins"; timeout 30 ros2 param get /behavior_server behavior_plugins
} > ~/proyecto_final_ws/evidencias/p5/$E/plugins_nav2.txt 2>&1
cat ~/proyecto_final_ws/evidencias/p5/$E/plugins_nav2.txt
date +%T
timeout 1200 ros2 run dif_bot probar_nav.py --ros-args -p use_sim_time:=true "$@" 2>&1 | grep -av "^\s*$" | grep -av "Feedback\|feedback" | tail -12 | cut -c1-400
date +%T
