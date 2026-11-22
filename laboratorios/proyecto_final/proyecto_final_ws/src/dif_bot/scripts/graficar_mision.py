#!/usr/bin/env python3
"""Proyecto final: grafica la misión sobre el mapa (ruta real, estimación de AMCL y waypoints).

Uso: python3 graficar_mision.py <mision_...json> <png_salida> <mapa.yaml>
"""
import csv
import json
import math
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import yaml

TINTA = '#0b0b0b'
TINTA_2 = '#52514e'
REAL = '#2a78d6'
AMCL = '#eb6834'
META = '#1baf7a'


def leer_pgm(ruta):
    with open(ruta, 'rb') as f:
        datos = f.read()
    partes, i = [], 0
    while len(partes) < 4:
        while datos[i:i + 1].isspace():
            i += 1
        if datos[i:i + 1] == b'#':
            while datos[i:i + 1] not in (b'\n', b''):
                i += 1
            continue
        j = i
        while not datos[j:j + 1].isspace():
            j += 1
        partes.append(datos[i:j])
        i = j
    ancho, alto, maximo = int(partes[1]), int(partes[2]), int(partes[3])
    i += 1
    dtype = np.uint8 if maximo < 256 else np.dtype('>u2')
    return np.frombuffer(datos[i:], dtype=dtype, count=ancho * alto).reshape(alto, ancho)


def main():
    archivo, salida, mapa = sys.argv[1], sys.argv[2], sys.argv[3]
    res = json.load(open(archivo, encoding='utf-8'))
    tray = archivo[:-5] + '_trayectoria.csv'
    with open(tray, encoding='utf-8') as f:
        filas = list(csv.DictReader(f))

    info = yaml.safe_load(open(mapa, encoding='utf-8'))
    img = leer_pgm(os.path.join(os.path.dirname(mapa), info['image']))
    r = info['resolution']
    x0, y0 = info['origin'][0], info['origin'][1]
    extension = [x0, x0 + img.shape[1] * r, y0, y0 + img.shape[0] * r]

    fig, ax = plt.subplots(figsize=(10, 7.2))
    ax.imshow(img, cmap='gray', extent=extension, vmin=0, vmax=255)
    ax.plot([float(p['x_amcl']) for p in filas], [float(p['y_amcl']) for p in filas],
            color=AMCL, linewidth=2, label='Estimación AMCL')
    ax.plot([float(p['x_real']) for p in filas], [float(p['y_real']) for p in filas],
            color=REAL, linewidth=2, label='Recorrido real (Gazebo)')
    for w in res['waypoints']:
        ax.plot(w['x'], w['y'], 'o', markersize=11, markerfacecolor='white', markeredgecolor=META,
                markeredgewidth=2.5)
        yaw = math.radians(w['yaw_deg'])
        ax.annotate('', xy=(w['x'] + 0.45 * math.cos(yaw), w['y'] + 0.45 * math.sin(yaw)), xytext=(w['x'], w['y']),
                    arrowprops=dict(arrowstyle='->', color=META, lw=2))
        ax.text(w['x'] + 0.25, w['y'] + 0.25, f"{w['indice']}. {w['nombre']}", fontsize=9, color=TINTA)
    ax.plot([], [], 'o', markerfacecolor='white', markeredgecolor=META, markeredgewidth=2.5, label='Waypoint')
    ax.set_title(f"Misión '{res['mision']}': {res['waypoints_logrados']}/{res['waypoints_total']} waypoints, "
                 f"{res['distancia_real_m']:.1f} m en {res['tiempo_total_s']:.0f} s",
                 color=TINTA, fontsize=11, loc='left')
    ax.set_xlabel('x [m]', color=TINTA_2)
    ax.set_ylabel('y [m]', color=TINTA_2)
    ax.tick_params(colors=TINTA_2, labelsize=9)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.09), ncol=3, frameon=False)
    fig.tight_layout()
    fig.savefig(salida, dpi=150, facecolor='white')
    print('Guardado', salida)


if __name__ == '__main__':
    main()
