#!/bin/bash
# Con mision.launch.py ya corriendo (log en logs/final_mision.log): espera Nav2, toma evidencias y llama al servicio.
source /opt/ros/kilted/setup.bash
source ~/proyecto_final_ws/install/setup.bash
cd ~/proyecto_final_ws
L=logs/final_mision.log
ok=0
for i in $(seq 1 60); do grep -aq "lifecycle_manager_navigation.*Managed nodes are active" $L && { ok=1; break; }; sleep 3; done
[ $ok = 1 ] || { echo "NAV2 NO ACTIVO"; exit 1; }
for i in $(seq 1 20); do
  n=$(timeout 15 ros2 topic info /cmd_vel 2>/dev/null | grep -a "Subscription count" | awk '{print $3}')
  [ "$n" = "1" ] && break; sleep 3
done
[ "$n" = "1" ] || { echo "CONTROLADOR NO ACTIVO"; exit 1; }
for i in $(seq 1 30); do timeout 10 ros2 service list 2>/dev/null | grep -q "^/iniciar_mision$" && break; sleep 2; done
D=~/proyecto_final_ws/evidencias/final; mkdir -p $D
bash "/mnt/c/Users/BRAYAN MATEO BRAVO L/AppData/Local/Temp/claude/50ac824fe08f93e3/fb118709-910e-49e3-94da-4587ba8cc395/scratchpad/evid.sh" final /estado_mision /waypoints_mision /cmd_vel /amcl_pose > /dev/null 2>&1
{ echo "### ros2 service list | grep mision"; timeout 15 ros2 service list -t | grep mision; echo; echo "### ros2 interface show std_srvs/srv/Trigger"; ros2 interface show std_srvs/srv/Trigger; } > $D/servicios.txt 2>&1
sleep 5
date +%T
timeout 1500 ros2 topic echo /estado_mision --field data > $D/estado_mision.txt 2>&1 &
sleep 2
echo "### ros2 service call /iniciar_mision std_srvs/srv/Trigger" > $D/llamada_servicio.txt
timeout 30 ros2 service call /iniciar_mision std_srvs/srv/Trigger >> $D/llamada_servicio.txt 2>&1
cat $D/llamada_servicio.txt | tail -3
