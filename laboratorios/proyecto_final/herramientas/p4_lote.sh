#!/bin/bash
# Corre varios experimentos de AMCL, cada uno con un localizacion.launch.py nuevo.
source /opt/ros/kilted/setup.bash
source ~/proyecto_final_ws/install/setup.bash
cd ~/proyecto_final_ws
S="/mnt/c/Users/BRAYAN MATEO BRAVO L/AppData/Local/Temp/claude/50ac824fe08f93e3/fb118709-910e-49e3-94da-4587ba8cc395/scratchpad"
correr() {  # correr <etiqueta> <args_launch> -- <args_evaluar...>
  E=$1; LA=$2; shift 2
  bash "$S/parar.sh" >/dev/null 2>&1
  ros2 launch dif_bot localizacion.launch.py gui:=false rviz:=false $LA > logs/p4_$E.log 2>&1 &
  bash "$S/p4.sh" $E "$@" 2>&1 | grep -a '"etiqueta"' | python3 -c "
import sys, json
for l in sys.stdin:
    d = json.loads(l[l.index('{'):])
    print(d['etiqueta'], {k: v for k, v in d.items() if k in ('convergio','tiempo_convergencia_s','recorrido_al_converger_m','error_inicial_m','error_final_m','error_final_yaw_deg','error_rms_post_convergencia_m','error_rms_post_convergencia_yaw_deg','error_max_post_convergencia_m')})
"
}
correr ruido_alto "ruido_laser:=0.15"
correr pose_muy_lejos "" -p x0:=-3.0 -p y0:=2.8 -p yaw0:=2.5
bash "$S/parar.sh" >/dev/null 2>&1
