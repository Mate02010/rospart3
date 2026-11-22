#!/usr/bin/env python3
"""Práctica 5: dibuja los recorridos de probar_nav.py sobre el mapa de la bodega.

Un panel por corrida (p5_sin_obstaculo, p5_con_obstaculo, p5_meta_bloqueada, ...):
recorrido real de cada meta, primer plan global, metas, punto de partida y la caja si se
puso. Arriba de cada panel, los totales y qué recuperaciones corrió el BT.

Uso: python3 graficar_p5.py <carpeta_resultados> <png_salida> [mapa.yaml]
"""
import csv
import glob
import json
import math
import os
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import yaml
from matplotlib.colors import to_rgb
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

TINTA = '#0b0b0b'
TINTA_2 = '#52514e'
REJILLA = '#e4e3df'
SERIES = ['#2a78d6', '#eb6834', '#1baf7a', '#6250d6']
CAJA = '#6250d6'


def mapa_por_defecto():
    try:
        from ament_index_python.packages import get_package_share_directory
        ruta = os.path.join(get_package_share_directory('dif_bot'), 'maps', 'bodega.yaml')
        if os.path.isfile(ruta):
            return ruta
    except Exception:
        pass
    # Con --symlink-install el script apunta a src/dif_bot/scripts.
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'maps', 'bodega.yaml')


def leer_pgm(ruta):
    """Lee un PGM (P5 binario o P2 texto) y lo devuelve en [0, 1]."""
    with open(ruta, 'rb') as f:
        datos = f.read()
    campos, i = [], 0
    while len(campos) < 4:
        while datos[i:i + 1].isspace():
            i += 1
        if datos[i:i + 1] == b'#':
            while datos[i:i + 1] not in (b'\n', b''):
                i += 1
            continue
        j = i
        while not datos[j:j + 1].isspace():
            j += 1
        campos.append(datos[i:j])
        i = j
    magia, ancho, alto, maximo = campos[0], int(campos[1]), int(campos[2]), int(campos[3])
    i += 1  # un solo espacio separa la cabecera de los datos
    if magia == b'P5':
        tipo = np.uint8 if maximo < 256 else '>u2'
        img = np.frombuffer(datos, dtype=tipo, count=ancho * alto, offset=i)
    elif magia == b'P2':
        img = np.array(datos[i:].split()[:ancho * alto], dtype=float)
    else:
        raise ValueError(f'{ruta}: formato {magia!r} no soportado')
    return img.reshape(alto, ancho).astype(float) / maximo


def leer_mapa(ruta_yaml):
    """Imagen RGB del mapa (libre, ocupado, desconocido) recortada a la zona conocida y su extent."""
    with open(ruta_yaml, encoding='utf-8') as f:
        info = yaml.safe_load(f)
    ruta_img = info['image']
    if not os.path.isabs(ruta_img):
        ruta_img = os.path.join(os.path.dirname(ruta_yaml), ruta_img)
    gris = leer_pgm(ruta_img)
    ocupacion = gris if info.get('negate', 0) else 1.0 - gris
    ocupado = ocupacion > info.get('occupied_thresh', 0.65)
    libre = ocupacion < 0.1  # solo para dibujar: el gris 205 de map_saver queda como desconocido

    rgb = np.empty(gris.shape + (3,))
    rgb[:] = to_rgb(REJILLA)
    rgb[libre] = (1.0, 1.0, 1.0)
    rgb[ocupado] = to_rgb(TINTA_2)

    # Recorte a lo conocido con un margen de 6 celdas.
    filas, cols = np.nonzero(libre | ocupado)
    alto, ancho = gris.shape
    f0, f1 = max(filas.min() - 6, 0), min(filas.max() + 6, alto - 1)
    c0, c1 = max(cols.min() - 6, 0), min(cols.max() + 6, ancho - 1)
    res = float(info['resolution'])
    ox, oy = float(info['origin'][0]), float(info['origin'][1])
    if abs(float(info['origin'][2])) > 1e-6:
        print('Aviso: el mapa tiene yaw en origin; se dibuja sin rotar.')
    extent = [ox + c0 * res, ox + (c1 + 1) * res, oy + (alto - 1 - f1) * res, oy + (alto - f0) * res]
    return rgb[f0:f1 + 1, c0:c1 + 1], extent


def leer_recorrido(ruta_csv):
    por_meta = {}
    with open(ruta_csv, encoding='utf-8') as f:
        for fila in csv.DictReader(f):
            xs, ys = por_meta.setdefault(int(fila['meta']), ([], []))
            xs.append(float(fila['x']))
            ys.append(float(fila['y']))
    return por_meta


def titulo_de(etiqueta):
    nombres = {'sin_obstaculo': 'Sin obstáculo', 'con_obstaculo': 'Con obstáculo',
               'meta_bloqueada': 'Meta bloqueada'}
    return nombres.get(etiqueta, etiqueta.replace('_', ' ').capitalize())


def panel(ax, imagen, extent, res, recorrido):
    ax.imshow(imagen, extent=extent, origin='upper', interpolation='nearest')

    for m in res['metas']:
        if m.get('plan_inicial'):
            px, py = zip(*m['plan_inicial'])
            ax.plot(px, py, color=TINTA_2, linewidth=2, linestyle=(0, (4, 3)), alpha=0.7,
                    label='Primer plan global')
    for m in res['metas']:
        k = m['meta']
        color = SERIES[(k - 1) % len(SERIES)]
        if k in recorrido:
            ax.plot(*recorrido[k], color=color, linewidth=2, label=f'Recorrido meta {k}')
        ax.plot(m['x'], m['y'], marker='o', markersize=9, markerfacecolor='white',
                markeredgecolor=color, markeredgewidth=2, linestyle='none')
        nombre = f'M{k}' if m['resultado'] == 'exito' else f"M{k} ({m['resultado'].replace('_', ' ')})"
        ax.annotate(nombre, (m['x'], m['y']), xytext=(7, 7), textcoords='offset points',
                    color=TINTA, fontsize=9)

    x0, y0 = res['pose_inicial'][:2]
    ax.plot(x0, y0, marker='s', markersize=7, color=TINTA, linestyle='none', label='Inicio')

    caja = res.get('caja')
    if caja and 'x' in caja and caja.get('creada') is not False:
        lado = caja.get('lado', 0.5)
        ax.add_patch(Rectangle((caja['x'] - lado / 2, caja['y'] - lado / 2), lado, lado,
                               facecolor=CAJA, edgecolor=TINTA, linewidth=1, label='Caja añadida'))

    tot = res['totales']
    lineas = [f"{tot['exitos']}/{tot['metas']} metas · {tot['distancia_m']:.1f} m recorridos · "
              f"{tot['tiempo_s']:.0f} s · {tot['recuperaciones']} recuperaciones"]
    detalle = []
    if tot.get('comportamientos'):
        detalle.append(', '.join(f'{n} ×{c}' for n, c in tot['comportamientos'].items()))
    if caja and caja.get('esquiva_s') is not None:
        detalle.append(f"plan nuevo {caja['esquiva_s']:.1f} s después de aparecer la caja")
    # Siempre dos renglones (el segundo puede ir vacío) para que los títulos queden alineados.
    lineas.append(' · '.join(detalle) or ' ')
    ax.text(0.0, 1.005, '\n'.join(lineas), transform=ax.transAxes, color=TINTA_2, fontsize=8.5,
            va='bottom', ha='left')
    ax.set_title(titulo_de(res['etiqueta']), color=TINTA, fontsize=11, loc='left', pad=28)
    ax.set_xlabel('x [m]', color=TINTA_2, fontsize=9)
    ax.set_ylabel('y [m]', color=TINTA_2, fontsize=9)
    ax.set_aspect('equal')
    for lado in ('top', 'right'):
        ax.spines[lado].set_visible(False)
    for lado in ('left', 'bottom'):
        ax.spines[lado].set_color(TINTA_2)
    ax.tick_params(colors=TINTA_2, labelsize=9)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    carpeta, salida = sys.argv[1], sys.argv[2]
    ruta_mapa = sys.argv[3] if len(sys.argv) > 3 else mapa_por_defecto()
    imagen, extent = leer_mapa(ruta_mapa)

    # Primero la corrida sin obstáculo, luego el resto en orden alfabético.
    rutas = sorted(glob.glob(os.path.join(carpeta, 'p5_*.json')),
                   key=lambda r: (not r.endswith('p5_sin_obstaculo.json'), r))
    if not rutas:
        sys.exit(f'No hay p5_*.json en {carpeta}')

    ancho_mapa = extent[1] - extent[0]
    alto_mapa = extent[3] - extent[2]
    n = len(rutas)
    fig, ejes = plt.subplots(1, n, figsize=(6.4 * n, 6.4 * alto_mapa / ancho_mapa + 1.4), squeeze=False)
    for ax, ruta in zip(ejes[0], rutas):
        with open(ruta, encoding='utf-8') as f:
            res = json.load(f)
        recorrido = leer_recorrido(ruta[:-5] + '.csv')
        panel(ax, imagen, extent, res, recorrido)

    # Una sola leyenda arriba, sin repetir entradas entre paneles.
    entradas = {}
    for ax in ejes[0]:
        for h, nombre in zip(*ax.get_legend_handles_labels()):
            entradas.setdefault(nombre, h)
    entradas['Meta'] = Line2D([], [], marker='o', markersize=9, markerfacecolor='white',
                              markeredgecolor=TINTA_2, markeredgewidth=2, linestyle='none')
    fig.legend(list(entradas.values()), list(entradas.keys()), loc='upper center',
               ncol=min(len(entradas), 4), frameon=False, fontsize=10, labelcolor=TINTA)
    filas_leyenda = math.ceil(len(entradas) / 4)
    fig.tight_layout(rect=(0, 0, 1, 1 - 0.06 * filas_leyenda))
    fig.savefig(salida, dpi=150, facecolor='white')
    print('Guardado', salida)


if __name__ == '__main__':
    main()
