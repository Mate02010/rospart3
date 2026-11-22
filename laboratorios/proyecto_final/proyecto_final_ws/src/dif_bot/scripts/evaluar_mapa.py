#!/usr/bin/env python3
"""Práctica 3: mide la calidad de un mapa de SLAM comparándolo con el mundo de Gazebo.

Pasa a la grilla del mapa los obstáculos verdaderos del SDF (cajas y cilindros del
modelo 'estructura', muros exteriores incluidos) y calcula:
  - exactitud: distancia de cada celda ocupada del mapa a la superficie real más
    cercana (media, mediana, percentil 95). Con 5 cm por celda, un mapa perfecto
    ya da 1 a 3 cm solo por la discretización;
  - completitud: fracción del borde real visible (el que da al interior de la
    bodega) que tiene una celda ocupada del mapa a 0,10 m o menos;
  - celdas espurias: ocupadas a más de 0,15 m de cualquier obstáculo real.
Supone que el marco map coincide con world (el SLAM arrancó con el robot en el origen).

Guarda un JSON con las métricas y un PNG con el mapa en grises, el contorno real en
azul, las celdas espurias en naranja y el borde que no quedó en el mapa en violeta.

Uso:
  python3 evaluar_mapa.py <mapa.yaml> <mundo.sdf> <carpeta_salida> [--etiqueta lento]
                          [--trayectoria p3_ruta_lento.csv]
  ros2 run dif_bot evaluar_mapa.py maps/bodega.yaml worlds/bodega.sdf ~/proyecto_final_ws/resultados
"""
import argparse
import csv
import json
import math
import os
import xml.etree.ElementTree as ET

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
import numpy as np
import yaml
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Patch, Polygon

TINTA = '#0b0b0b'
TINTA_2 = '#52514e'
REJILLA = '#e4e3df'
REAL = '#2a78d6'
ESPURIA = '#eb6834'
RUTA = '#1baf7a'
FALTANTE = '#6250d6'


# ---------------------------------------------------------------- mapa

def leer_pgm(ruta):
    """Lee un PGM binario (P5) o de texto (P2) y devuelve grises de 0 a 255."""
    with open(ruta, 'rb') as f:
        datos = f.read()
    campos, i = [], 0
    while len(campos) < 4:  # tipo, ancho, alto y valor máximo; '#' inicia un comentario
        while i < len(datos) and datos[i:i + 1].isspace():
            i += 1
        if datos[i:i + 1] == b'#':
            while i < len(datos) and datos[i:i + 1] not in (b'\n', b'\r'):
                i += 1
            continue
        j = i
        while j < len(datos) and not datos[j:j + 1].isspace():
            j += 1
        campos.append(datos[i:j])
        i = j
    tipo, ancho, alto, maximo = campos[0], int(campos[1]), int(campos[2]), int(campos[3])
    if tipo == b'P5':
        tipo_dato = '>u2' if maximo > 255 else 'u1'
        img = np.frombuffer(datos, dtype=tipo_dato, count=ancho * alto, offset=i + 1)
    elif tipo == b'P2':
        img = np.array([int(t) for t in datos[i:].split()[:ancho * alto]], dtype=float)
    else:
        raise ValueError(f'{ruta}: formato {tipo!r} no soportado (solo P5 o P2)')
    return img.reshape(alto, ancho).astype(float) * 255.0 / maximo


def leer_imagen(ruta):
    if ruta.lower().endswith('.pgm'):
        return leer_pgm(ruta)
    from PIL import Image  # PNG u otro formato
    return np.asarray(Image.open(ruta).convert('L'), dtype=float)


def cargar_mapa(ruta_yaml):
    """Devuelve la clase de cada celda (1 ocupada, 0 libre, -1 desconocida) y los metadatos."""
    with open(ruta_yaml, encoding='utf-8') as f:
        meta = yaml.safe_load(f)
    imagen = meta['image']
    if not os.path.isabs(imagen):
        imagen = os.path.join(os.path.dirname(os.path.abspath(ruta_yaml)), imagen)
    gris = leer_imagen(imagen)
    modo = meta.get('mode', 'trinary')
    negate = int(meta.get('negate', 0))
    umbral_ocupada = float(meta.get('occupied_thresh', 0.65))
    umbral_libre = float(meta.get('free_thresh', 0.25))

    # Misma regla que map_server: p = probabilidad de ocupación del píxel.
    if modo == 'raw':
        p = np.where(gris <= 100, gris / 100.0, np.nan)
    else:
        p = gris / 255.0 if negate else (255.0 - gris) / 255.0
    clase = np.full(gris.shape, -1, dtype=np.int8)
    clase[p > umbral_ocupada] = 1
    clase[p < umbral_libre] = 0
    if modo == 'trinary' and not negate:
        # map_saver guarda lo desconocido con gris 205 (p = 0,196), que con
        # free_thresh = 0,25 caería como libre.
        clase[np.round(gris) == 205] = -1

    return clase, {
        'imagen': imagen,
        'resolucion': float(meta['resolution']),
        'origen': [float(v) for v in meta['origin']],
        'modo': modo,
        'negate': negate,
        'occupied_thresh': umbral_ocupada,
        'free_thresh': umbral_libre,
    }


# ---------------------------------------------------------------- mundo

def leer_pose(elemento):
    """(x, y, yaw) de la etiqueta <pose> de un elemento; el robot es plano."""
    p = elemento.find('pose')
    if p is None or not (p.text or '').strip():
        return 0.0, 0.0, 0.0
    v = [float(t) for t in p.text.split()]
    yaw = math.radians(v[5]) if p.get('degrees') == 'true' else v[5]
    return v[0], v[1], yaw


def componer(a, b):
    x, y, th = a
    c, s = math.cos(th), math.sin(th)
    return x + c * b[0] - s * b[1], y + s * b[0] + c * b[1], th + b[2]


def leer_obstaculos(ruta_sdf, modelo='estructura'):
    """Cajas y cilindros de colisión del modelo, en el marco world."""
    obstaculos = []
    for m in ET.parse(ruta_sdf).getroot().iter('model'):
        if m.get('name') != modelo:
            continue
        pose_modelo = leer_pose(m)
        for link in m.findall('link'):
            pose_link = componer(pose_modelo, leer_pose(link))
            for col in link.findall('collision'):
                x, y, yaw = componer(pose_link, leer_pose(col))
                caja = col.find('geometry/box/size')
                cilindro = col.find('geometry/cylinder/radius')
                if caja is not None:
                    sx, sy = (float(t) for t in caja.text.split()[:2])
                    obstaculos.append({'nombre': link.get('name'), 'tipo': 'caja',
                                       'centro': (x, y), 'yaw': yaw, 'medio': (sx / 2, sy / 2)})
                elif cilindro is not None:
                    obstaculos.append({'nombre': link.get('name'), 'tipo': 'cilindro',
                                       'centro': (x, y), 'radio': float(cilindro.text)})
    if not obstaculos:
        raise ValueError(f'No hay cajas ni cilindros en el modelo {modelo!r} de {ruta_sdf}')
    return obstaculos


def distancia_con_signo(px, py, ob):
    """Distancia al borde del obstáculo: positiva afuera, negativa adentro."""
    dx, dy = px - ob['centro'][0], py - ob['centro'][1]
    if ob['tipo'] == 'cilindro':
        return np.hypot(dx, dy) - ob['radio']
    c, s = math.cos(ob['yaw']), math.sin(ob['yaw'])
    qx = np.abs(c * dx + s * dy) - ob['medio'][0]
    qy = np.abs(-s * dx + c * dy) - ob['medio'][1]
    afuera = np.hypot(np.maximum(qx, 0.0), np.maximum(qy, 0.0))
    adentro = np.minimum(np.maximum(qx, qy), 0.0)
    return afuera + adentro


def vertices(ob):
    if ob['tipo'] == 'cilindro':
        (x, y), r = ob['centro'], ob['radio']
        return [(x - r, y - r), (x + r, y + r)]
    (x, y), (hx, hy), c, s = ob['centro'], ob['medio'], math.cos(ob['yaw']), math.sin(ob['yaw'])
    return [(x + c * a - s * b, y + s * a + c * b) for a, b in ((hx, hy), (-hx, hy), (-hx, -hy), (hx, -hy))]


# ---------------------------------------------------------------- grilla

def dilatar(mascara, radio_celdas):
    """Marca las celdas a radio_celdas o menos (distancia euclídea) de una celda marcada."""
    r = int(math.floor(radio_celdas))
    alto, ancho = mascara.shape
    grande = np.zeros((alto + 2 * r, ancho + 2 * r), dtype=bool)
    for di in range(-r, r + 1):
        for dj in range(-r, r + 1):
            if di * di + dj * dj <= radio_celdas * radio_celdas + 1e-9:
                grande[r + di:r + di + alto, r + dj:r + dj + ancho] |= mascara
    return grande[r:r + alto, r:r + ancho]


def vecinas(mascara):
    """Celdas con alguna vecina (4-conexión) marcada."""
    v = np.zeros_like(mascara)
    v[1:, :] |= mascara[:-1, :]
    v[:-1, :] |= mascara[1:, :]
    v[:, 1:] |= mascara[:, :-1]
    v[:, :-1] |= mascara[:, 1:]
    return v


def inundar(libre, semilla):
    """Región libre conectada a la celda semilla (4-conexión)."""
    region = np.zeros_like(libre)
    region[semilla] = True
    while True:
        nueva = (region | vecinas(region)) & libre
        if (nueva == region).all():
            return region
        region = nueva


def main():
    ap = argparse.ArgumentParser(description='Compara un mapa de SLAM con los obstáculos del SDF.')
    ap.add_argument('mapa', help='YAML del mapa (map_saver)')
    ap.add_argument('mundo', help='SDF del mundo')
    ap.add_argument('salida', help='carpeta para el JSON y el PNG')
    ap.add_argument('--etiqueta', default=None, help='nombre de la corrida (por defecto, el del YAML)')
    ap.add_argument('--modelo', default='estructura', help='modelo del SDF con los obstáculos')
    ap.add_argument('--trayectoria', default=None, help='CSV de explorar.py para dibujar la ruta')
    ap.add_argument('--inicio', nargs=2, type=float, default=(0.0, 0.0), metavar=('X', 'Y'),
                    help='punto libre dentro de la bodega (world)')
    ap.add_argument('--tol_completitud', type=float, default=0.10)
    ap.add_argument('--tol_espuria', type=float, default=0.15)
    args = ap.parse_args()
    etiqueta = args.etiqueta or os.path.splitext(os.path.basename(args.mapa))[0]

    clase, meta = cargar_mapa(args.mapa)
    obstaculos = leer_obstaculos(args.mundo, args.modelo)
    res = meta['resolucion']
    ox, oy, oyaw = meta['origen']
    c0, s0 = math.cos(oyaw), math.sin(oyaw)
    alto0, ancho0 = clase.shape

    # Agranda la grilla (como desconocida) si el mundo se sale del mapa, para que
    # el borde real que el SLAM no alcanzó a ver también cuente.
    esquinas = np.array([v for ob in obstaculos for v in vertices(ob)])
    u = c0 * (esquinas[:, 0] - ox) + s0 * (esquinas[:, 1] - oy)
    v = -s0 * (esquinas[:, 0] - ox) + c0 * (esquinas[:, 1] - oy)
    izq = max(0, int(math.ceil(-u.min() / res)) + 2)
    der = max(0, int(math.ceil(u.max() / res)) - ancho0 + 2)
    abajo = max(0, int(math.ceil(-v.min() / res)) + 2)
    arriba = max(0, int(math.ceil(v.max() / res)) - alto0 + 2)
    clase = np.pad(clase, ((arriba, abajo), (izq, der)), constant_values=-1)
    alto, ancho = clase.shape

    # Centro de cada celda en el marco world (la fila 0 es el borde de arriba).
    col, fila = np.meshgrid(np.arange(ancho), np.arange(alto))
    uc = (col - izq + 0.5) * res
    vc = (alto0 - 1 - (fila - arriba) + 0.5) * res
    xc = ox + c0 * uc - s0 * vc
    yc = oy + s0 * uc + c0 * vc

    dist = np.stack([distancia_con_signo(xc, yc, ob) for ob in obstaculos])
    sdf = dist.min(axis=0)             # distancia a la unión de obstáculos
    mas_cercano = dist.argmin(axis=0)

    ocupada = clase == 1
    d_sup = np.abs(sdf[ocupada])       # distancia a la superficie real
    espuria = ocupada & (sdf > args.tol_espuria)
    d_buenas = np.abs(sdf[ocupada & ~espuria])

    # Borde real visible: celdas del obstáculo (o a media celda) pegadas a la zona
    # libre a la que llega el robot desde el punto de inicio.
    obstaculo = sdf <= res / 2
    ui = c0 * (args.inicio[0] - ox) + s0 * (args.inicio[1] - oy)
    vi = -s0 * (args.inicio[0] - ox) + c0 * (args.inicio[1] - oy)
    semilla = (arriba + alto0 - 1 - int(math.floor(vi / res)), izq + int(math.floor(ui / res)))
    if obstaculo[semilla]:
        raise ValueError('El punto de inicio cae dentro de un obstáculo; usa --inicio')
    alcanzable = inundar(~obstaculo, semilla)
    borde = obstaculo & vecinas(alcanzable)
    cubierto = dilatar(ocupada, args.tol_completitud / res)
    faltante = borde & ~cubierto

    por_obstaculo = {}
    for k, ob in enumerate(obstaculos):
        b = borde & (mas_cercano == k)
        if b.any():
            por_obstaculo[ob['nombre']] = round(float((b & cubierto).sum() / b.sum()), 3)

    libre_real = alcanzable & ~obstaculo
    resultado = {
        'etiqueta': etiqueta,
        'mapa': os.path.abspath(args.mapa),
        'mundo': os.path.abspath(args.mundo),
        'resolucion_m': res,
        'tamano_celdas': [ancho0, alto0],
        'tamano_m': [round(ancho0 * res, 2), round(alto0 * res, 2)],
        'origen': meta['origen'],
        'celdas': {
            'ocupadas': int(ocupada.sum()),
            'libres': int((clase == 0).sum()),
            'desconocidas': int((clase[arriba:arriba + alto0, izq:izq + ancho0] == -1).sum()),
        },
        'exactitud': {
            'media_m': round(float(d_sup.mean()), 4) if d_sup.size else None,
            'mediana_m': round(float(np.median(d_sup)), 4) if d_sup.size else None,
            'p95_m': round(float(np.percentile(d_sup, 95)), 4) if d_sup.size else None,
            'max_m': round(float(d_sup.max()), 4) if d_sup.size else None,
            'media_sin_espurias_m': round(float(d_buenas.mean()), 4) if d_buenas.size else None,
        },
        'completitud': {
            'fraccion': round(float((borde & cubierto).sum() / max(borde.sum(), 1)), 4),
            'tolerancia_m': args.tol_completitud,
            'celdas_borde': int(borde.sum()),
            'celdas_borde_cubiertas': int((borde & cubierto).sum()),
            'por_obstaculo': por_obstaculo,
        },
        'espurias': {
            'celdas': int(espuria.sum()),
            'fraccion_de_ocupadas': round(float(espuria.sum() / max(ocupada.sum(), 1)), 4),
            'umbral_m': args.tol_espuria,
        },
        # Parte del piso libre real (dentro de la bodega) que el mapa marca como libre.
        'cobertura_libre': round(float((libre_real & (clase == 0)).sum() / max(libre_real.sum(), 1)), 4),
    }

    os.makedirs(args.salida, exist_ok=True)
    base = os.path.join(args.salida, f'p3_mapa_{etiqueta}')
    with open(base + '.json', 'w', encoding='utf-8') as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------ figura
    gris = np.where(clase == 1, 0.25, np.where(clase == 0, 1.0, 0.85))
    capa = np.zeros((alto, ancho, 4))
    capa[faltante] = matplotlib.colors.to_rgba(FALTANTE)
    capa[espuria] = matplotlib.colors.to_rgba(ESPURIA)
    extension = (-izq * res, (ancho - izq) * res, -(alto - alto0 - arriba) * res, (alto0 + arriba) * res)
    ancho_m, alto_m = ancho * res, alto * res
    fig, ax = plt.subplots(figsize=(10, 10 * alto_m / ancho_m + 1.2))
    # La imagen se dibuja en el marco del mapa y se lleva a world con el origen.
    a_world = mtransforms.Affine2D().rotate(oyaw).translate(ox, oy) + ax.transData
    for img, kw in ((gris, {'cmap': 'gray', 'vmin': 0, 'vmax': 1}), (capa, {})):
        ax.imshow(img, extent=extension, origin='upper', interpolation='nearest',
                  transform=a_world, **kw)
    for ob in obstaculos:
        if ob['tipo'] == 'cilindro':
            ax.add_patch(Circle(ob['centro'], ob['radio'], fill=False, edgecolor=REAL, linewidth=1.0))
        else:
            ax.add_patch(Polygon(vertices(ob), closed=True, fill=False, edgecolor=REAL, linewidth=1.0))
    leyenda = [Line2D([], [], color=REAL, linewidth=2, label='Obstáculos reales (SDF)'),
               Patch(color=ESPURIA, label=f'Celdas espurias (> {args.tol_espuria:.2f} m)'),
               Patch(color=FALTANTE, label='Borde real sin mapear')]
    if args.trayectoria:
        with open(args.trayectoria, encoding='utf-8') as f:
            filas = list(csv.DictReader(f))
        ax.plot([float(r['x']) for r in filas], [float(r['y']) for r in filas],
                color=RUTA, linewidth=1.5)
        leyenda.append(Line2D([], [], color=RUTA, linewidth=2, label='Ruta real del robot'))

    esq = np.array([[e0, e2] for e0 in extension[:2] for e2 in extension[2:]])
    xs = ox + c0 * esq[:, 0] - s0 * esq[:, 1]
    ys = oy + s0 * esq[:, 0] + c0 * esq[:, 1]
    ax.set_xlim(xs.min(), xs.max())
    ax.set_ylim(ys.min(), ys.max())
    ax.set_aspect('equal')
    ex, co, es = resultado['exactitud'], resultado['completitud'], resultado['espurias']
    media_cm = f'{100 * ex["media_m"]:.1f} cm' if ex['media_m'] is not None else 'sin datos'
    ax.set_title(f'Mapa "{etiqueta}" ({res:.2f} m/celda)\nerror medio {media_cm}, '
                 f'completitud {100 * co["fraccion"]:.1f} %, {es["celdas"]} celdas espurias',
                 color=TINTA, fontsize=11, loc='left')
    ax.set_xlabel('x [m]', color=TINTA_2, fontsize=9)
    ax.set_ylabel('y [m]', color=TINTA_2, fontsize=9)
    for lado in ('top', 'right'):
        ax.spines[lado].set_visible(False)
    for lado in ('left', 'bottom'):
        ax.spines[lado].set_color(TINTA_2)
    ax.tick_params(colors=TINTA_2, labelsize=9)
    ax.legend(handles=leyenda, loc='upper center', bbox_to_anchor=(0.5, -0.08), ncol=len(leyenda),
              frameon=False, fontsize=9, labelcolor=TINTA)
    fig.tight_layout()
    fig.savefig(base + '.png', dpi=150, facecolor='white')

    print(json.dumps(resultado, indent=2, ensure_ascii=False))
    print(f'Guardado en {base}.json / .png')


if __name__ == '__main__':
    main()
