#!/bin/bash
# Uso: arco.sh <topico_odom> <topico_cmd> <Twist|TwistStamped>
source /opt/ros/kilted/setup.bash
source ~/proyecto_final_ws/install/setup.bash
for i in $(seq 1 12); do
  if timeout 15 ros2 topic echo $1 --once >/dev/null 2>&1; then echo "listo ($i)"; break; fi
  sleep 2
done
sleep 2
if [ "$3" = "Twist" ]; then
  timeout 6 ros2 topic pub -r 20 $2 geometry_msgs/msg/Twist "{linear: {x: 0.3}, angular: {z: 0.3}}" >/dev/null 2>&1
  ros2 topic pub --once $2 geometry_msgs/msg/Twist "{}" >/dev/null 2>&1
else
  timeout 6 ros2 topic pub -r 20 $2 geometry_msgs/msg/TwistStamped "{twist: {linear: {x: 0.3}, angular: {z: 0.3}}}" >/dev/null 2>&1
  ros2 topic pub --once $2 geometry_msgs/msg/TwistStamped "{}" >/dev/null 2>&1
fi
sleep 2
