source "/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/video/mostrar.sh"
esperar_topico /odom_filtered
sleep 5
nota "Práctica 3: SLAM Toolbox (online async). Recorrido automático por la bodega a 0.45 m/s."
mostrar "ros2 run dif_bot explorar.py --ros-args -p use_sim_time:=true -p v:=0.45 -p w_max:=1.2 -p etiqueta:=video -p salida:=/tmp 2>&1 | grep -a --line-buffered -E 'Punto|terminado' | cut -c40-"
sleep 4
nota "Guardar el mapa:"
mostrar "ros2 run nav2_map_server map_saver_cli -f /tmp/mapa_video --ros-args -p use_sim_time:=true 2>&1 | grep -a 'saved'"
mostrar "cat /tmp/mapa_video.yaml"
touch /tmp/guion_listo
