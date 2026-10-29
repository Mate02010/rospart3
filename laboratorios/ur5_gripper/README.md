# UR5 con gripper: ROS 2 y MoveIt

**Curso:** Robótica, Corte 2, Práctica 2, Escuela Colombiana de Ingeniería Julio Garavito.  
**Autor:** Brayan Mateo Bravo Losada.  
**Entorno utilizado:** Ubuntu 24.04 en WSL2, ROS 2 Kilted, Gazebo Sim Ionic 9.5.0 y MoveIt 2.

Rutina Pick and Place con cuatro puntos diferentes, pinza articulada y confirmación digital simulada. Se verificaron el control por tópicos, la configuración de MoveIt Setup Assistant, Plan/Execute en RViz y la ejecución desde un nodo MoveIt.

## Contenido

```text
ur5_gripper/
├── README.md
├── ejecutar.sh
├── lab_manipulador/             Nodos pick_place y digital_io
├── ur5_robotiq_description/     Modelo UR5 y dedos prismáticos
├── ur5_robotiq_bringup/         Gazebo, mundo y controladores
├── ur5_gripper_moveit/          Configuración generada en Setup Assistant
├── herramientas/               Ajustes de configuración y grabación
└── evidencias/
    ├── capturas/               Capturas de Setup Assistant, RViz y Gazebo
    ├── VIDEO.md                Índice de los cuatro videos
    ├── videos/                 Grabaciones MP4
    ├── resultados/             Mediciones JSON de las pruebas
    ├── COMANDOS_ROS.md
    ├── CONFIGURACION_MOVEIT.md
    ├── RESULTADOS.md
    └── ESTRUCTURA.md
```

## Documentación

El informe académico se entrega por separado y se conserva localmente. Este repositorio no incluye el PDF, el proyecto LaTeX ni los archivos de Overleaf. Las evidencias públicas son videos, capturas, resultados y documentación técnica.

## Videos de demostración

<details>
<summary><b>▶ Ver videos: UR5 con gripper</b></summary>

- [01 - Generación con Setup Assistant, x8](evidencias/videos/01_setup_assistant_resumen.mp4).
- [02 - Plan y Execute de brazo y pinza en RViz, x4](evidencias/videos/02_rviz_grupos_resumen.mp4).
- [03 - Rutina por tópicos ROS, tiempo real](evidencias/videos/03_topics_gazebo.mp4).
- [04 - Rutina mediante MoveIt, tiempo real](evidencias/videos/04_moveit_gazebo.mp4).

[Índice con enlaces directos y duraciones](evidencias/VIDEO.md)

</details>

## Compilación

Si ya tienes la copia, sitúate en esta carpeta. Para obtenerla desde GitHub:

```bash
git clone https://github.com/Mate02010/rospart3.git
cd rospart3/laboratorios/ur5_gripper
bash ejecutar.sh build
```

El script utiliza ROS Kilted ya instalado y compila únicamente los cuatro paquetes de esta práctica. No instala programas. Los paquetes y el overlay quedan en esta carpeta; `build/`, `install/` y `log/` se generan localmente y no se versionan.

## Ejecución

Mantener procesos en terminales independientes, todas situadas en esta carpeta:

```bash
# Terminal 1: simulación; false permite ejecutarla sin interfaz gráfica.
bash ejecutar.sh sim true

# Terminal 2: señales digitales; true confirma automáticamente después de 1.5 s.
bash ejecutar.sh io true

# Terminal 3: MoveIt y RViz sobre los controladores de Gazebo.
bash ejecutar.sh planificador
```

En una cuarta terminal ejecutar **una rutina a la vez**:

```bash
bash ejecutar.sh topics
# Al terminar, se puede probar la otra vía:
bash ejecutar.sh moveit
```

Se usa `ROS_DOMAIN_ID=74`. No iniciar otra simulación en ese dominio mientras esta esté en uso. Finalizar cada proceso con Ctrl+C. Los JSON de una nueva ejecución se guardan en `ejecuciones_locales/`, sin sobrescribir los resultados históricos de `evidencias/resultados/`.

## Actividades realizadas

1. Construcción de paquetes y movimientos del brazo y la pinza mediante `JointTrajectory`.
2. Nodo Pick and Place: Preparación, Recogida, Intermedio y Entrega, más retorno a Preparación.
3. Apertura, cierre, mensajes, salida digital y espera de una entrada BAJA seguida de una nueva ALTA.
4. Configuración generada desde Setup Assistant para los grupos `arm` y `gripper`.
5. Plan y Execute de ambos grupos desde RViz y ocho movimientos desde el nodo MoveIt.

Para controlar el robot por comandos, demostrar la espera manual y revisar los grupos, consultar [COMANDOS_ROS.md](evidencias/COMANDOS_ROS.md) y [CONFIGURACION_MOVEIT.md](evidencias/CONFIGURACION_MOVEIT.md).

## Resultados y alcance

Las dos rutinas registradas completaron **8/8 movimientos**, recorrieron **cuatro objetivos distintos** y recibieron la confirmación digital. Las mediciones están en [RESULTADOS.md](evidencias/RESULTADOS.md) y los JSON originales en [evidencias/resultados](evidencias/resultados).

El brazo y los dedos son articulaciones simuladas en Gazebo. La pieza recogida es un estado lógico: no se acredita agarre por contacto, fuerza de sujeción, protocolo propietario de Robotiq ni ejecución sobre un robot físico.

## Base utilizada

Adaptado de [DanielPalominoS/ur5_gripper_packages](https://github.com/DanielPalominoS/ur5_gripper_packages), revisión `87a547dfde78df811fd5964c7f6ff4882630c9f8`. Se conservan los nombres de sus paquetes. Las adaptaciones de controladores y configuración están explicadas en la documentación. La organización anterior se conserva en la rama `codex/ur5-gripper-moveit`; la versión actual de esta práctica está en `main`.
