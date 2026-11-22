set -e
SRC="/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/proyecto_final_ws/src/"
mkdir -p ~/proyecto_final_ws/src ~/proyecto_final_ws/resultados ~/proyecto_final_ws/logs
rsync -a --delete "$SRC" ~/proyecto_final_ws/src/
find ~/proyecto_final_ws/src -type f \( -name "*.py" -o -name "*.xacro" -o -name "*.yaml" -o -name "*.sdf" -o -name "*.xml" -o -name "*.txt" -o -name "*.rviz" -o -name "*.md" \) -exec sed -i 's/\r$//' {} +
find ~/proyecto_final_ws/src -path "*/scripts/*.py" -exec chmod +x {} +
source /opt/ros/kilted/setup.bash
cd ~/proyecto_final_ws && colcon build --symlink-install --cmake-force-configure 2>&1 | grep -E "Finished|Failed|error|Error" | head -10
