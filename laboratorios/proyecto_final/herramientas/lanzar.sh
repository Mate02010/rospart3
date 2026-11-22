# Uso: lanzar.sh <nombre_log> <comando ros2 ...>
source /opt/ros/kilted/setup.bash
source ~/proyecto_final_ws/install/setup.bash
mkdir -p ~/proyecto_final_ws/logs
LOG=~/proyecto_final_ws/logs/$1.log; shift
echo "[$(date +%H:%M:%S)] $*" > "$LOG"
exec "$@" >> "$LOG" 2>&1
