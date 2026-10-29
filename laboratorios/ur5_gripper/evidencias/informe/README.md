# Informe IEEE y proyecto Overleaf

`main.tex` utiliza la misma clase `IEEEtran` de los informes anteriores de Robótica: dos columnas, bloque de autor, resumen, secciones académicas, figuras, tablas, ecuación de error y referencias.

## Abrir en Overleaf

1. Crear un proyecto en blanco o importar el ZIP de fuentes entregado localmente.
2. Subir `main.tex`, `IEEEtran.cls` y la carpeta `figuras/`, conservando sus nombres.
3. Seleccionar `main.tex` como documento principal y el compilador **pdfLaTeX**.
4. Compilar; una segunda pasada resuelve referencias a figuras, tablas y bibliografía.

El PDF final se publica en [../Informe_UR5_Gripper.pdf](../Informe_UR5_Gripper.pdf). No es necesario ejecutar los paquetes ROS para compilar el informe. Las figuras provienen de las pruebas originales y sus captions distinguen Setup Assistant, RViz y Gazebo.

Para una instalación local de TeX Live se requieren las fuentes Times y los paquetes habituales declarados en el preámbulo. El editor integrado y Overleaf pueden compilar esta carpeta directamente.
