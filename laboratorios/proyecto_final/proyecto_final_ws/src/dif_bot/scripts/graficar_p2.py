#!/usr/bin/env python3
"""Práctica 2: grafica las corridas de comparar_ekf.py (con y sin IMU).

Uso: python3 graficar_p2.py <carpeta_resultados> <png_salida>
"""
import csv
import math
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

TINTA = '#0b0b0b'
TINTA_2 = '#52514e'
REJILLA = '#e4e3df'
RUEDAS = '#eb6834'
EKF = '#2a78d6'


def leer(ruta):
    with open(ruta, encoding='utf-8') as f:
        filas = list(csv.DictReader(f))
    return {k: [float(r[k]) for r in filas] for k in filas[0]}


def error_yaw(d, fuente):
    return [abs(math.degrees(math.atan2(math.sin(a - b), math.cos(a - b))))
            for a, b in zip(d[f'yaw_{fuente}'], d['yaw_real'])]


def estilo(ax):
    ax.grid(True, color=REJILLA, linewidth=0.8)
    for lado in ('top', 'right'):
        ax.spines[lado].set_visible(False)
    for lado in ('left', 'bottom'):
        ax.spines[lado].set_color(TINTA_2)
    ax.tick_params(colors=TINTA_2, labelsize=9)


def main():
    carpeta, salida = sys.argv[1], sys.argv[2]
    corridas = [('con_imu', 'Con IMU'), ('sin_imu', 'Sin IMU')]
    fig, ejes = plt.subplots(2, 2, figsize=(10, 8.4), gridspec_kw={'height_ratios': [1.35, 1]})

    for col, (etiqueta, titulo) in enumerate(corridas):
        d = leer(f'{carpeta}/p2_{etiqueta}.csv')

        ax = ejes[0][col]
        ax.plot(d['x_real'], d['y_real'], color=TINTA, linewidth=2, linestyle='--', label='Real (Gazebo)')
        ax.plot(d['x_ruedas'], d['y_ruedas'], color=RUEDAS, linewidth=2, label='Odometría ruedas')
        ax.plot(d['x_ekf'], d['y_ekf'], color=EKF, linewidth=2, label='EKF (/odom_filtered)')
        ax.set_aspect('equal', adjustable='datalim')
        ax.set_title(f'{titulo}: trayectoria', color=TINTA, fontsize=11, loc='left')
        ax.set_xlabel('x [m]', color=TINTA_2, fontsize=9)
        ax.set_ylabel('y [m]', color=TINTA_2, fontsize=9)
        estilo(ax)

        ax = ejes[1][col]
        ax.plot(d['t'], error_yaw(d, 'ruedas'), color=RUEDAS, linewidth=2, label='Odometría ruedas')
        ax.plot(d['t'], error_yaw(d, 'ekf'), color=EKF, linewidth=2, label='EKF')
        ax.set_title(f'{titulo}: error de orientación', color=TINTA, fontsize=11, loc='left')
        ax.set_xlabel('tiempo [s]', color=TINTA_2, fontsize=9)
        ax.set_ylabel('|error yaw| [°]', color=TINTA_2, fontsize=9)
        ax.set_ylim(0, 22)
        estilo(ax)

    # Una sola leyenda arriba para las tres fuentes.
    manejadores, nombres = ejes[0][0].get_legend_handles_labels()
    fig.legend(manejadores, nombres, loc='upper center', ncol=3, frameon=False, fontsize=10,
               labelcolor=TINTA)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(salida, dpi=150, facecolor='white')
    print('Guardado', salida)


if __name__ == '__main__':
    main()
