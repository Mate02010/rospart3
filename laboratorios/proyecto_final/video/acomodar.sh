#!/bin/bash
# Uso: acomodar.sh "<parte del título>" x y ancho alto   (espera hasta 90 s a que aparezca la ventana)
export DISPLAY=:99
for i in $(seq 1 90); do
  W=$(xdotool search --name "$1" 2>/dev/null | tail -1)
  [ -n "$W" ] && break
  sleep 1
done
[ -z "$W" ] && { echo "no apareció: $1"; exit 1; }
xdotool windowsize $W $4 $5 windowmove $W $2 $3
echo "ventana '$1' en $2,$3 ${4}x$5"
