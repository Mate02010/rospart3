source "/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/video/mostrar.sh"
esperar_nav2 ~/proyecto_final_ws/logs/video_final.log
for i in $(seq 1 30); do timeout 10 ros2 service list 2>/dev/null | grep -q "^/iniciar_mision$" && break; sleep 2; done
sleep 3
nota "Misión final: mision.py (nav2_simple_commander). Waypoints en config/waypoints.yaml:"
mostrar "grep -E '^ *- \{' ~/proyecto_final_ws/install/dif_bot/share/dif_bot/config/waypoints.yaml | cut -c7-80"
nota "La misión se inicia con un servicio:"
mostrar "ros2 service call /iniciar_mision std_srvs/srv/Trigger | tail -1"
mostrar "ros2 topic echo /estado_mision --field data 2>/dev/null | grep -av --line-buffered -E 'faltan|^---' | sed -u '/COMPLETADA/q'"
touch /tmp/guion_listo
