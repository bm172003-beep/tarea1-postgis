#!/usr/bin/env python3
"""
consultas.py — Parte C de la Tarea 1: corre las consultas sobre la base que dejó `cargar.py`.

    python3 consultas.py                 # todo, en orden, con la ruta 514 para Q5
    python3 consultas.py --ruta 505      # otra ruta (route_short_name) para Q5
    python3 consultas.py --solo q4 q6    # solo los archivos cuyo nombre empieza con q4 o q6
    python3 consultas.py --sin-mapas     # no exporta el GeoPackage

Para cada archivo de sql/consultas/ (ver MANIFEST):
    csv   → resultados/<archivo>.csv           (el resultado de la consulta)
    plan  → resultados/planes/<archivo>.txt    (EXPLAIN ANALYZE) y una línea en planes/resumen_tiempos.md
    ddl   → solo ejecuta (tablas auxiliares, vistas materializadas)
Al final exporta resultados/mapas.gpkg (una capa por mapa, SRID 5361) para abrir en QGIS, y los
CSV de índices (q9) quedan en resultados/q9_indices_uso.csv.

Reutiliza el acceso a la base de cargar.py (docker compose exec ... psql). Solo librería estándar.
"""
import argparse
import re
import sys
import time

import cargar
from cargar import AQUI, PG, PSQL, RESULTADOS, ZONAS, compose, salir

SQL = AQUI / "sql" / "consultas"
MAPAS_SQL = AQUI / "sql" / "mapas"
PLANES = RESULTADOS / "planes"

# (archivo, tipo). El orden importa: unas consultas leen tablas que dejan las anteriores.
MANIFEST = [
    ("00_preparacion.sql", "ddl"),
    ("q1_paraderos_por_comuna.sql", "csv"),
    ("q1_plan.sql", "plan"),
    ("q2_cobertura.sql", "csv"),
    ("q2_plan_con_indice.sql", "plan"),
    ("q2_plan_sin_indice.sql", "plan"),
    ("q3_dos_fuentes.sql", "csv"),
    ("q3b_sensibilidad.sql", "csv"),
    ("q4_plan_con_subdivide.sql", "plan"),
    ("q4_plan_sin_subdivide.sql", "plan"),
    ("q4_plan_completa_sin_subdivide.sql", "plan"),
    ("q4_plan_completa_con_subdivide.sql", "plan"),
    ("q4_km_por_comuna.sql", "csv"),
    ("q5_vecino_mas_cercano.sql", "csv"),
    ("q5b_resumen.sql", "csv"),
    ("q5_plan_con_indice.sql", "plan"),
    ("q5_plan_sin_indice.sql", "plan"),
    ("q6_grilla.sql", "ddl"),
    ("q6_top10.sql", "csv"),
    ("q6b_resumen.sql", "csv"),
    ("q7_00_buffer.sql", "ddl"),
    ("q7_vias_sin_servicio.sql", "csv"),
    ("q7b_top_calles.sql", "csv"),
    ("q9_indices_uso.sql", "csv"),
]

# (archivo SQL, nombre de la capa, tipo de geometría)
MAPAS = [
    ("mapa_q1.sql", "q1_densidad_paraderos", "MULTIPOLYGON"),
    ("mapa_q2.sql", "q2_cobertura_500m", "MULTIPOLYGON"),
    ("mapa_q5.sql", "q5_paraderos_ruta", "POINT"),
    ("mapa_q5_salud.sql", "q5_salud", "POINT"),
    ("mapa_q6.sql", "q6_grilla_hex", "POLYGON"),
]


def ejecutar(archivo, tipo, variables):
    args = list(PSQL) + (["--csv"] if tipo == "csv" else [])
    for k, v in variables.items():
        args += ["-v", f"{k}={v}"]
    args += ["-f", f"/sql/consultas/{archivo}"]
    t0 = time.perf_counter()
    salida = compose(*args, capturar=True).stdout
    return salida, time.perf_counter() - t0


def exportar_mapas():
    print("\n=== Mapas: resultados/mapas.gpkg")
    compose("exec", "-T", "db", "rm", "-f", "/resultados/mapas.gpkg")
    for k, (archivo, capa, geom) in enumerate(MAPAS):
        sql = (MAPAS_SQL / archivo).read_text(encoding="utf-8")
        sql = " ".join(re.sub(r"--[^\n]*", "", sql).split())
        args = ["exec", "-T", "db", "ogr2ogr", "-f", "GPKG", "/resultados/mapas.gpkg", PG,
                "-sql", sql, "-nln", capa, "-nlt", geom]
        if k > 0:
            args.insert(6, "-update")
        compose(*args, capturar=True)
        print(f"    capa {capa}")


def main():
    ap = argparse.ArgumentParser(description="Ejecuta las consultas de la Tarea 1.")
    ap.add_argument("--ruta", default="514", help="route_short_name para Q5 (por defecto 514)")
    ap.add_argument("--solo", nargs="+", metavar="PREFIJO")
    ap.add_argument("--sin-mapas", action="store_true")
    a = ap.parse_args()

    cargar.verificar_entorno()
    xmin, ymin, xmax, ymax = ZONAS["santiago-centro"]
    variables = {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax, "ruta": a.ruta}
    if cargar.psql("SELECT to_regclass('public.recorridos') IS NOT NULL", filas=True) != "t":
        salir("La base no está cargada: corran primero `python3 cargar.py`.")

    RESULTADOS.mkdir(exist_ok=True)
    PLANES.mkdir(exist_ok=True)
    tiempos = []
    for archivo, tipo in MANIFEST:
        if a.solo and not any(archivo.startswith(p) for p in a.solo):
            continue
        print(f"\n=== {archivo}  [{tipo}]", flush=True)
        salida, seg = ejecutar(archivo, tipo, variables)
        stem = archivo[:-4]
        if tipo == "csv":
            (RESULTADOS / f"{stem}.csv").write_text(salida + "\n", encoding="utf-8")
            lineas = salida.splitlines()
            print("\n".join("    " + l for l in lineas[:14]) + (f"\n    ... ({len(lineas) - 1} filas en total)" if len(lineas) > 14 else ""))
        elif tipo == "plan":
            (PLANES / f"{stem}.txt").write_text(salida + "\n", encoding="utf-8")
            m = re.search(r"Execution Time: ([\d.]+) ms", salida)
            p = re.search(r"Planning Time: ([\d.]+) ms", salida)
            ejec = float(m.group(1)) if m else float("nan")
            tiempos.append((archivo, ejec, float(p.group(1)) if p else float("nan")))
            print(f"    ejecución: {ejec / 1000:.2f} s  ·  plan guardado en resultados/planes/{stem}.txt")
        print(f"    ({seg:.1f} s)")

    if tiempos:
        previo = {}
        ruta_md = PLANES / "resumen_tiempos.md"
        if ruta_md.exists():       # con --solo se conservan los tiempos de las corridas anteriores
            for linea in ruta_md.read_text(encoding="utf-8").splitlines():
                m = re.match(r"\| `([^`]+)` \| ([\d.]+) \| ([\d.]+) \|", linea)
                if m:
                    previo[m.group(1)] = (float(m.group(2)) * 1000, float(m.group(3)))
        previo.update({f: (e, p) for f, e, p in tiempos})
        orden = [f for f, t in MANIFEST if t == "plan" and f in previo]
        filas = ["# Tiempos de ejecución de los planes (EXPLAIN ANALYZE)", "",
                 "| archivo | ejecución (s) | planificación (ms) |", "|---|---:|---:|"]
        filas += [f"| `{f}` | {previo[f][0] / 1000:.2f} | {previo[f][1]:.1f} |" for f in orden]
        ruta_md.write_text("\n".join(filas) + "\n", encoding="utf-8")
        print("\nresultados/planes/resumen_tiempos.md escrito")

    if not a.sin_mapas and not a.solo:
        exportar_mapas()
    print("\nListo. Resultados en resultados/ (CSV), resultados/planes/ (EXPLAIN) y resultados/mapas.gpkg")


if __name__ == "__main__":
    main()
