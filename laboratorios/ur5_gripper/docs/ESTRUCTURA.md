# Organización de la práctica

Se conserva esta práctica dentro de `rospart3/laboratorios/ur5_gripper`, por elección del autor. La disposición sigue la de las otras prácticas: README de entrada, paquetes ROS accesibles desde la raíz de la práctica y recursos de documentación en `docs/`.

| Organización anterior | Organización actual |
|---|---|
| `codigo/src/<paquete>` | `<paquete>` |
| `output/pdf/Reporte_Laboratorio_UR5_Gripper.pdf` | `docs/Informe_UR5_Gripper.pdf` |
| Generador del reporte en Python | `docs/informe/main.tex`, plantilla IEEE/LaTeX |
| `evidencias/videos` | `docs/videos` e índice `docs/VIDEO.md` |
| JSON de pruebas publicados | `docs/resultados` |
| Capturas del reporte | `docs/informe/figuras` |
| Scripts auxiliares en la raíz | `herramientas` |

El informe usa `IEEEtran` a dos columnas, como los anteriores de Robótica. La versión previa queda conservada en la rama `codex/ur5-gripper-moveit`. Los programas ROS y las grabaciones de la ejecución original se conservan; se actualizan las rutas del lanzador y de las herramientas auxiliares.

Para compilar la nueva estructura, ejecutar `bash ejecutar.sh build` desde esta carpeta. El overlay está ahora en `install/setup.bash`, no en `codigo/install/setup.bash`. Los resultados de futuras ejecuciones se guardan en `evidencias/`, que Git ignora, para conservar intactos los JSON históricos.
