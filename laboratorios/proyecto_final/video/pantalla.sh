#!/bin/bash
# Arranca la pantalla oculta :99 (1920x1080) con openbox si no está corriendo.
if ! pgrep -f "Xvfb :99" >/dev/null; then
  nohup Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp > /tmp/xvfb.log 2>&1 &
  sleep 2
fi
if ! pgrep -x openbox >/dev/null; then
  DISPLAY=:99 nohup openbox > /tmp/openbox.log 2>&1 &
  sleep 1
fi
DISPLAY=:99 xsetroot -solid "#202020" 2>/dev/null
echo "pantalla :99 lista"
