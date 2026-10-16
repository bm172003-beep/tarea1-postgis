#!/usr/bin/env python3
"""
mapas.py — dibuja los mapas del informe a partir de resultados/mapas.gpkg (lo deja consultas.py).

    python3 mapas.py          # escribe resultados/mapas/*.png

Necesita matplotlib (pip install matplotlib). Lee el GeoPackage con sqlite3 y decodifica la geometría
a mano (cabecera GeoPackage + WKB), así que no hace falta GDAL/geopandas.
Todos los mapas llevan título, escala de color, escala gráfica y la fuente con su fecha.
"""
import csv
import sqlite3
import struct
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.patches import PathPatch
from matplotlib.path import Path as MPath

AQUI = Path(__file__).resolve().parent
RES = AQUI / "resultados"
SALIDA = RES / "mapas"
FUENTE_OSM = "OpenStreetMap (Geofabrik, extracto del 13-10-2026)"
FUENTE_GTFS = "GTFS Red Movilidad, feed V168.20261003 (vigente desde el 03-10-2026)"
FUENTE_DPA = "comunas: DPA 2023"


# ------------------------------------------------------------------ lectura del GeoPackage
def _wkb(b, off=0):
    e = "<" if b[off] == 1 else ">"
    tipo = struct.unpack_from(e + "I", b, off + 1)[0] % 1000
    off += 5
    if tipo == 1:
        x, y = struct.unpack_from(e + "dd", b, off)
        return ("Point", (x, y)), off + 16
    if tipo == 3:
        n, = struct.unpack_from(e + "I", b, off)
        off += 4
        anillos = []
        for _ in range(n):
            m, = struct.unpack_from(e + "I", b, off)
            off += 4
            anillos.append([struct.unpack_from(e + "dd", b, off + 16 * k) for k in range(m)])
            off += 16 * m
        return ("Polygon", anillos), off
    if tipo == 6:
        n, = struct.unpack_from(e + "I", b, off)
        off += 4
        polis = []
        for _ in range(n):
            (_, anillos), off = _wkb(b, off)
            polis.append(anillos)
        return ("MultiPolygon", polis), off
    raise ValueError(f"tipo WKB no soportado: {tipo}")


def capa(gpkg, nombre):
    """Devuelve una lista de dicts con los atributos y 'geom' = (tipo, coordenadas)."""
    con = sqlite3.connect(gpkg)
    cols = [r[1] for r in con.execute(f'pragma table_info("{nombre}")') if r[1] not in ("fid", "geom")]
    filas = []
    for fila in con.execute(f'select geom, {", ".join(cols)} from "{nombre}"'):
        blob = fila[0]
        env = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(blob[3] >> 1) & 7]
        g, _ = _wkb(blob, 8 + env)
        d = dict(zip(cols, fila[1:]))
        d["geom"] = g
        filas.append(d)
    con.close()
    return filas


def csv_filas(nombre):
    with open(RES / nombre, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ------------------------------------------------------------------ dibujo
def poligonos(g):
    return [g[1]] if g[0] == "Polygon" else g[1]


def ruta_mpl(anillos):
    v, c = [], []
    for a in anillos:
        v += list(a)
        c += [MPath.MOVETO] + [MPath.LINETO] * (len(a) - 2) + [MPath.CLOSEPOLY]
    return MPath(v, c)


def pintar(ax, g, **kw):
    for p in poligonos(g):
        ax.add_patch(PathPatch(ruta_mpl(p), **kw))


def contorno_comunas(ax, comunas, lw=0.6, color="#555555"):
    for c in comunas:
        pintar(ax, c["geom"], facecolor="none", edgecolor=color, lw=lw, zorder=3)


def centro(g):
    p = max(poligonos(g), key=lambda a: len(a[0]))
    xs = [x for x, _ in p[0]]
    ys = [y for _, y in p[0]]
    return (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2


def limites(comunas):
    xs, ys = [], []
    for c in comunas:
        for p in poligonos(c["geom"]):
            xs += [x for x, _ in p[0]]
            ys += [y for _, y in p[0]]
    return min(xs), max(xs), min(ys), max(ys)


def escala_grafica(ax, km=5):
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    x, y = x0 + 0.04 * (x1 - x0), y0 + 0.04 * (y1 - y0)
    ax.plot([x, x + km * 1000], [y, y], color="black", lw=3, zorder=10, solid_capstyle="butt")
    ax.text(x + km * 500, y + 0.012 * (y1 - y0), f"{km} km", ha="center", va="bottom", fontsize=8, zorder=10)


def preparar_eje(ax, lim):
    ax.set_xlim(lim[0], lim[1])
    ax.set_ylim(lim[2], lim[3])
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)


# ------------------------------------------------------------------ mapa Q6 (principal)
def mapa_q6(gpkg, comunas):
    celdas = capa(gpkg, "q6_grilla_hex")
    rank = {(int(r["i"]), int(r["j"])): k + 1 for k, r in enumerate(csv_filas("q6_top10.csv"))}
    lim = limites(comunas)
    fig, axs = plt.subplots(1, 2, figsize=(15, 7.0))
    paneles = [
        ("n_edificios", "Edificios por celda", "YlOrRd", "Edificios (OSM)", FUENTE_OSM),
        ("n_rutas", "Recorridos distintos que cruzan la celda", "Blues", "Recorridos distintos (GTFS)", FUENTE_GTFS),
    ]
    for ax, (campo, titulo, cmap, etiqueta, fuente) in zip(axs, paneles):
        vmax = max(c[campo] for c in celdas)
        norm = Normalize(vmin=0, vmax=vmax)
        cm = plt.get_cmap(cmap)
        for c in celdas:
            cero = c[campo] == 0
            pintar(ax, c["geom"], facecolor="#e6e6e6" if cero else cm(norm(c[campo])),
                   edgecolor="white", lw=0.3, zorder=1)
        contorno_comunas(ax, comunas)
        for c in celdas:
            k = rank.get((c["i"], c["j"]))
            if k:
                pintar(ax, c["geom"], facecolor="none", edgecolor="black", lw=2.2, zorder=6)
                if campo == "n_edificios":
                    x, y = centro(c["geom"])
                    ax.text(x, y, str(k), ha="center", va="center", fontsize=9, fontweight="bold", zorder=7,
                            bbox=dict(boxstyle="circle,pad=0.15", fc="white", ec="black", lw=0.8))
        preparar_eje(ax, lim)
        escala_grafica(ax)
        ax.set_title(titulo, fontsize=12)
        cb = fig.colorbar(ScalarMappable(norm=norm, cmap=cm), ax=ax, shrink=0.7, pad=0.01)
        cb.set_label(etiqueta + ("  (gris = 0)" if campo == "n_rutas" else ""))
        ax.text(0.5, -0.02, "Fuente: " + fuente, transform=ax.transAxes, ha="center", va="top", fontsize=8, color="#444")
    fig.suptitle("Santiago centro: edificios y recorridos de transporte público por celda hexagonal (lado 500 m)",
                 fontsize=14, fontweight="bold", y=0.975)
    fig.text(0.5, 0.035, "Contorno negro numerado: las 10 celdas completas con más edificios por (recorridos + 1).  "
             "Gris claro: celdas sin edificios / sin recorridos.  Líneas grises: límites comunales (DPA 2023).",
             ha="center", fontsize=9)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.9, bottom=0.11, wspace=0.04)
    fig.savefig(SALIDA / "mapa_q6_grilla.png", dpi=170)
    plt.close(fig)


# ------------------------------------------------------------------ mapa Q1
def mapa_q1(gpkg, comunas):
    filas = {r["comuna"]: r for r in csv_filas("q1_paraderos_por_comuna.csv")}
    dens = {}
    for c in comunas:
        r = filas[c["comuna"]]
        frac = float(r["area_en_caja_km2"]) / float(r["area_km2"])
        c["frac"], c["dens"] = frac, float(r["paraderos_por_km2_en_caja"])
    validas = [c for c in comunas if c["frac"] >= 0.5]
    norm = Normalize(vmin=min(c["dens"] for c in validas), vmax=max(c["dens"] for c in validas))
    cm = plt.get_cmap("viridis_r")
    fig, ax = plt.subplots(figsize=(9.5, 8.6))
    for c in comunas:
        if c["frac"] >= 0.5:
            pintar(ax, c["geom"], facecolor=cm(norm(c["dens"])), edgecolor="white", lw=0.8)
        else:
            pintar(ax, c["geom"], facecolor="#eeeeee", edgecolor="#999999", lw=0.8, hatch="////")
    for c in comunas:
        x, y = centro(c["geom"])
        ax.text(x, y, c["comuna"], ha="center", va="center", fontsize=6.5, zorder=5,
                color="white" if c["frac"] >= 0.5 and norm(c["dens"]) < 0.55 else "black")
    preparar_eje(ax, limites(comunas))
    escala_grafica(ax)
    cb = fig.colorbar(ScalarMappable(norm=norm, cmap=cm), ax=ax, shrink=0.7, pad=0.01)
    cb.set_label("Paraderos GTFS de bus por km² (área de la comuna dentro de la zona)")
    ax.set_title("Densidad de paraderos de bus por comuna — Santiago centro", fontsize=13, fontweight="bold")
    fig.text(0.5, 0.045, "Trama gris: comuna con menos del 50 % de su área dentro de la zona (densidad no comparable).\n"
             "Fuente: " + FUENTE_GTFS + "; " + FUENTE_DPA + ".", ha="center", fontsize=8.5)
    fig.subplots_adjust(left=0.01, right=0.97, top=0.94, bottom=0.09)
    fig.savefig(SALIDA / "mapa_q1_densidad_paraderos.png", dpi=170)
    plt.close(fig)


# ------------------------------------------------------------------ mapa Q5
def mapa_q5(gpkg, comunas):
    paradas = capa(gpkg, "q5_paraderos_ruta")
    salud = capa(gpkg, "q5_salud")
    xs = [p["geom"][1][0] for p in paradas]
    ys = [p["geom"][1][1] for p in paradas]
    m = 1500
    lim = (min(xs) - m, max(xs) + m, min(ys) - m, max(ys) + m)
    fig, ax = plt.subplots(figsize=(11, 7.4))
    contorno_comunas(ax, comunas, lw=0.7, color="#888888")
    for c in comunas:
        x, y = centro(c["geom"])
        if lim[0] < x < lim[1] and lim[2] < y < lim[3]:
            ax.text(x, y, c["comuna"], fontsize=7, color="#777777", ha="center", zorder=2, style="italic")
    sx = [s["geom"][1][0] for s in salud]
    sy = [s["geom"][1][1] for s in salud]
    ax.scatter(sx, sy, marker="^", s=14, c="#2a9d8f", alpha=0.65, zorder=4, label="Farmacia o centro de salud (OSM)")
    dist = [p["dist_m"] for p in paradas]
    norm = Normalize(vmin=0, vmax=max(dist))
    sc = ax.scatter(xs, ys, c=dist, cmap="plasma_r", norm=norm, s=34, edgecolor="black", lw=0.4, zorder=6,
                    label="Paradero de la ruta 514 (GTFS)")
    preparar_eje(ax, lim)
    escala_grafica(ax, km=2)
    cb = fig.colorbar(sc, ax=ax, shrink=0.7, pad=0.01)
    cb.set_label("Distancia a la farmacia / centro de salud más cercano (m)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=2, fontsize=8.5, frameon=False)
    ax.set_title("Ruta 514 (Enea – San Luis de Macul)\nDistancia de cada paradero a la farmacia o centro de salud más cercano",
                 fontsize=12, fontweight="bold")
    fig.text(0.5, 0.02, "Fuentes: " + FUENTE_GTFS + ";\n" + FUENTE_OSM + ". Distancia en línea recta (SRID 5361).",
             ha="center", fontsize=8.5)
    fig.subplots_adjust(left=0.01, right=0.97, top=0.9, bottom=0.12)
    fig.savefig(SALIDA / "mapa_q5_ruta514_salud.png", dpi=170)
    plt.close(fig)


def main():
    gpkg = RES / "mapas.gpkg"
    if not gpkg.exists():
        raise SystemExit("Falta resultados/mapas.gpkg: corran antes `python3 consultas.py`.")
    SALIDA.mkdir(parents=True, exist_ok=True)
    comunas = capa(gpkg, "q1_densidad_paraderos")
    for f in (mapa_q6, mapa_q1, mapa_q5):
        f(gpkg, comunas)
        print("ok:", f.__name__)
    print("PNG en", SALIDA)


if __name__ == "__main__":
    main()
