#!/usr/bin/env python3
"""
cargar.py — Tarea 1 (PostGIS de punta a punta, Santiago centro).

Deja la base completa a partir de los tres archivos fuente en `datos_fuente/`:

    datos_fuente/chile-AAMMDD.osm.pbf      extracto de Chile (Geofabrik)
    datos_fuente/GTFS_AAAAMMDD.zip         GTFS vigente (DTPM), sin descomprimir
    datos_fuente/comunas_cl.sql            DPA 2023 (Lab 03)

Uso, en una máquina limpia (solo Docker + Python 3.8+, sin librerías extra):

    docker compose up -d --wait --build    # opcional: el script también lo hace
    python3 cargar.py

Pasos:
    1. Levanta PostGIS (compose) y activa postgis + hstore.
    2. Carga comunas_cl (Lab 03) si no existe.
    3. OSM: preparar_datos.py (.pbf → GeoPackage 5361) → ogr2ogr a osm_puntos / osm_lineas /
       osm_poligonos → reparación de geometrías inválidas (cuenta y registra cuántas).
    4. sql/01_osm.sql: calles, edificios (con punto interior), paraderos_osm, amenidades,
       comunas_zona, comunas_sub; cada una con su índice GiST.
    5. GTFS: descomprime el ZIP, crea las tablas crudas leyendo las cabeceras reales y carga
       con COPY (nunca INSERT fila por fila).
    6. sql/02_gtfs.sql: paraderos_gtfs, estaciones_gtfs, recorridos (una LineString por shape).
    7. VACUUM ANALYZE, validaciones (SRID 5361, tipos) y resultados/etl_resumen.md con fuentes,
       reparaciones, conteos e índices (insumo directo del README).

Opciones:
    --saltar-osm     no repite el paso 3 (útil para iterar sobre el GTFS)
    --forzar         rehace el GeoPackage aunque ya exista
    --zona NOMBRE    zona de preparar_datos.py (por defecto santiago-centro)
    --bbox X0 Y0 X1 Y1 --nombre N   caja propia (lon/lat); anótenlo en el README
"""
import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):          # consola de Windows: evitar errores de codificación
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

AQUI = Path(__file__).resolve().parent
FUENTE = AQUI / "datos_fuente"
DATOS = AQUI / "datos"
RESULTADOS = AQUI / "resultados"
sys.path.insert(0, str(AQUI))
from preparar_datos import ZONAS  # noqa: E402  (el script del Lab 05, sin cambios)

SRID = 5361
PG = "PG:host=localhost dbname=postgres user=postgres password=pmd2026"   # visto DESDE el contenedor
CAPAS_OSM = {"points": "osm_puntos", "lines": "osm_lineas", "multipolygons": "osm_poligonos"}

# (archivo, tabla cruda, obligatorio)
GTFS_ARCHIVOS = [
    ("stops", "raw_stops", True),
    ("routes", "raw_routes", True),
    ("trips", "raw_trips", True),
    ("shapes", "raw_shapes", True),
    ("stop_times", "raw_stop_times", True),
    ("frequencies", "raw_frequencies", False),
]
COLUMNAS_REQUERIDAS = {
    "stops": {"stop_id", "stop_name", "stop_lat", "stop_lon", "location_type"},
    "routes": {"route_id", "route_short_name", "route_long_name", "route_type"},
    "trips": {"route_id", "trip_id", "shape_id", "direction_id"},
    "shapes": {"shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"},
    "stop_times": {"trip_id", "stop_id"},
}
TABLAS_RESUMEN = [
    "osm_puntos", "osm_lineas", "osm_poligonos",
    "calles", "edificios", "paraderos_osm", "amenidades",
    "comunas_cl", "comunas_zona", "comunas_sub",
    "raw_stops", "raw_routes", "raw_trips", "raw_shapes", "raw_stop_times", "raw_frequencies",
    "gtfs_stop_modos", "paraderos_gtfs", "estaciones_gtfs", "recorridos",
]

ctx = {}   # datos que los pasos dejan para el resumen final


# ------------------------------------------------------------------ utilidades
def salir(mensaje):
    print(f"\n[ERROR] {mensaje}", file=sys.stderr)
    sys.exit(1)


def paso(titulo):
    print(f"\n=== {titulo}", flush=True)
    return time.perf_counter()


def fin(t0):
    print(f"    listo en {time.perf_counter() - t0:.1f} s", flush=True)


def compose(*args, capturar=False, entrada=None, check=True):
    """`docker compose <args>` en la carpeta del repo. Con capturar=True devuelve stdout/stderr."""
    cmd = ["docker", "compose", *args]
    r = subprocess.run(cmd, cwd=AQUI, input=entrada, text=True, encoding="utf-8", errors="replace",
                       capture_output=capturar)
    if check and r.returncode != 0:
        detalle = (r.stderr or "").strip()[-1500:] if capturar else ""
        salir(f"falló: {' '.join(cmd[:6])} ...\n{detalle}")
    return r


PSQL = ["exec", "-T", "db", "psql", "-q", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", "postgres"]


def psql(sql=None, archivo=None, variables=None, filas=False):
    """Ejecuta SQL con el psql del contenedor. `filas=True` devuelve el resultado como texto (-At)."""
    args = list(PSQL)
    for k, v in (variables or {}).items():
        args += ["-v", f"{k}={v}"]
    if filas:
        args.append("-At")
    if archivo:
        args += ["-f", archivo]
        entrada = None
    else:
        args += ["-f", "-"]
        entrada = sql
    return compose(*args, capturar=True, entrada=entrada).stdout.strip()


# ------------------------------------------------------------------ argumentos y fuentes
def argumentos():
    ap = argparse.ArgumentParser(description="Carga completa de la Tarea 1.")
    ap.add_argument("--zona", default="santiago-centro", choices=sorted(ZONAS))
    ap.add_argument("--bbox", nargs=4, type=float, metavar=("XMIN", "YMIN", "XMAX", "YMAX"))
    ap.add_argument("--nombre")
    ap.add_argument("--forzar", action="store_true")
    ap.add_argument("--saltar-osm", action="store_true")
    a = ap.parse_args()
    if a.bbox:
        if not a.nombre:
            ap.error("--bbox necesita --nombre")
        return a.nombre, tuple(a.bbox), a
    return a.zona, ZONAS[a.zona], a


def verificar_entorno():
    if not shutil.which("docker"):
        salir("No encuentro `docker`. Instalen Docker Desktop (o docker-ce + plugin compose) y reintenten.")
    r = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True)
    if r.returncode != 0:
        salir("`docker compose` no responde: ¿Docker Desktop abierto? ¿falta el plugin compose?")


def verificar_fuentes():
    """Comprueba los tres archivos fuente y explica exactamente qué falta."""
    pbfs = sorted(FUENTE.glob("*.osm.pbf"))
    zips = sorted(p for p in FUENTE.glob("*.zip") if "gtfs" in p.name.lower())
    comunas = FUENTE / "comunas_cl.sql"
    faltan = []
    if not pbfs:
        faltan.append("un .osm.pbf (chile-latest.osm.pbf de Geofabrik, con su nombre terminado en .osm.pbf)")
    if not zips:
        faltan.append("el ZIP del GTFS vigente de la DTPM (el nombre debe contener «GTFS»), sin descomprimir")
    if not comunas.exists():
        faltan.append("comunas_cl.sql (el de 03/datos/ del Lab 03)")
    if faltan:
        salir(f"Faltan archivos fuente en {FUENTE}:\n   - " + "\n   - ".join(faltan) + "\n   Ver README.md.")
    if len(pbfs) > 1:     # preparar_datos.py usaría el primero por orden alfabético: mejor no dejar ambigüedad
        salir("Hay más de un .osm.pbf en datos_fuente/ (" + ", ".join(p.name for p in pbfs) + ").\n"
              "   Dejen solo uno: de él sale el GeoPackage y es el que se documenta en el README.")
    if len(zips) > 1:
        print(f"[aviso] hay {len(zips)} ZIP de GTFS en datos_fuente/; se usa el último: {zips[-1].name}")
    return {"pbf": pbfs[-1], "gtfs": zips[-1], "comunas": comunas}


# ------------------------------------------------------------------ 1. infraestructura
def levantar_infra():
    t0 = paso("1/7  Infraestructura: docker compose up -d --wait --build")
    compose("up", "-d", "--wait", "--build")
    psql("CREATE EXTENSION IF NOT EXISTS postgis; CREATE EXTENSION IF NOT EXISTS hstore;")
    ctx["versiones"] = psql("SELECT split_part(version(), ',', 1) || ' · PostGIS ' || postgis_version()", filas=True)
    print("    " + ctx["versiones"])
    fin(t0)


# ------------------------------------------------------------------ 2. comunas (DPA)
def cargar_comunas():
    t0 = paso("2/7  Comunas (DPA 2023, Lab 03)")
    if psql("SELECT to_regclass('public.comunas_cl') IS NOT NULL", filas=True) == "t":
        print("    comunas_cl ya existe: se conserva")
    else:
        psql(archivo="/datos_fuente/comunas_cl.sql")
    psql("""
        DO $$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE tablename = 'comunas_cl' AND indexdef ILIKE '%gist%') THEN
            CREATE INDEX idx_comunas_cl_geom ON comunas_cl USING GIST (geom);
          END IF;
        END $$;
        ANALYZE comunas_cl;""")
    n, srid = psql("SELECT count(*), max(ST_SRID(geom)) FROM comunas_cl", filas=True).split("|")
    print(f"    comunas_cl: {n} filas, SRID {srid}")
    if srid != str(SRID):
        salir(f"comunas_cl viene en SRID {srid}, se esperaba {SRID}.")
    fin(t0)


# ------------------------------------------------------------------ 3. OSM
def reparar_geometrias():
    """ST_MakeValid sobre los polígonos inválidos de OSM, contando antes y después."""
    inval = psql("SELECT count(*), coalesce(round(sum(ST_Area(geom))), 0) FROM osm_poligonos WHERE NOT ST_IsValid(geom)",
                 filas=True).split("|")
    total = int(psql("SELECT count(*) FROM osm_poligonos", filas=True))
    razones = psql("""SELECT razon || ' | ' || n FROM (
                        SELECT regexp_replace(ST_IsValidReason(geom), '\\[.*\\]', '') AS razon, count(*) AS n
                        FROM osm_poligonos WHERE NOT ST_IsValid(geom) GROUP BY 1) t
                      ORDER BY n DESC LIMIT 5""", filas=True)
    psql("""UPDATE osm_poligonos
            SET geom = ST_Multi(ST_CollectionExtract(ST_MakeValid(geom), 3))
            WHERE NOT ST_IsValid(geom)""")
    despues = psql("""SELECT count(*) FILTER (WHERE NOT ST_IsValid(geom)),
                             count(*) FILTER (WHERE ST_IsEmpty(geom)) FROM osm_poligonos""", filas=True).split("|")
    ctx["reparacion"] = {"total": total, "invalidos": int(inval[0]), "area_m2": inval[1], "razones": razones,
                         "quedan_invalidos": int(despues[0]), "vacios": int(despues[1])}
    print(f"    polígonos: {total:,} · inválidos reparados: {inval[0]} · "
          f"quedan {despues[0]} inválidos y {despues[1]} vacíos (se excluyen al derivar)")


def cargar_osm(nombre, zona_args, forzar):
    t0 = paso("3/7  OSM: .pbf → GeoPackage → PostGIS → reparación")
    cmd = [sys.executable, str(AQUI / "preparar_datos.py"), *zona_args]
    if forzar:
        cmd.append("--forzar")
    r = subprocess.run(cmd, cwd=AQUI, env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    if r.returncode != 0:
        salir("preparar_datos.py falló (ver mensaje arriba).")
    gpkg = DATOS / f"osm_{nombre}.gpkg"
    ctx["gpkg"] = f"{gpkg.name} ({gpkg.stat().st_size / 1e6:.0f} MB)"
    for capa, tabla in CAPAS_OSM.items():
        t1 = time.perf_counter()
        compose("exec", "-T", "db", "ogr2ogr", "-f", "PostgreSQL", PG, f"/datos/{gpkg.name}", capa,
                "-nln", tabla, "-overwrite",
                "-lco", "GEOMETRY_NAME=geom", "-lco", "SPATIAL_INDEX=GIST",
                "-lco", "COLUMN_TYPES=other_tags=hstore", "-lco", "FID=id", capturar=True)
        print(f"    {capa:>14} → {tabla:<14} {time.perf_counter() - t1:6.1f} s")
    reparar_geometrias()
    fin(t0)


def derivar_osm(vars_caja):
    t0 = paso("4/7  Capas derivadas de OSM (sql/01_osm.sql)")
    psql(archivo="/sql/01_osm.sql", variables=vars_caja)
    fin(t0)


# ------------------------------------------------------------------ 5. GTFS
def ddl_raw(ruta_csv, tabla, ruta_contenedor):
    """CREATE TABLE (todo texto, columnas = cabecera real del archivo) + COPY. Devuelve (sql, columnas)."""
    with open(ruta_csv, encoding="utf-8-sig", newline="") as f:
        columnas = [re.sub(r"\W", "_", c.strip().lower()) for c in next(csv.reader(f))]
    defs = ",\n  ".join(f'"{c}" text' for c in columnas)
    sql = (f"DROP TABLE IF EXISTS {tabla} CASCADE;\n"
           f"CREATE TABLE {tabla} (\n  {defs}\n);\n"
           f"COPY {tabla} FROM '{ruta_contenedor}' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8');\n")
    return sql, columnas


def cargar_gtfs(zip_gtfs):
    t0 = paso(f"5/7  GTFS: {zip_gtfs.name} → tablas crudas (COPY)")
    destino = DATOS / "gtfs"
    shutil.rmtree(destino, ignore_errors=True)
    destino.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_gtfs) as z:
        z.extractall(destino)
    stops = next(destino.rglob("stops.txt"), None)
    if stops is None:
        salir(f"{zip_gtfs.name} no contiene stops.txt: ¿es un ZIP de GTFS?")
    carpeta = stops.parent
    ctx["gtfs_zip"] = f"{zip_gtfs.name} ({zip_gtfs.stat().st_size / 1e6:.1f} MB)"
    ctx["gtfs_filas"] = {}
    feed = carpeta / "feed_info.txt"
    if feed.exists():
        with open(feed, encoding="utf-8-sig", newline="") as f:
            ctx["feed_info"] = next(csv.DictReader(f), {})
    for archivo, tabla, obligatorio in GTFS_ARCHIVOS:
        ruta = carpeta / f"{archivo}.txt"
        if not ruta.exists():
            if obligatorio:
                salir(f"Falta {archivo}.txt en el GTFS.")
            print(f"    {archivo}.txt no está en este feed: se omite")
            continue
        interno = "/datos/gtfs/" + ruta.relative_to(destino).as_posix()
        sql, columnas = ddl_raw(ruta, tabla, interno)
        faltan = COLUMNAS_REQUERIDAS.get(archivo, set()) - set(columnas)
        if faltan:
            salir(f"{archivo}.txt no trae las columnas {sorted(faltan)}; cabecera real: {columnas}")
        t1 = time.perf_counter()
        psql(sql)
        n = int(psql(f"SELECT count(*) FROM {tabla}", filas=True))
        ctx["gtfs_filas"][archivo] = n
        print(f"    {archivo + '.txt':<16} → {tabla:<16} {n:>10,} filas  {time.perf_counter() - t1:5.1f} s")
    fin(t0)


def derivar_gtfs(vars_caja):
    t0 = paso("6/7  Geometrías del GTFS (sql/02_gtfs.sql)")
    psql(archivo="/sql/02_gtfs.sql", variables=vars_caja)
    ctx["shapes_huerfanos"] = int(psql("""
        SELECT count(*) FROM (SELECT DISTINCT shape_id FROM raw_shapes) s
        WHERE NOT EXISTS (SELECT 1 FROM raw_trips t WHERE t.shape_id = s.shape_id)""", filas=True))
    ctx["shapes_total"] = int(psql("SELECT count(DISTINCT shape_id) FROM raw_shapes", filas=True))
    fin(t0)


# ------------------------------------------------------------------ 7. cierre
def validar():
    problemas = []
    for fila in psql("""SELECT f_table_name, f_geometry_column, srid, type FROM geometry_columns
                        WHERE f_table_schema = 'public' ORDER BY 1, 2""", filas=True).splitlines():
        tabla, col, srid, tipo = fila.split("|")
        if srid != str(SRID):
            problemas.append(f"{tabla}.{col} tiene SRID {srid} (se esperaba {SRID})")
    tipos, invalidas, n = psql("""SELECT count(*) FILTER (WHERE GeometryType(geom) <> 'LINESTRING'),
                                         count(*) FILTER (WHERE NOT ST_IsValid(geom)), count(*) FROM recorridos""",
                               filas=True).split("|")
    if tipos != "0":
        problemas.append(f"{tipos} recorridos no son LineString")
    if invalidas != "0":
        problemas.append(f"{invalidas} recorridos inválidos")
    if n == "0":
        problemas.append("recorridos está vacía")
    inval_edif = psql("SELECT count(*) FROM edificios WHERE NOT ST_IsValid(geom)", filas=True)
    if inval_edif != "0":
        problemas.append(f"{inval_edif} edificios siguen inválidos")
    for tabla in ("edificios", "paraderos_gtfs", "paraderos_osm", "recorridos"):
        if psql(f"SELECT count(*) FROM {tabla}", filas=True) == "0":
            problemas.append(f"{tabla} está vacía")
    return problemas


def escribir_resumen(nombre, bbox, fuentes, segundos):
    conteos, tamanos = {}, {}
    for t in TABLAS_RESUMEN:
        if psql(f"SELECT to_regclass('public.{t}') IS NOT NULL", filas=True) == "t":
            conteos[t] = int(psql(f"SELECT count(*) FROM {t}", filas=True))
            tamanos[t] = psql(f"SELECT pg_size_pretty(pg_total_relation_size('{t}'))", filas=True)
    indices = psql("""SELECT tablename || '|' || indexname || '|' || indexdef FROM pg_indexes
                      WHERE schemaname = 'public' AND tablename = ANY(string_to_array(:'tablas', ','))
                      ORDER BY 1""", variables={"tablas": ",".join(conteos)}, filas=True).splitlines()
    geoms = psql("""SELECT f_table_name || '.' || f_geometry_column || '|' || srid || '|' || type
                    FROM geometry_columns WHERE f_table_schema = 'public' ORDER BY 1""", filas=True).splitlines()
    feed = ctx.get("feed_info", {})
    rep = ctx.get("reparacion")
    L = [f"# Resumen de la carga (generado por cargar.py · {datetime.now():%Y-%m-%d %H:%M})", ""]
    L += ["## Fuentes y versiones", "",
          f"- OSM: `{fuentes['pbf'].name}` ({fuentes['pbf'].stat().st_size / 1e6:.0f} MB) — Geofabrik, ODbL. "
          f"Zona `{nombre}`: lon {bbox[0]}…{bbox[2]} · lat {bbox[1]}…{bbox[3]} → {ctx.get('gpkg', 'GeoPackage previo')}",
          f"- GTFS: `{ctx.get('gtfs_zip')}` — feed_version `{feed.get('feed_version', '?')}`, "
          f"vigencia {feed.get('feed_start_date', '?')} a {feed.get('feed_end_date', '?')}",
          f"- DPA: `{fuentes['comunas'].name}` (DPA 2023, Lab 03)",
          f"- Motor: {ctx.get('versiones')}", f"- Duración de la carga: {segundos / 60:.1f} min", ""]
    L += ["## Reparación de geometrías OSM (ST_MakeValid)", ""]
    if rep:
        L += [f"- Polígonos totales: {rep['total']:,}",
              f"- Inválidos antes de reparar: **{rep['invalidos']:,}** (área declarada: {rep['area_m2']} m²)",
              f"- Tras `ST_Multi(ST_CollectionExtract(ST_MakeValid(geom), 3))`: {rep['quedan_invalidos']} inválidos, "
              f"{rep['vacios']} vacíos (excluidos al derivar `edificios` y `amenidades`)",
              "- Razones más frecuentes (ST_IsValidReason, sin coordenadas):", "", "```", rep["razones"] or "(ninguna)", "```", ""]
    else:
        L += ["- No se ejecutó en esta corrida (`--saltar-osm`): usar el resumen de la corrida completa.", ""]
    L += ["## GTFS", ""]
    for archivo, n in ctx.get("gtfs_filas", {}).items():
        L.append(f"- `{archivo}.txt`: {n:,} filas (cargado con COPY)")
    if "shapes_total" in ctx:
        L += [f"- Shapes: {ctx['shapes_total']:,} en shapes.txt, de los cuales {ctx['shapes_huerfanos']:,} "
              f"no tienen ningún viaje en trips.txt (descartados)."]
    L += ["", "## Tablas (filas · tamaño total con índices)", "", "| tabla | filas | tamaño |", "|---|---:|---:|"]
    L += [f"| `{t}` | {conteos[t]:,} | {tamanos[t]} |" for t in conteos]
    L += ["", "## Geometrías (tipo y SRID declarados)", "", "| columna | SRID | tipo |", "|---|---:|---|"]
    L += [f"| `{g.split('|')[0]}` | {g.split('|')[1]} | {g.split('|')[2]} |" for g in geoms]
    L += ["", "## Índices", "", "| tabla | índice | definición |", "|---|---|---|"]
    for fila in indices:
        t, i, d = fila.split("|", 2)
        L.append(f"| `{t}` | `{i}` | `{d.replace('CREATE ', '').replace('INDEX ', '').replace('UNIQUE ', '')}` |")
    RESULTADOS.mkdir(exist_ok=True)
    (RESULTADOS / "etl_resumen.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print("    resultados/etl_resumen.md escrito")


def main():
    nombre, bbox, a = argumentos()
    zona_args = ["--bbox", *map(str, bbox), "--nombre", nombre] if a.bbox else ["--zona", nombre]
    vars_caja = dict(zip(("xmin", "ymin", "xmax", "ymax"), map(str, bbox)))
    inicio = time.perf_counter()
    print(f"Tarea 1 — carga de la zona «{nombre}» (lon {bbox[0]}…{bbox[2]} · lat {bbox[1]}…{bbox[3]})")
    verificar_entorno()
    fuentes = verificar_fuentes()
    DATOS.mkdir(exist_ok=True)

    levantar_infra()
    cargar_comunas()
    if a.saltar_osm:
        print("\n(3/7) OSM omitido por --saltar-osm: se usan las tablas osm_* que ya estén en la base")
    else:
        cargar_osm(nombre, zona_args, a.forzar)
    derivar_osm(vars_caja)
    cargar_gtfs(fuentes["gtfs"])
    derivar_gtfs(vars_caja)

    t0 = paso("7/7  VACUUM ANALYZE, validación y resumen")
    psql("VACUUM ANALYZE")
    problemas = validar()
    escribir_resumen(nombre, bbox, fuentes, time.perf_counter() - inicio)
    fin(t0)
    if problemas:
        print("\n[VALIDACIÓN CON PROBLEMAS]\n  - " + "\n  - ".join(problemas))
        sys.exit(2)
    print(f"\nVALIDACIÓN OK — carga completa en {(time.perf_counter() - inicio) / 60:.1f} min. "
          "Conteos e índices en resultados/etl_resumen.md")
    print("Consola SQL:  docker compose exec db psql -U postgres")


if __name__ == "__main__":
    main()
