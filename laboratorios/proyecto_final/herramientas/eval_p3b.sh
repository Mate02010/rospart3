#!/bin/bash
bash "/mnt/c/Users/BRAYAN MATEO BRAVO L/AppData/Local/Temp/claude/50ac824fe08f93e3/fb118709-910e-49e3-94da-4587ba8cc395/scratchpad/parar.sh" >/dev/null 2>&1
WIN_PKG="/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/proyecto_final_ws/src/dif_bot"
R=~/proyecto_final_ws/resultados
python3 "$WIN_PKG/scripts/evaluar_mapa.py" "$WIN_PKG/maps/bodega_muy_rapido.yaml" "$WIN_PKG/worlds/bodega.sdf" $R --etiqueta muy_rapido --trayectoria $R/p3_ruta_muy_rapido.csv > /dev/null 2>&1
python3 - <<'PY'
import json, os
R = os.path.expanduser('~/proyecto_final_ws/resultados')
for e in ('lento', 'rapido', 'muy_rapido'):
    d = json.load(open(f'{R}/p3_mapa_{e}.json')); r = json.load(open(f'{R}/p3_ruta_{e}.json'))
    print(e, 'ruta', {k: r[k] for k in r if not isinstance(r[k], (list, dict))})
    print('   exactitud', d['exactitud']['media_m'], d['exactitud']['p95_m'], d['exactitud']['max_m'],
          'completitud', d['completitud']['fraccion'], 'espurias', d['espurias']['celdas'],
          'ocupadas', d['celdas']['ocupadas'], 'cobertura', d['cobertura_libre'])
PY
D="/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/evidencias/p3"
mkdir -p "$D/resultados"; cp $R/p3_* "$D/resultados/"; cp -r ~/proyecto_final_ws/evidencias/p3/* "$D/" 2>/dev/null; ls "$D" "$D/resultados"
