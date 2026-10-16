# Tarea 1 — PostGIS de punta a punta: Santiago centro

Procesamiento Masivo de Datos · USM 2026-2 · Integrantes: Benjamín Medina, Javier Fernández

Pipeline geoespacial que cruza **OpenStreetMap** (ciudad construida) con el **GTFS** de la red de transporte público de Santiago (red declarada por el operador), sobre las comunas oficiales (DPA 2023). Todo en **SRID 5361** (SIRGAS-Chile / UTM 19S). Zona: lon −70,75…−70,52 · lat −33,52…−33,36.

## 1. Reproducir desde cero

Requisitos: Docker (con `docker compose`) y Python 3.8+ (en Windows el comando suele ser `python`; en Linux/Mac, `python3`). No hay que instalar nada más.

**Paso 1. Dejar los tres archivos fuente en `datos_fuente/`** (no se versionan; ver `.gitignore`):

| Archivo | De dónde | Nombre esperado |
|---|---|---|
| Extracto de OSM | <https://download.geofabrik.de/south-america/chile-latest.osm.pbf> | un solo `*.osm.pbf` (el nombre debe terminar en `.osm.pbf`) |
| GTFS vigente | <https://www.dtpm.cl/index.php/noticias/gtfs-vigente> | un `.zip` con «GTFS» en el nombre, **sin descomprimir** |
| Comunas (DPA 2023) | `03/datos/comunas_cl.sql` del Lab 03 (se extrae del `03.zip` solo ese archivo) | `comunas_cl.sql` |

**Paso 2. Levantar y cargar:**

```bash
docker compose up -d --wait --build
python3 cargar.py
```

`cargar.py` hace todo lo demás (recorte del `.pbf` con `preparar_datos.py` del Lab 05, carga, reparaciones, GTFS con `COPY`, índices, `VACUUM ANALYZE`, validaciones) y escribe `resultados/etl_resumen.md` con fuentes, reparaciones, conteos e índices. Es re-ejecutable. Termina con `VALIDACIÓN OK` o lista qué falló. Consola SQL: `docker compose exec db psql -U postgres`. Para apagar y limpiar: `docker compose down -v`.

Tiempos en nuestra máquina (Windows 11 + Docker Desktop): carga completa en 1,2 min con el GeoPackage ya generado; además, el recorte del `.pbf` toma ≈60 s y la primera carga de `comunas_cl` ≈90 s. Recursos: 6 CPU y 7,55 GB de RAM asignados a Docker (WSL2)..

Las consultas (Parte C) se corren después, con `python3 consultas.py` (ver sección 5).

## 2. Fuentes y versiones

| Fuente | Versión | Fecha |
|---|---|---|
| OpenStreetMap, extracto de Chile (Geofabrik, ODbL) | `chile-261013.osm.pbf` (349 MB) | extracto del 13-10-2026 (el nombre lleva la fecha del extracto), descargado el 13-10-2026 |
| GTFS Red Movilidad (DTPM) | `GTFS_20261003.zip`, `feed_version V168.20261003` | vigente desde el 03-10-2026, válido hasta el 31-12-2026; descargado el 13-10-2026 |
| DPA 2023 | `comunas_cl.sql` (Lab 03) | 2023 |

Nota: el enunciado menciona `GTFS 20260829.zip` (vigente al 08-09); entregamos con el vigente a la fecha de nuestra descarga, como pide el enunciado. Los paraderos de OSM son los que alguien dibujó; el GTFS es lo que el operador declara. Cada conclusión del informe indica de qué fuente es.

## 3. Tablas, conteos e índices

Conteos de la carga (detalle completo, tamaños, SRID de cada columna e índices en `resultados/etl_resumen.md`):

| Tabla | Filas | | Tabla | Filas |
|---|---:|---|---|---:|
| `osm_puntos` | 255.829 | | `paraderos_gtfs` | 6.569 |
| `osm_lineas` | 169.742 | | `estaciones_gtfs` | 593 |
| `osm_poligonos` | 146.835 | | `recorridos` | 708 |
| `calles` | 100.915 | | `raw_stops` | 18.455 |
| `edificios` | 118.852 | | `raw_shapes` | 456.573 |
| `paraderos_osm` | 6.572 | | `raw_stop_times` | 1.098.529 |
| `amenidades` | 20.874 | | `raw_frequencies` | 14.542 |
| `comunas_zona` / `comunas_sub` | 30 / 182 | | `comunas_cl` | 345 |

**Índices por tabla** (`resultados/etl_resumen.md` trae también las definiciones completas). Las tablas `raw_*` restantes y `gtfs_stop_modos` son auxiliares:

| Tabla | Índices |
|---|---|
| `osm_puntos` | `osm_puntos_geom_geom_idx` (gist, geom); `osm_puntos_pkey` (btree, id) |
| `osm_lineas` | `osm_lineas_geom_geom_idx` (gist, geom); `osm_lineas_pkey` (btree, id) |
| `osm_poligonos` | `osm_poligonos_geom_geom_idx` (gist, geom); `osm_poligonos_pkey` (btree, id) |
| `calles` | `idx_calles_geom` (gist, geom) |
| `edificios` | `idx_edificios_geom` (gist, geom); `idx_edificios_punto` (gist, punto) |
| `paraderos_osm` | `idx_paraderos_osm_geom` (gist, geom) |
| `amenidades` | `idx_amenidades_amenity` (btree, amenity); `idx_amenidades_geom` (gist, geom) |
| `comunas_cl` | `comunas_cl_geom_idx` (gist, geom); `comunas_cl_pkey` (btree, gid) |
| `comunas_zona` | `idx_comunas_zona_geom` (gist, geom) |
| `comunas_sub` | `idx_comunas_sub_geom` (gist, geom) |
| `raw_routes` | `raw_routes_route_idx` (btree, route_id) |
| `raw_trips` | `raw_trips_shape_idx` (btree, shape_id); `raw_trips_trip_idx` (btree, trip_id) |
| `gtfs_stop_modos` | `gtfs_stop_modos_stop_id_idx` (btree, stop_id) |
| `paraderos_gtfs` | `idx_paraderos_gtfs_geom` (gist, geom); `paraderos_gtfs_pkey` (btree, stop_id) |
| `estaciones_gtfs` | `idx_estaciones_gtfs_geom` (gist, geom) |
| `recorridos` | `idx_recorridos_geom` (gist, geom); `idx_recorridos_ruta` (btree, route_short_name); `recorridos_pkey` (btree, shape_id) |

Tras las consultas se crean además el índice parcial `idx_amenidades_salud_geom` (solo amenidades de salud) y las tablas `caja_zona`, `comunas_caja`, `comunas_caja_sub`, `edificios_comuna`, `grilla_hex` (vista materializada) y `recorridos_bus_buf15`, cada una con su índice GiST (ver `sql/consultas/`).

Resumen de lo que se crea:

| Capa | Origen | Notas |
|---|---|---|
| `osm_puntos`, `osm_lineas`, `osm_poligonos` | `ogr2ogr` desde el GeoPackage | crudas; `other_tags` como `hstore`; índice GiST automático |
| `calles`, `edificios`, `paraderos_osm`, `amenidades` | derivadas de OSM | `edificios` con `geom` y `punto` (punto interior) |
| `comunas_cl`, `comunas_zona`, `comunas_sub` | DPA | `comunas_zona` = comunas que tocan la caja; `comunas_sub` = `ST_Subdivide(geom, 128)` |
| `raw_*` (6 tablas) | GTFS por `COPY` | todo texto; columnas tomadas de la cabecera real de cada archivo |
| `paraderos_gtfs`, `estaciones_gtfs` | `stops.txt` + `stop_times.txt` | ver decisiones |
| `recorridos` | `shapes.txt` + `trips.txt` + `routes.txt` | una `LineString` por `shape_id` |

## 4. Decisiones

**SRID.** Todo se lleva a 5361 al cargar (`-t_srs` en `ogr2ogr`; `ST_Transform` desde 4326 para el GTFS). Cada columna geométrica queda con tipo y SRID declarados, y `cargar.py` aborta si alguna no es 5361.

**Punto interior vs polígono.** `edificios.punto = ST_PointOnSurface(geom)`. Cada edificio cuenta una sola vez, en la comuna donde cae su punto; con el polígono (`ST_Intersects`) los que cruzan un límite comunal se cuentan en dos comunas. Las preguntas por comuna usan el punto. Medido: con el polígono, 34 de los 118.852 edificios tocan más de una comuna y se contarían dos veces (0,03 %).

**Geometrías inválidas de OSM.** Se reparan con `ST_Multi(ST_CollectionExtract(ST_MakeValid(geom), 3))` antes de derivar (sin eso, `ST_PointOnSurface` falla). De 146.835 polígonos, **368 eran inválidos**. 309 eran degenerados (anillos de menos de 3 puntos): `ST_MakeValid` los deja **vacíos** y se excluyen al derivar `edificios` y `amenidades`. Los otros 59 eran autointersecciones (58) y un anillo autointersectado (1) que sí se repararon. Tras reparar quedan 0 inválidos. De los polígonos válidos con `building` salen 118.852 edificios.

**Qué es un «paraderos GTFS».** `stops.txt` mezcla varias cosas: de 18.455 filas, 5.565 no tienen coordenadas (nodos genéricos y áreas de embarque) y se descartan. De las 7.162 con coordenadas dentro de la caja, definimos `paraderos_gtfs` como las atendidas por algún viaje de **bus** (`route_type = 3`, vía `stop_times` → `trips` → `routes`), que es lo comparable con `highway=bus_stop` de OSM. Valores esperados (verificados en Python sobre el feed): 6.569 de bus; el resto va a `estaciones_gtfs` (234 andenes de metro, 8 de tren, 103 estaciones, 247 accesos y 1 parada sin viajes).

**Recorridos y shapes múltiples por ruta.** `shapes.txt` tiene 981 `shape_id` y 456.573 puntos, sin secuencias duplicadas ni fuera de orden. 859 shapes tienen viajes y 122 no tienen ninguno (huérfanos, descartados). Las 428 rutas tienen entre 1 y 5 shapes (248 tienen exactamente 2: ida y vuelta) y **ningún shape pertenece a dos rutas**. Conservamos **una fila por shape** (no unimos ni elegimos uno por ruta) y las preguntas cuentan rutas con `COUNT(DISTINCT route_short_name)`. Los recorridos que intersectan la caja se guardan **completos**, sin recortar; el recorte a comunas o a la caja se hace en la consulta correspondiente (Q4, Q6). La tabla incluye bus, metro y tren (`route_type`); cada consulta indica si filtra por bus.

**`stop_times.txt`.** 1.098.529 filas (≈50 MB), cargadas con `COPY` a una tabla de texto; nunca `INSERT` por fila. El feed opera por **frecuencias** (`frequencies.txt`, 14.542 filas): `stop_times` describe viajes plantilla, no salidas reales, así que `n_viajes_plantilla` **no** es «viajes por día».

**Efecto de borde.** OSM y GTFS se recortan a la misma caja. Un edificio a menos de 500 m del borde puede parecer «sin paradero» solo porque su paradero quedó afuera. Por eso Q2 mide únicamente edificios a ≥ 500 m del borde de la caja (`caja_interior_500`). Además, varias comunas quedan cortadas por la caja (Las Condes, La Florida, Peñalolén…): Q1 entrega la densidad sobre el área total de la comuna (lo que pide el enunciado) y sobre el área dentro de la caja, que es la que corresponde a los datos cargados. Q4 recorta los trazados a «comuna ∩ caja».

**Km de trazado (Q4).** Es kilómetros de trazado *acumulado*: cada shape (ruta y sentido) cuenta, así que dos rutas por la misma calle suman dos veces. Mide oferta de recorridos, no longitud de red.

**Muestra en los planes sin índice.** Para Q2 el plan con y sin índice se compara sobre una muestra fija de 2.000 edificios: sin índice, la consulta completa (118 mil edificios × 6.569 paraderos) tardaría demasiado. Los planes sin índice apagan `enable_indexscan` y `enable_bitmapscan` solo dentro de una transacción.

**Índices.** GiST sobre toda columna geométrica, B-tree sobre `route_short_name` y `amenity`, claves primarias en `paraderos_gtfs` y `recorridos`. Índice inútil según `pg_stat_user_indexes`: `idx_edificios_geom` (4,8 MB, 0 usos), porque todas las consultas usan el punto interior; tampoco se usaron `idx_calles_geom` (4,2 MB) ni `idx_amenidades_geom` (reemplazado por el índice parcial de salud).

## 5. Consultas, resultados y mapas

```bash
python3 consultas.py                # todas, en orden (Q5 con la ruta 514)
python3 consultas.py --ruta 505     # otra ruta para Q5
python3 consultas.py --solo q4 q6   # solo algunas
```

| Pregunta | Archivo(s) en `sql/consultas/` | Patrón |
|---|---|---|
| Q1 paraderos por comuna | `q1_paraderos_por_comuna.sql`, `q1_plan.sql` | punto-en-polígono |
| Q2 cobertura 500 m | `q2_cobertura.sql`, `q2_plan_con_indice.sql`, `q2_plan_sin_indice.sql` | anti-join `NOT EXISTS` + `ST_DWithin` |
| Q3 dos fuentes | `q3_dos_fuentes.sql`, `q3b_sensibilidad.sql` | anti-join en los dos sentidos; KNN para la sensibilidad al umbral |
| Q4 km por comuna | `q4_plan_con_subdivide.sql`, `q4_plan_sin_subdivide.sql`, `q4_plan_completa_*_subdivide.sql`, `q4_km_por_comuna.sql` | `ST_Intersection` línea/polígono; `ST_Subdivide` medido con comunas recortadas a la caja y con comunas completas |
| Q5 vecino más cercano | `q5_vecino_mas_cercano.sql`, `q5b_resumen.sql`, `q5_plan_con_indice.sql`, `q5_plan_sin_indice.sql` | `CROSS JOIN LATERAL` + `<->` + `LIMIT 1`, índice parcial |
| Q6 grilla hexagonal | `q6_grilla.sql`, `q6_top10.sql`, `q6b_resumen.sql` | `ST_HexagonGrid` + vista materializada |
| Q7 propia: vías principales sin recorrido | `q7_00_buffer.sql`, `q7_vias_sin_servicio.sql`, `q7b_top_calles.sql` | línea contra línea con tolerancia de 15 m |
| Uso de índices | `q9_indices_uso.sql` | `pg_stat_user_indexes` |

El informe está en `informe/` (Word editable y PDF, 6 páginas) y se entrega por Aula junto con el link del repositorio. El notebook `analisis.ipynb` (ejecutarlo con *Run All* y guardarlo con las salidas) reúne las consultas, resultados, planes y mapas para recorrerlos en orden.

Los mapas del informe se dibujan con `python3 mapas.py` (necesita `matplotlib`; lee `resultados/mapas.gpkg`) y quedan en `resultados/mapas/*.png`.

Salidas: CSV en `resultados/`, planes en `resultados/planes/` (con `resumen_tiempos.md`) y los mapas en `resultados/mapas.gpkg` (capas `q1_densidad_paraderos`, `q2_cobertura_500m`, `q5_paraderos_ruta`, `q5_salud`, `q6_grilla_hex`, todas en SRID 5361).

**Q7, la propia.** *¿Qué parte de las vías principales dibujadas en OSM (motorway a tertiary) tiene un recorrido de bus del GTFS a ≤ 15 m, y cuáles son las vías con más kilómetros sin servicio?* Cruza la red vial de OSM con los trazados que declara el operador; no es una variante de las anteriores (ni conteo por comuna, ni cobertura de edificios, ni comparación de paraderos).

## 6. Qué no funcionó

- `ST_Subdivide` **no aceleró** Q4: con comunas recortadas a la zona pasó de 0,43 s a 0,65 s y con comunas completas de 0,53 s a 0,62 s (30 → 182 piezas, 3.298 → 5.945 intersecciones). Las comunas del centro son polígonos livianos.
- Un `GROUP BY 1` con un agregado en la columna 1 hizo fallar una consulta de `cargar.py`; se corrigió con una subconsulta.
- Los planes sin índice activan compilación JIT, que infla sus tiempos totales (Q5); por eso se compara también el costo por paradero.
- Q7 usa 15 m de tolerancia: las avenidas con calzadas separadas pueden aparecer sin bus aunque tengan servicio. No se probó con 30 m.
