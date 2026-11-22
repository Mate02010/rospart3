#!/bin/bash
# Termina la grabación en curso (SIGINT para que ffmpeg cierre bien el mp4).
P=$(cat ~/videos/grabando.pid 2>/dev/null)
[ -n "$P" ] && kill -INT $P 2>/dev/null
for i in $(seq 1 20); do kill -0 $P 2>/dev/null || break; sleep 0.5; done
rm -f ~/videos/grabando.pid
echo "grabación cerrada"
