"""Graba ejecuciones reales de Gazebo y conserva resultados ROS y metadatos."""
from pathlib import Path
import json
import math
import signal
import subprocess
import threading
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy
from std_msgs.msg import String

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / 'evidencias'
VIDEOS = EVIDENCE / 'videos'
VIDEOS.mkdir(exist_ok=True)
(EVIDENCE / 'logs').mkdir(parents=True, exist_ok=True)
status_file = EVIDENCE / 'video_status.txt'
status_file.write_text('Preparando prueba')

# Camara X hacia delante y Z hacia arriba, orientada al centro de la celda.
camera = (1.2, 1.2, 1.1)
target = (0.0, 0.0, 0.4)
yaw = math.atan2(target[1]-camera[1], target[0]-camera[0])
pitch = math.atan2(camera[2]-target[2], math.hypot(target[0]-camera[0], target[1]-camera[1]))
qx = -math.sin(yaw/2)*math.sin(pitch/2)
qy = math.cos(yaw/2)*math.sin(pitch/2)
qz = math.sin(yaw/2)*math.cos(pitch/2)
qw = math.cos(yaw/2)*math.cos(pitch/2)
request = f'pose: {{position: {{x: {camera[0]}, y: {camera[1]}, z: {camera[2]}}}, orientation: {{x: {qx}, y: {qy}, z: {qz}, w: {qw}}}}}'
subprocess.run(['gz', 'service', '-s', '/gui/move_to/pose', '--reqtype', 'gz.msgs.GUICamera',
    '--reptype', 'gz.msgs.Boolean', '--timeout', '5000', '--req', request], check=True)
window = subprocess.check_output(['xdotool', 'search', '--onlyvisible', '--name', '^Gazebo Sim$'], text=True).strip()
if len(window.split()) != 1:
    raise RuntimeError('Ventana Gazebo ambigua')

rclpy.init()
observer = Node('observador_evidencia')
def update_status(msg):
    event = json.loads(msg.data)
    status_file.write_text(f"{event.get('kind', '')}  {event.get('point', '')}")
observer.create_subscription(String, '/lab/status', update_status,
    QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL))
worker = threading.Thread(target=lambda: rclpy.spin(observer), daemon=True)
worker.start()
records = []
try:
    for number, mode in [(3, 'topics'), (4, 'moveit')]:
        video = VIDEOS / f'{number:02}_{mode}_gazebo.mp4'
        title = 'ROS 2 - comandos por topicos' if mode == 'topics' else 'MoveIt 2 - planificacion y ejecucion'
        caption = (
            f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='{title}':x=12:y=54:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.7,"
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:textfile=video_status.txt:reload=1:x=12:y=88:fontsize=20:fontcolor=white:box=1:boxcolor=black@0.7,"
            "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='Pieza logica - sin agarre por contacto':x=12:y=h-72:fontsize=17:fontcolor=white:box=1:boxcolor=black@0.7"
        )
        with (EVIDENCE / 'logs' / f'grabacion_{mode}.log').open('w') as encoder_log:
            recorder = subprocess.Popen(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'warning',
                '-f', 'x11grab', '-framerate', '10', '-window_id', window, '-i', ':0',
                '-vf', caption, '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '25',
                '-pix_fmt', 'yuv420p', str(video)], stdin=subprocess.PIPE,
                stdout=encoder_log, stderr=encoder_log, cwd=str(EVIDENCE))
            start = time.time()
            try:
                time.sleep(1)
                with (EVIDENCE / 'logs' / f'rutina_{mode}_grabada.log').open('w') as output:
                    result = subprocess.run(['ros2', 'run', 'lab_manipulador', 'pick_place', '--ros-args',
                        '-p', f'mode:={mode}', '-p', 'use_sim_time:=true', '-p', f'output_dir:={EVIDENCE}'],
                        stdout=output, stderr=subprocess.STDOUT, timeout=360)
                time.sleep(2)
            finally:
                recorder.communicate(b'q', timeout=30)
            if result.returncode:
                raise RuntimeError(f'La prueba {mode} fallo: revisar log')
            record = json.loads((EVIDENCE / f'resultado_{mode}.json').read_text())
            assert record['success'], record['error']
            assert len({tuple(p) for p in record['poses'].values()}) >= 3
            assert any(e['kind'] == 'digital_input_confirmed' for e in record['events'])
            if mode == 'moveit':
                assert sum(e['kind'] == 'plan_success' for e in record['events']) == 8
            records.append({'mode': mode, 'success': True, 'wall_duration_sec': time.time()-start,
                'video': video.name, 'movements': sum(e['kind']=='motion_success' for e in record['events'])})
            print(json.dumps(records[-1]), flush=True)
finally:
    rclpy.shutdown()
    worker.join(timeout=3)
    observer.destroy_node()
(EVIDENCE / 'validacion_videos.json').write_text(json.dumps(records, indent=2))
