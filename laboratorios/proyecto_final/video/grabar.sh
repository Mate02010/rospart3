#!/bin/bash
# Uso: grabar.sh <nombre> [fps]   graba la pantalla :99 a ~/videos/<nombre>.mp4 hasta que se llame a cortar.sh
mkdir -p ~/videos
F=${2:-12}
nohup ffmpeg -y -loglevel error -f x11grab -video_size 1920x1080 -framerate $F -i :99 \
  -c:v libx264 -preset ultrafast -crf 26 -pix_fmt yuv420p ~/videos/$1.mp4 > ~/videos/$1.log 2>&1 &
echo $! > ~/videos/grabando.pid
echo "grabando $1 (pid $(cat ~/videos/grabando.pid))"
