#!/usr/bin/env python3
"""Práctica 4: grafica el error de AMCL en el tiempo para varias corridas de evaluar_amcl.py.

Cada corrida se pasa como etiqueta=ruta_csv; una línea por corrida y el punto marca
cuándo convergió (error < 0,15 m y < 5° durante 2 s, igual que evaluar_amcl.py).

El eje y es lineal desde 0: una corrida perdida (más de 1 m de error) aplasta a las
demás, por eso conviene una figura por pregunta.

Uso:
  python3 graficar_p4.py p4_pose.png "Pose correcta=p4_pose_correcta.csv" \
      "Pose incorrecta=p4_pose_incorrecta.csv"
  python3 graficar_p4.py p4_ruido.png "Ruido 0,01 m=p4_pose_correcta.csv" "Ruido 0,15 m=p4_ruido_alto.csv"
"""
import csv
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

TINTA = '#0b0b0b'
TINTA_2 = '#52514e'
REJILLA = '#e4e3df'
SERIES = ['#2a78d6', '#eb6834', '#1baf7a', '#6250d6']

UMBRAL_POS = 0.15   # m
UMBRAL_YAW = 5.0    # grados
PERMANENCIA = 2.0   # s


def leer(ruta):
    with open(ruta, encoding='utf-8') as f:
        filas = list(csv.DictReader(f))
    return {k: [float(r[k]) for r in filas] for k in filas[0]}


def convergencia(t, e_pos, e_yaw):
    """Primera muestra desde la que el error queda bajo los umbrales durante PERMANENCIA s."""
    inicio = None
    for i, (ti, ep, ey) in enumerate(zip(t, e_pos, e_yaw)):
        if ep < UMBRAL_POS and ey < UMBRAL_YAW:
            if inicio is None:
                inicio = i
            if ti - t[inicio] >= PERMANENCIA:
                return inicio
        else:
            inicio = None
    return None


def estilo(ax):
    ax.grid(True, color=REJILLA, linewidth=0.8)
    for lado in ('top', 'right'):
        ax.spines[lado].set_visible(False)
    for lado in ('left', 'bottom'):
        ax.spines[lado].set_color(TINTA_2)
    ax.tick_params(colors=TINTA_2, labelsize=9)


def main():
    if len(sys.argv) < 3 or any('=' not in a for a in sys.argv[2:]):
        sys.exit(__doc__)
    salida = sys.argv[1]
    corridas = [a.split('=', 1) for a in sys.argv[2:]]
    if len(corridas) > len(SERIES):
        sys.exit(f'Máximo {len(SERIES)} corridas por gráfica.')

    fig, (ax_p, ax_y) = plt.subplots(2, 1, figsize=(10, 7.5), sharex=True)
    for (etiqueta, ruta), color in zip(corridas, SERIES):
        d = leer(ruta)
        ax_p.plot(d['t'], d['err_pos'], color=color, linewidth=2, label=etiqueta)
        ax_y.plot(d['t'], d['err_yaw_deg'], color=color, linewidth=2, label=etiqueta)
        i = convergencia(d['t'], d['err_pos'], d['err_yaw_deg'])
        if i is not None:
            ax_p.plot(d['t'][i], d['err_pos'][i], 'o', color=color, markersize=7)
            ax_y.plot(d['t'][i], d['err_yaw_deg'][i], 'o', color=color, markersize=7)

    ax_p.axhline(UMBRAL_POS, color=TINTA_2, linewidth=1.2, linestyle='--', label='Umbral de convergencia')
    ax_y.axhline(UMBRAL_YAW, color=TINTA_2, linewidth=1.2, linestyle='--')

    ax_p.set_title('Error de posición de AMCL (punto = convergencia)', color=TINTA, fontsize=11, loc='left')
    ax_p.set_ylabel('error de posición [m]', color=TINTA_2, fontsize=9)
    ax_y.set_title('Error de orientación de AMCL', color=TINTA, fontsize=11, loc='left')
    ax_y.set_ylabel('|error yaw| [°]', color=TINTA_2, fontsize=9)
    ax_y.set_xlabel('tiempo desde la pose inicial [s]', color=TINTA_2, fontsize=9)
    for ax in (ax_p, ax_y):
        ax.set_ylim(bottom=0)
        estilo(ax)

    # Una sola leyenda arriba para todas las corridas.
    manejadores, nombres = ax_p.get_legend_handles_labels()
    fig.legend(manejadores, nombres, loc='upper center', ncol=len(nombres), frameon=False,
               fontsize=10, labelcolor=TINTA)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(salida, dpi=150, facecolor='white')
    print('Guardado', salida)


if __name__ == '__main__':
    main()
