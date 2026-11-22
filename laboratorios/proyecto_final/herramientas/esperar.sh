#!/bin/bash
# Uso: esperar.sh <archivo> <segundos_max>
for i in $(seq 1 $2); do
  [ -f "$1" ] && { echo "listo tras ${i}s"; exit 0; }
  sleep 1
done
echo "timeout"
