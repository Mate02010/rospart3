#!/bin/bash
P="/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final"
f=$(ls ~/proyecto_final_ws/resultados/mision_recorrido_bodega_*[0-9].json | head -1)
python3 "$P/proyecto_final_ws/src/dif_bot/scripts/graficar_mision.py" "$f" "$P/evidencias/final/mision_trayectoria.png" "$P/proyecto_final_ws/src/dif_bot/maps/bodega.yaml"
