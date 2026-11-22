#!/bin/bash
for i in $(seq 1 560); do
  f=$(ls ~/proyecto_final_ws/resultados/mision_recorrido_bodega_*.json 2>/dev/null | head -1)
  [ -n "$f" ] && { echo "listo tras ${i}s: $f"; exit 0; }
  sleep 1
done
echo timeout
