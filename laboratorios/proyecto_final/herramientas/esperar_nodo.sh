#!/bin/bash
# Uso: esperar_nodo.sh <patron_proceso> <segundos_max> <espera_extra>
for i in $(seq 1 $2); do
  if pgrep -f "$1" >/dev/null; then sleep $3; echo "visto tras ${i}s"; exit 0; fi
  sleep 1
done
echo timeout
