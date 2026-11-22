#!/bin/bash
G="/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/proyecto_final_ws/src/dif_bot/scripts/graficar_p5.py"
D="/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/evidencias/p5"
M="/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/proyecto_final_ws/src/dif_bot/maps/bodega.yaml"
T=$(mktemp -d)
cp ~/proyecto_final_ws/resultados/p5_sin_obstaculo.* ~/proyecto_final_ws/resultados/p5_con_obstaculo.* ~/proyecto_final_ws/resultados/p5_meta_bloqueada.* $T/
python3 "$G" $T "$D/p5_trayectorias.png" "$M" 2>&1 | tail -1
