#!/bin/bash
bash "/mnt/c/Users/BRAYAN MATEO BRAVO L/AppData/Local/Temp/claude/50ac824fe08f93e3/fb118709-910e-49e3-94da-4587ba8cc395/scratchpad/parar.sh" >/dev/null 2>&1
WIN_PKG="/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/proyecto_final_ws/src/dif_bot"
R=~/proyecto_final_ws/resultados
for e in lento rapido; do
  m=bodega; [ $e = rapido ] && m=bodega_rapido
  python3 "$WIN_PKG/scripts/evaluar_mapa.py" "$WIN_PKG/maps/$m.yaml" "$WIN_PKG/worlds/bodega.sdf" $R --etiqueta $e --trayectoria $R/p3_ruta_$e.csv 2>&1 | tail -3
done
python3 - <<'PY'
import json, os
R = os.path.expanduser('~/proyecto_final_ws/resultados')
for e in ('lento', 'rapido'):
    d = json.load(open(f'{R}/p3_mapa_{e}.json'))
    print('==', e)
    def plano(x, pre=''):
        for k, v in x.items():
            if isinstance(v, dict):
                plano(v, pre + k + '.')
            elif not isinstance(v, list):
                print(f'  {pre}{k}: {v}')
    plano(d)
PY
