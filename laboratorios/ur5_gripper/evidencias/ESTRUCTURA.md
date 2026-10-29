# Organización de la práctica

Se conserva esta práctica dentro de `rospart3/laboratorios/ur5_gripper`, por elección del autor. La disposición sigue la de las otras prácticas: README de entrada, paquetes ROS accesibles desde la raíz de la práctica y recursos de documentación en `evidencias/`.

| Organización anterior | Organización actual |
|---|---|
| `codigo/src/<paquete>` | `<paquete>` |
| `output/pdf/Reporte_Laboratorio_UR5_Gripper.pdf` | `evidencias/Informe_UR5_Gripper.pdf` |
| Generador del reporte en Python | `evidencias/informe/main.tex`, plantilla IEEE/LaTeX |
| `evidencias/videos` | `evidencias/videos` e índice `evidencias/VIDEO.md` |
| JSON de pruebas publicados | `evidencias/resultados` |
| Capturas del reporte | `evidencias/informe/figuras` |
| Scripts auxiliares en la raíz | `herramientas` |

El informe usa `IEEEtran` a dos columnas, como los anteriores de Robótica. La versión previa queda conservada en la rama `codex/ur5-gripper-moveit`. Los programas ROS y las grabaciones de la ejecución original se conservan; se actualizan las rutas del lanzador y de las herramientas auxiliares.

Para compilar la nueva estructura, ejecutar `bash ejecutar.sh build` desde esta carpeta. El overlay está ahora en `install/setup.bash`, no en `codigo/install/setup.bash`. Los resultados de futuras ejecuciones se guardan en `ejecuciones_locales/`, que Git ignora, para conservar intactos los JSON históricos.

## Nombre de evidencias (28-oct-2026)

Por solicitud del autor, la carpeta de recursos se llama `evidencias/`. Contiene el informe, sus fuentes, videos y mediciones históricas. Las nuevas ejecuciones se guardan en `ejecuciones_locales/`, excluida de Git, para no reemplazar las evidencias conservadas. Los cuatro paquetes son necesarios para aplicación, descripción del robot, simulación/controladores y configuración MoveIt. No se han eliminado paquetes ni prácticas anteriores.
