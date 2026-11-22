source "/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/video/mostrar.sh"
esperar_nav2 ~/proyecto_final_ws/logs/video_p5.log
sleep 3
nota "Práctica 5: Nav2. Planificador y controlador activos:"
mostrar "ros2 param get /planner_server GridBased.plugin"
mostrar "ros2 param get /controller_server FollowPath.plugin"
nota "Tres metas seguidas; camino a la meta 2 aparece una caja y Nav2 replanifica."
mostrar "ros2 run dif_bot probar_nav.py --ros-args -p use_sim_time:=true -p obstaculo:=true -p etiqueta:=video -p salida:=/tmp 2>&1 | grep -a --line-buffered -E 'Meta [0-9]|caja ' | cut -c40-"
touch /tmp/guion_listo
