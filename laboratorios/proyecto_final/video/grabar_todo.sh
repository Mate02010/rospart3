#!/bin/bash
# Graba un clip por práctica (en orden) en la pantalla oculta :99.
V="/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/video"
C() { bash "$V/clip.sh" "$@"; }
for p in "$@"; do
  case $p in
    p1) C p1 guion_p1.sh 150 ros2 launch dif_bot sim.launch.py use_ros2_control:=true camara:=true gui:=false ;;
    p2) C p2 guion_p2.sh 240 ros2 launch dif_bot ekf.launch.py gui:=false ;;
    p3) C p3 guion_p3.sh 600 ros2 launch dif_bot slam.launch.py gui:=false ;;
    p4) C p4 guion_p4.sh 240 ros2 launch dif_bot localizacion.launch.py gui:=false ;;
    p5) C p5 guion_p5.sh 600 ros2 launch dif_bot navegacion.launch.py gui:=false ;;
    final) C final guion_final.sh 800 ros2 launch dif_bot mision.launch.py gui:=false ;;
  esac
done
echo "FIN $(date +%T)"
