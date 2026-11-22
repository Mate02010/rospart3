#!/bin/bash
# Uso: clip.sh <nombre> <guion.sh> <segundos_max> <ros2 launch ... gui:=false>
# Abre la simulación en la pantalla oculta :99 (Gazebo con vista mínima, RViz y una terminal) y la graba.
V="/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/video"
PARAR="/mnt/c/Users/BRAYAN MATEO BRAVO L/AppData/Local/Temp/claude/50ac824fe08f93e3/fb118709-910e-49e3-94da-4587ba8cc395/scratchpad/parar.sh"
N=$1; G=$2; T=$3; shift 3
bash "$PARAR" >/dev/null 2>&1; pkill xterm 2>/dev/null; pkill -f "gz sim -g" 2>/dev/null; rm -f /tmp/guion_listo
bash "$V/pantalla.sh" >/dev/null
source "$V/entorno.sh"
"$@" > ~/proyecto_final_ws/logs/video_$N.log 2>&1 &
for i in $(seq 1 60); do timeout 10 ros2 topic echo /clock --once >/dev/null 2>&1 && break; sleep 2; done
gz sim -g --gui-config "$V/gazebo_video.config" -v 1 > /tmp/gz_gui_$N.log 2>&1 &
bash "$V/acomodar.sh" "Gazebo Sim" 0 0 960 620
bash "$V/acomodar.sh" "RViz" 960 0 960 620
sleep 10
bash "$V/grabar.sh" $N 12
sleep 2
bash "$V/terminal.sh" "Terminal" "$V/$G" 0 640 1920 440 >/dev/null
for i in $(seq 1 $T); do [ -f /tmp/guion_listo ] && break; sleep 1; done
[ -f /tmp/guion_listo ] || echo "AVISO: el guion de $N no terminó en $T s"
sleep 5
bash "$V/cortar.sh" >/dev/null
ffmpeg -loglevel error -y -sseof -2 -i ~/videos/$N.mp4 -frames:v 1 "$V/clips/${N}_ultimo_cuadro.png"
pkill xterm; pkill -f "gz sim -g"; bash "$PARAR" >/dev/null 2>&1
echo "$N: $(ffprobe -v error -show_entries format=duration -of csv=p=0 ~/videos/$N.mp4) s"
