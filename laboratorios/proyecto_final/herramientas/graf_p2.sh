#!/bin/bash
D="/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/evidencias/p2"
S="/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/proyecto_final_ws/src/dif_bot/scripts/graficar_p2.py"
mkdir -p "$D/resultados"
cp ~/proyecto_final_ws/resultados/p2_* "$D/resultados/"
cp -r ~/proyecto_final_ws/evidencias/p2/con_imu ~/proyecto_final_ws/evidencias/p2/sin_imu "$D/"
python3 "$S" ~/proyecto_final_ws/resultados "$D/p2_comparacion_ekf.png" 2>&1 | grep -v Warning
