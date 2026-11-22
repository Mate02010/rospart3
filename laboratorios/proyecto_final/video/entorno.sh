# Variables para abrir ventanas en la pantalla oculta :99 (no en la pantalla del usuario).
source /opt/ros/kilted/setup.bash
source ~/proyecto_final_ws/install/setup.bash
export DISPLAY=:99
unset WAYLAND_DISPLAY
export QT_QPA_PLATFORM=xcb
export LIBGL_ALWAYS_SOFTWARE=1
cd ~/proyecto_final_ws
