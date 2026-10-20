"""Reporte academico reproducible, construido a partir de los resultados medidos."""
from pathlib import Path
import json
from xml.sax.saxutils import escape
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

ROOT = Path(__file__).resolve().parent
E = ROOT / 'evidencias'
OUT = ROOT / 'output/pdf'
OUT.mkdir(parents=True, exist_ok=True)
publication_file = ROOT / 'publicacion.json'
publication = json.loads(publication_file.read_text(encoding='utf-8')) if publication_file.exists() else None
topics = json.loads((E/'resultado_topics.json').read_text())
moveit = json.loads((E/'resultado_moveit.json').read_text())
assert topics['success'] and moveit['success']

font_root = Path('C:/Windows/Fonts')
if not font_root.exists():
    font_root = Path('/usr/share/fonts/truetype/dejavu')
    regular, bold = 'DejaVuSans.ttf', 'DejaVuSans-Bold.ttf'
else:
    regular, bold = 'arial.ttf', 'arialbd.ttf'
pdfmetrics.registerFont(TTFont('Lab', str(font_root/regular)))
pdfmetrics.registerFont(TTFont('LabBold', str(font_root/bold)))
pdfmetrics.registerFontFamily('Lab', normal='Lab', bold='LabBold', italic='Lab', boldItalic='LabBold')
BLUE = colors.HexColor('#173B58')
TEAL = colors.HexColor('#087E8B')
GREY = colors.HexColor('#E9EFF3')
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='LabBody', fontName='Lab', fontSize=9.5, leading=14, spaceAfter=8, textColor=colors.HexColor('#243440')))
styles.add(ParagraphStyle(name='LabSmall', parent=styles['LabBody'], fontSize=8, leading=11, spaceAfter=5))
styles.add(ParagraphStyle(name='LabH1', fontName='LabBold', fontSize=17, leading=21, textColor=BLUE, spaceAfter=14))
styles.add(ParagraphStyle(name='LabH2', fontName='LabBold', fontSize=11.5, leading=16, textColor=TEAL, spaceBefore=9, spaceAfter=7))
styles.add(ParagraphStyle(name='LabTitle', fontName='LabBold', fontSize=25, leading=30, textColor=BLUE, spaceAfter=18))
styles.add(ParagraphStyle(name='LabCaption', parent=styles['LabSmall'], textColor=colors.HexColor('#506371'), alignment=TA_CENTER))
story = []
WIDTH = 483

def para(text, style='LabBody'):
    return Paragraph(text, styles[style])

def add(text, style='LabBody'):
    story.append(para(text, style))

def table(rows, widths, header=True):
    cells = [[para(str(c), 'LabSmall') for c in row] for row in rows]
    t = Table(cells, colWidths=widths, hAlign='LEFT', repeatRows=1 if header else 0)
    rules = [('VALIGN',(0,0),(-1,-1),'TOP'), ('LEFTPADDING',(0,0),(-1,-1),7),
        ('RIGHTPADDING',(0,0),(-1,-1),7), ('TOPPADDING',(0,0),(-1,-1),7),
        ('BOTTOMPADDING',(0,0),(-1,-1),5), ('LINEBELOW',(0,0),(-1,0),.7,TEAL),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,GREY])]
    if header:
        rules += [('BACKGROUND',(0,0),(-1,0),GREY)]
    t.setStyle(TableStyle(rules))
    story.extend([t, Spacer(1,9)])

def figure(name, caption, width=WIDTH, max_height=270):
    path = E / name
    iw, ih = ImageReader(str(path)).getSize()
    height = width*ih/iw
    if height > max_height:
        width *= max_height/height
        height = max_height
    image = Image(str(path), width=width, height=height)
    image.hAlign='CENTER'
    story.append(KeepTogether([image, Spacer(1,5), para(caption,'LabCaption')]))
    story.append(Spacer(1,6))

def link(label, path, raw=False):
    if publication:
        url = publication['folder_url'] if not path else (publication['raw_base'] if raw or path.endswith('.mp4') else publication['file_base']) + '/' + path
    else:
        # El PDF vive en output/pdf: los enlaces conservan la estructura del ZIP.
        url = '../../' + (path or 'README.md')
    return f'<link href="{escape(url)}" color="#087E8B"><u>{escape(label)}</u></link>'

def counts(record):
    motions=[e for e in record['events'] if e['kind']=='motion_success']
    arm=[e['max_error'] for e in motions if e['group']=='arm']
    grip=[e['max_error'] for e in motions if e['group']=='gripper']
    return len(motions), max(arm), max(grip), record['events'][-1]['time']-record['events'][0]['time']

def footer(c, doc):
    c.setStrokeColor(TEAL); c.setLineWidth(.6); c.line(56,43,539,43)
    c.setFont('Lab',7.5); c.setFillColor(BLUE)
    c.drawString(56,30,'Robótica | UR5 con gripper | Brayan Mateo Bravo Losada')
    c.drawRightString(539,30,str(doc.page))

add('LABORATORIO DE ROBÓTICA','LabH2')
add('UR5 con gripper<br/>Control ROS 2 y planificación con MoveIt','LabTitle')
add('<b>Brayan Mateo Bravo Losada</b><br/>Ingeniería Electrónica<br/>Escuela Colombiana de Ingeniería Julio Garavito<br/>20 de octubre de 2026')
add('Resumen','LabH2')
add('Se construyeron los paquetes del UR5 con una pinza paralela de dos dedos y se ejecutó una rutina de cuatro puntos mediante tópicos ROS 2. Se generó una configuración con MoveIt Setup Assistant y se verificó la planificación y ejecución de los grupos del brazo y de la pinza desde RViz y desde un nodo Python. Las ejecuciones grabadas completaron ocho movimientos cada una, incluyendo apertura, cierre y confirmación digital simulada.')
add('1. Objetivo y alcance','LabH2')
add('Integrar descripción cinemática, simulación, controladores y planificación en un workspace local. El brazo y los dedos se simulan en Gazebo. La recogida y entrega de una pieza se representan mediante estados lógicos: esta práctica no acredita agarre por contacto físico ni uso de un robot real.')
table([['Componente','Entorno utilizado'], ['Sistema','Windows con WSL2; Ubuntu 24.04.4 LTS'],
       ['ROS y simulador','ROS 2 Kilted; Gazebo Sim Ionic 9.5.0'],
       ['Planificación','MoveIt 2 y Setup Assistant 2.14.3; OMPL/RRTConnect'],
       ['Control','gz_ros2_control; controlador del brazo y JointTrajectoryController de pinza'],
       ['Base docente','DanielPalominoS/ur5_gripper_packages; revisión 87a547dfde78']],[117,366])
add('Se reutilizó el entorno previamente instalado. Los paquetes se compilaron con colcon; los resultados corresponden a esta implementación y a las mediciones guardadas en los archivos JSON de evidencia.','LabSmall')
story.append(PageBreak())

add('2. Construcción y rutina por tópicos','LabH1')
add('La entrega contiene cuatro paquetes: <b>ur5_robotiq_description</b>, <b>ur5_robotiq_bringup</b>, <b>lab_manipulador</b> y <b>ur5_gripper_moveit</b>. La compilación concluyó con los cuatro paquetes finalizados. Los lanzadores comparten el dominio ROS 74 y el reloj de Gazebo.')
add('Puntos y operaciones','LabH2')
table([['Punto','Objetivo articular [rad]','Operación'],
 ['Preparación','[0, -1.57, 1.57, -1.57, -1.57, 0]','Mensaje informativo y apertura'],
 ['Recogida','[0.35, -1.45, 1.80, -1.92, -1.57, 0]','Cierre y estado lógico de recogida'],
 ['Intermedio','[0, -1.20, 1.40, -1.77, -1.57, 0]','Salida digital ALTA'],
 ['Entrega','[-0.40, -1.45, 1.80, -1.92, -1.57, 0]','Apertura y espera digital']],[82,223,178])
add('Cada objetivo es distinto. Tras la entrega, la aplicación observa una entrada BAJA seguida de una nueva entrada ALTA y regresa a Preparación. El nodo digital permite confirmación manual mediante SetBool o un pulsador automático de demostración que publica el cambio después de 1.5 s.')
table([['Interfaz','Tipo / propósito'],
 ['/scaled_joint_trajectory_controller/<br/>joint_trajectory','trajectory_msgs/msg/JointTrajectory: seis articulaciones del brazo'],
 ['/gripper_controller/joint_trajectory','trajectory_msgs/msg/JointTrajectory: dos dedos'],
 ['/joint_states','sensor_msgs/msg/JointState: comprobación de posición final'],
 ['/lab/digital_input y /lab/digital_output','std_msgs/msg/Bool: señales de entrada y salida'],
 ['/lab/set_digital_input','std_srvs/srv/SetBool: confirmación manual']],[235,248])
add('Reproducción mínima','LabH2')
add('Desde la carpeta de entrega: <b>bash ejecutar.sh build</b>. Mantener terminales independientes con <b>bash ejecutar.sh sim true</b>, <b>bash ejecutar.sh io true</b> y <b>bash ejecutar.sh planificador</b>. En otra terminal ejecutar <b>bash ejecutar.sh topics</b> o <b>bash ejecutar.sh moveit</b>, una rutina a la vez. El README incluye comandos manuales completos y el modo de entrada digital manual.','LabSmall')
story.append(PageBreak())

add('3. Configuración con Setup Assistant','LabH1')
add('Se cargó <b>ur_with_gripper_moveit.urdf.xacro</b> en la interfaz gráfica y se generó la matriz de autocolisiones con 10 000 muestras. El archivo SRDF y los archivos de configuración se produjeron mediante el botón de generación del asistente; la grabación y la captura permiten revisar ese proceso.')
table([['Elemento','Configuración'], ['Brazo','Grupo arm; cadena base_link → tool0; solucionador KDL'],
 ['Pinza','Grupo gripper; gripper_finger_joint y right_finger_joint'],
 ['Efector','eef; grupo gripper; montaje en tool0; grupo padre arm'],
 ['Referencia fija','world ya existe en el URDF; no se añadió un virtual joint redundante'],
 ['Ejecución','FollowJointTrajectory para brazo y pinza']],[103,380])
figure('07_paquete_generado.png','Figura 1. Paquete generado en la interfaz gráfica de MoveIt Setup Assistant.',max_height=235)
add('Ajustes de integración','LabH2')
add('Después de la generación se alineó el nombre del controlador del brazo con <b>scaled_joint_trajectory_controller</b>, se añadieron los cuatro estados del brazo y los estados Open/Close de la pinza, se habilitaron límites de aceleración y se configuró OMPL/RRTConnect. El launch de integración consume los estados y los controladores de Gazebo; no inicia otro gestor de hardware. Estos ajustes están documentados en completar_configuracion.py.','LabSmall')
story.append(PageBreak())

add('4. Verificación y resultados','LabH1')
t = counts(topics); m = counts(moveit)
table([['Prueba','Movimientos','Error máx. brazo','Error máx. dedo','Tiempo rutina'],
 ['Tópicos ROS',f'{t[0]}/8',f'{t[1]:.6f} rad',f'{t[2]:.6f} m',f'{t[3]:.1f} s'],
 ['Nodo MoveIt',f'{m[0]}/8',f'{m[1]:.6f} rad',f'{m[2]:.6f} m',f'{m[3]:.1f} s']],[103,69,113,111,87])
add('Los errores se calcularon comparando la consigna con /joint_states. Para el control por tópicos se exigió error menor que 0.02 rad en el brazo y 0.002 m en los dedos durante varias actualizaciones. MoveIt también verificó el resultado de sus acciones y validó ocho planes. Los tiempos son de pared entre el primer y el último evento, no tiempos de simulación.')
add('Pruebas desde RViz','LabH2')
add('En MotionPlanning se seleccionó el grupo arm, inicio &lt;current&gt; y objetivo Recogida; se pulsó Plan y luego Execute. La planificación tardó aproximadamente 0.079 s y la ejecución terminó con SUCCEEDED. Se repitió el procedimiento con el grupo gripper y el objetivo Close: planificación aproximada de 0.062 s y ejecución correcta. Los tiempos de planificación pertenecen a esas consultas puntuales.')
imgs=[]
for name in ['10_rviz_plan_brazo.png','16_rviz_gripper_completado.png']:
    iw,ih=ImageReader(str(E/name)).getSize()
    imgs.append(Image(str(E/name),width=235,height=235*ih/iw))
story.append(Table([imgs],colWidths=[241.5,241.5]))
add('Figura 2. Verificación de los grupos arm y gripper desde el plugin de MoveIt en RViz.','LabCaption')
add('Evidencia auditable','LabH2')
add('Los JSON contienen objetivos, secuencia de operaciones, muestras articulares y el indicador de éxito. Los videos de las rutinas conservan su tiempo real y muestran los estados de la aplicación. Los resúmenes de Setup Assistant y RViz indican explícitamente reproducción x8 y x4, respectivamente.','LabSmall')
story.append(PageBreak())

add('5. Hallazgos y recursos de entrega','LabH1')
table([['Hallazgo','Solución aplicada'],
 ['Control de la pinza','El controlador original recibía posiciones por tópico y no ofrecía GripperCommand. Se usó JointTrajectoryController con los dos dedos y la misma acción FollowJointTrajectory en MoveIt.'],
 ['Lanzamiento y modelo','Se corrigieron -z, la ruta del mundo, el suelo de espesor cero y los estados iniciales. Las rutas con espacios se entrecomillaron; Setup Assistant se abrió con --urdf_path y un alias temporal.'],
 ['Planificador instalado','Se utilizó el identificador RRTConnect de los archivos instalados, en lugar del nombre RRTConnectkConfigDefault de la práctica anterior.'],
 ['Funciones no utilizadas','El escenario no incorpora percepción 3D ni reconocimiento de objetos. Sus avisos de disponibilidad no impidieron las planificaciones y ejecuciones verificadas.']],[112,371])
add('Alcance del resultado','LabH2')
add('Se verificaron brazo, dedos, señales digitales y planificación en simulación. La pieza es lógica y no se validaron contacto, fuerza de agarre ni transferencia a hardware. La matriz de colisiones está basada en muestreo; no constituye una prueba formal para todas las configuraciones. El trabajo cubre los puntos solicitados de control, nodo de rutina, configuración y ejecución MoveIt, con evidencias de ambas vías.')
add('Enlaces de la solución','LabH2')
add('Código, configuración, resultados y videos se reúnen en la carpeta del laboratorio del repositorio Mate02010/rospart3. Los enlaces siguientes permiten consultar la solución y descargar las grabaciones. También se adjunta una copia local con la misma estructura de archivos.' if publication else 'Entrega local por elección del estudiante: código, configuración y videos adjuntos. Los enlaces siguientes son relativos a este PDF y requieren conservar la estructura de carpetas del ZIP. La publicación del repositorio y los enlaces públicos de videos quedan pendientes.','LabSmall')
add(link('Código y guía de ejecución','')+'<br/>'+link('Nodo Pick and Place','codigo/src/lab_manipulador/lab_manipulador/pick_place.py')+'<br/>'+link('Paquete de configuración MoveIt','codigo/src/ur5_gripper_moveit/package.xml')+'<br/>'+link('Resultados de la prueba mediante MoveIt','evidencias/resultado_moveit.json'),'LabSmall')
for label,name in [('Configuración con Setup Assistant (x8)','01_setup_assistant_resumen.mp4'),
                   ('Planificación de ambos grupos en RViz (x4)','02_rviz_grupos_resumen.mp4'),
                   ('Rutina mediante tópicos ROS, tiempo real','03_topics_gazebo.mp4'),
                   ('Rutina mediante MoveIt, tiempo real','04_moveit_gazebo.mp4')]:
    add(link(label,'evidencias/videos/'+name),'LabSmall')
add('Referencias','LabH2')
for label,url in [
 ('Repositorio y guía del profesor','https://github.com/DanielPalominoS/ur5_gripper_packages'),
 ('ROS 2 Kilted: instalación en Ubuntu','https://docs.ros.org/en/kilted/Installation/Ubuntu-Install-Debs.html'),
 ('Compatibilidad de ROS y Gazebo','https://gazebosim.org/docs/fortress/ros_installation/')]:
    add(f'<link href="{escape(url)}" color="#087E8B"><u>{escape(label)}</u></link>','LabSmall')

pdf = OUT / 'Reporte_Laboratorio_UR5_Gripper.pdf'
doc = SimpleDocTemplate(str(pdf), pagesize=(595.28,841.89), rightMargin=56,leftMargin=56,
                        topMargin=48,bottomMargin=56,title='UR5 con gripper: ROS 2 y MoveIt',
                        author='Brayan Mateo Bravo Losada')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print(pdf)
