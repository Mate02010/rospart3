#!/bin/bash
python3 - <<'PY'
import json, glob, os
for f in sorted(glob.glob(os.path.expanduser('~/proyecto_final_ws/resultados/p5_*.json'))):
    if 'invalida' in f or 'tolerancia' in f: continue
    d = json.load(open(f))
    print('==', d['etiqueta'], 'totales', d.get('totales'))
    if d.get('caja'): print('   caja', {k: v for k, v in d['caja'].items() if not isinstance(v, (list, dict))})
    for m in d.get('metas', []):
        print('  ', {k: v for k, v in m.items() if k in ('meta','x','y','resultado','codigo_error','mensaje_error','tiempo_s','recuperaciones','comportamientos','largo_plan_m','distancia_recorrida_m','error_final_m')})
PY
