#!/bin/bash
# Uso: terminal.sh "<titulo>" <script> x y ancho alto   abre un xterm en :99 que corre el script (se ve el comando y su salida)
export DISPLAY=:99
xterm -T "$1" -fa "DejaVu Sans Mono" -fs 11 -bg "#101418" -fg "#e6e6e6" -geometry 100x20 \
  -e bash -c "source '/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/video/entorno.sh'; bash '$2'; echo; echo '[fin]'; sleep 600" &
sleep 2
bash "/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/video/acomodar.sh" "$1" $3 $4 $5 $6
