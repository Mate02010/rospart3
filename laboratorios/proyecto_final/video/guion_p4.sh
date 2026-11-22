source "/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/video/mostrar.sh"
esperar_activo ~/proyecto_final_ws/logs/video_p4.log
esperar_topico /odom_filtered
sleep 3
nota "Práctica 4: AMCL sobre el mapa de la P3. Localización global: partículas repartidas en todo el mapa."
mostrar "ros2 service call /reinitialize_global_localization std_srvs/srv/Empty '{}' | tail -1"
sleep 4
nota "El robot gira en el sitio y avanza; las partículas que no encajan con el láser desaparecen."
mostrar "timeout 9 ros2 topic pub -r 20 /diff_drive_controller/cmd_vel geometry_msgs/msg/TwistStamped '{twist: {angular: {z: 0.8}}}' > /dev/null"
mostrar "timeout 6 ros2 topic pub -r 20 /diff_drive_controller/cmd_vel geometry_msgs/msg/TwistStamped '{twist: {linear: {x: 0.25}}}' > /dev/null"
sleep 2
mostrar "python3 '/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/video/pose_amcl.py'"
touch /tmp/guion_listo
