#!/bin/bash
bash "/mnt/c/Users/BRAYAN MATEO BRAVO L/AppData/Local/Temp/claude/50ac824fe08f93e3/fb118709-910e-49e3-94da-4587ba8cc395/scratchpad/parar.sh" >/dev/null 2>&1
G="/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/proyecto_final_ws/src/dif_bot/scripts/graficar_p4.py"
D="/mnt/c/Users/BRAYAN MATEO BRAVO L/Documents/ChatGPT/Universidad/Robotica/Corte 3/Proyecto_Final/evidencias/p4"
R=~/proyecto_final_ws/resultados
cat > $R/p4_global_manual.json <<'J'
{"etiqueta": "global_manual", "pose_inicial": "localización global (/reinitialize_global_localization), partículas en todo el mapa",
 "movimiento": "1 vuelta en el sitio a 0.8 rad/s y 1.2 m en recta a 0.25 m/s (teleoperado)",
 "amcl_final": [-0.62, -0.18, -165.3], "real_final": [-0.61, -0.16, -165.8], "error_final_m": 0.03, "error_final_yaw_deg": 0.5,
 "desviacion_final": {"x_m": 0.18, "y_m": 0.07, "yaw_deg": 9.3}}
J
mkdir -p "$D/resultados"
cd $R
python3 "$G" "$D/p4_pose_inicial.png" "Pose correcta=p4_pose_correcta.csv" "Pose incorrecta (1.3 m, 34°)=p4_pose_incorrecta.csv" 2>&1 | tail -1
python3 "$G" "$D/p4_pose_muy_lejos.png" "Pose muy lejos (4.1 m, 143°)=p4_pose_muy_lejos.csv" 2>&1 | tail -1
python3 "$G" "$D/p4_ruido.png" "Ruido láser 0.01 m=p4_pose_correcta.csv" "Ruido láser 0.15 m=p4_ruido_alto.csv" 2>&1 | tail -1
cp $R/p4_* "$D/resultados/"; cp -r ~/proyecto_final_ws/evidencias/p4/* "$D/"; ls "$D" "$D/resultados"
