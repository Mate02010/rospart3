source "/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/video/mostrar.sh"
esperar_topico /odom_filtered
nota "Práctica 2: EKF (robot_localization) con odometría de ruedas + IMU."
mostrar "ros2 topic info /odom_filtered -v | grep -E 'Node name|Publisher count'"
mostrar "ros2 param get /ekf_filter_node odom0 && ros2 param get /ekf_filter_node imu0"
nota "Cuadrado de 1 m. En RViz: flechas azules = ruedas, verdes = EKF."
mostrar "ros2 run dif_bot comparar_ekf.py --ros-args -p use_sim_time:=true -p vueltas:=1 -p etiqueta:=video -p salida:=/tmp > /dev/null 2>&1"
mostrar "python3 -c \"import json; d=json.load(open('/tmp/p2_video.json')); print('ruedas:', d['ruedas']); print('EKF   :', d['ekf'])\""
touch /tmp/guion_listo
