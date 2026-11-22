# Uso: evid.sh <carpeta_evidencia> ; guarda info de nodos, topicos y TF
source /opt/ros/kilted/setup.bash; source ~/proyecto_final_ws/install/setup.bash; cd ~/proyecto_final_ws
D=~/proyecto_final_ws/evidencias/$1; mkdir -p $D; cd $D
{ echo "### ros2 node list"; ros2 node list; echo; for t in "${@:2}"; do echo "### ros2 topic info -v $t"; ros2 topic info -v $t 2>&1 | grep -E "Type|Publisher count|Subscription count|Node name|Topic type" ; echo; done; } > info_nodos_topicos.txt 2>&1
timeout 15 ros2 run tf2_tools view_frames -o arbol_tf > /dev/null 2>&1 || true
ls $D; head -40 info_nodos_topicos.txt
