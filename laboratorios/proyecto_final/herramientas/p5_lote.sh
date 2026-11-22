#!/bin/bash
source /opt/ros/kilted/setup.bash
source ~/proyecto_final_ws/install/setup.bash
cd ~/proyecto_final_ws
S="/mnt/c/Users/BRAYAN MATEO BRAVO L/AppData/Local/Temp/claude/50ac824fe08f93e3/fb118709-910e-49e3-94da-4587ba8cc395/scratchpad"
correr() {  # correr <etiqueta> [params probar_nav...]; reintenta una vez si el controlador no arrancó
  E=$1; shift
  for intento in 1 2; do
    bash "$S/parar.sh" >/dev/null 2>&1
    ros2 launch dif_bot navegacion.launch.py gui:=false rviz:=false > logs/p5_$E.log 2>&1 &
    echo "=== $E intento $intento ($(date +%T))"
    bash "$S/p5.sh" $E "$@" 2>&1 | grep -aE "CONTROLADOR|Meta [0-9]|meta [0-9]|Caja|caja|Resumen" | cut -c1-300
    [ -f resultados/p5_$E.json ] && break
  done
}
# correr sin_obstaculo   (ya hecha)
correr con_obstaculo -p obstaculo:=true
correr meta_bloqueada -p bloquear_meta:=true
bash "$S/parar.sh" >/dev/null 2>&1
echo "FIN $(date +%T)"
