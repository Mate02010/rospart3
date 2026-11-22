#!/bin/bash
python3 - <<'PY'
import json, glob, os
for f in sorted(glob.glob(os.path.expanduser('~/proyecto_final_ws/resultados/p4_*.json'))):
    d = json.load(open(f))
    print(d['etiqueta'], {k: v for k, v in d.items() if k in ('pose_inicial_dada','convergio','tiempo_convergencia_s','recorrido_al_converger_m','error_inicial_m','error_inicial_yaw_deg','error_final_m','error_final_yaw_deg','error_max_m','error_rms_post_convergencia_m','error_rms_post_convergencia_yaw_deg','error_max_post_convergencia_m')})
PY
