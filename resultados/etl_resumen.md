# Resumen de la carga (generado por cargar.py · 2026-10-15 22:13)

## Fuentes y versiones

- OSM: `chile-261013.osm.pbf` (349 MB) — Geofabrik, ODbL. Zona `santiago-centro`: lon -70.75…-70.52 · lat -33.52…-33.36 → osm_santiago-centro.gpkg (146 MB)
- GTFS: `GTFS_20261003.zip (12.8 MB)` — feed_version `V168.20261003`, vigencia 20261003 a 20261231
- DPA: `comunas_cl.sql` (DPA 2023, Lab 03)
- Motor: PostgreSQL 16.15 (Debian 16.15-1.pgdg12+2) on x86_64-pc-linux-gnu · PostGIS 3.6 USE_GEOS=1 USE_PROJ=1 USE_STATS=1
- Duración de la carga: 3.3 min

## Reparación de geometrías OSM (ST_MakeValid)

- Polígonos totales: 146,835
- Inválidos antes de reparar: **368** (área declarada: 8901731 m²)
- Tras `ST_Multi(ST_CollectionExtract(ST_MakeValid(geom), 3))`: 0 inválidos, 309 vacíos (excluidos al derivar `edificios` y `amenidades`)
- Razones más frecuentes (ST_IsValidReason, sin coordenadas):

```
Too few points in geometry component | 232
IllegalArgumentException: Invalid number of points in LinearRing found 2 - must be 0 or >= 3 | 77
Self-intersection | 58
Ring Self-intersection | 1
```

## GTFS

- `stops.txt`: 18,455 filas (cargado con COPY)
- `routes.txt`: 428 filas (cargado con COPY)
- `trips.txt`: 26,159 filas (cargado con COPY)
- `shapes.txt`: 456,573 filas (cargado con COPY)
- `stop_times.txt`: 1,098,529 filas (cargado con COPY)
- `frequencies.txt`: 14,542 filas (cargado con COPY)
- Shapes: 981 en shapes.txt, de los cuales 122 no tienen ningún viaje en trips.txt (descartados).

## Tablas (filas · tamaño total con índices)

| tabla | filas | tamaño |
|---|---:|---:|
| `osm_puntos` | 255,829 | 57 MB |
| `osm_lineas` | 169,742 | 47 MB |
| `osm_poligonos` | 146,835 | 49 MB |
| `calles` | 100,915 | 23 MB |
| `edificios` | 118,852 | 40 MB |
| `paraderos_osm` | 6,572 | 1000 kB |
| `amenidades` | 20,874 | 3128 kB |
| `comunas_cl` | 345 | 109 MB |
| `comunas_zona` | 30 | 336 kB |
| `comunas_sub` | 182 | 304 kB |
| `raw_stops` | 18,455 | 2072 kB |
| `raw_routes` | 428 | 120 kB |
| `raw_trips` | 26,159 | 3544 kB |
| `raw_shapes` | 456,573 | 27 MB |
| `raw_stop_times` | 1,098,529 | 77 MB |
| `raw_frequencies` | 14,542 | 1016 kB |
| `gtfs_stop_modos` | 12,465 | 976 kB |
| `paraderos_gtfs` | 6,569 | 1208 kB |
| `estaciones_gtfs` | 593 | 136 kB |
| `recorridos` | 708 | 6928 kB |

## Geometrías (tipo y SRID declarados)

| columna | SRID | tipo |
|---|---:|---|
| `amenidades.geom` | 5361 | POINT |
| `calles.geom` | 5361 | LINESTRING |
| `comunas_cl.geom` | 5361 | MULTIPOLYGON |
| `comunas_sub.geom` | 5361 | GEOMETRY |
| `comunas_zona.geom` | 5361 | MULTIPOLYGON |
| `edificios.geom` | 5361 | MULTIPOLYGON |
| `edificios.punto` | 5361 | POINT |
| `estaciones_gtfs.geom` | 5361 | POINT |
| `osm_lineas.geom` | 5361 | LINESTRING |
| `osm_poligonos.geom` | 5361 | MULTIPOLYGON |
| `osm_puntos.geom` | 5361 | POINT |
| `paraderos_gtfs.geom` | 5361 | POINT |
| `paraderos_osm.geom` | 5361 | POINT |
| `recorridos.geom` | 5361 | LINESTRING |

## Índices

| tabla | índice | definición |
|---|---|---|
| `amenidades` | `idx_amenidades_amenity` | `idx_amenidades_amenity ON public.amenidades USING btree (amenity)` |
| `amenidades` | `idx_amenidades_geom` | `idx_amenidades_geom ON public.amenidades USING gist (geom)` |
| `calles` | `idx_calles_geom` | `idx_calles_geom ON public.calles USING gist (geom)` |
| `comunas_cl` | `comunas_cl_geom_idx` | `comunas_cl_geom_idx ON public.comunas_cl USING gist (geom)` |
| `comunas_cl` | `comunas_cl_pkey` | `comunas_cl_pkey ON public.comunas_cl USING btree (gid)` |
| `comunas_sub` | `idx_comunas_sub_geom` | `idx_comunas_sub_geom ON public.comunas_sub USING gist (geom)` |
| `comunas_zona` | `idx_comunas_zona_geom` | `idx_comunas_zona_geom ON public.comunas_zona USING gist (geom)` |
| `edificios` | `idx_edificios_geom` | `idx_edificios_geom ON public.edificios USING gist (geom)` |
| `edificios` | `idx_edificios_punto` | `idx_edificios_punto ON public.edificios USING gist (punto)` |
| `estaciones_gtfs` | `idx_estaciones_gtfs_geom` | `idx_estaciones_gtfs_geom ON public.estaciones_gtfs USING gist (geom)` |
| `gtfs_stop_modos` | `gtfs_stop_modos_stop_id_idx` | `gtfs_stop_modos_stop_id_idx ON public.gtfs_stop_modos USING btree (stop_id)` |
| `osm_lineas` | `osm_lineas_geom_geom_idx` | `osm_lineas_geom_geom_idx ON public.osm_lineas USING gist (geom)` |
| `osm_lineas` | `osm_lineas_pkey` | `osm_lineas_pkey ON public.osm_lineas USING btree (id)` |
| `osm_poligonos` | `osm_poligonos_geom_geom_idx` | `osm_poligonos_geom_geom_idx ON public.osm_poligonos USING gist (geom)` |
| `osm_poligonos` | `osm_poligonos_pkey` | `osm_poligonos_pkey ON public.osm_poligonos USING btree (id)` |
| `osm_puntos` | `osm_puntos_geom_geom_idx` | `osm_puntos_geom_geom_idx ON public.osm_puntos USING gist (geom)` |
| `osm_puntos` | `osm_puntos_pkey` | `osm_puntos_pkey ON public.osm_puntos USING btree (id)` |
| `paraderos_gtfs` | `idx_paraderos_gtfs_geom` | `idx_paraderos_gtfs_geom ON public.paraderos_gtfs USING gist (geom)` |
| `paraderos_gtfs` | `paraderos_gtfs_pkey` | `paraderos_gtfs_pkey ON public.paraderos_gtfs USING btree (stop_id)` |
| `paraderos_osm` | `idx_paraderos_osm_geom` | `idx_paraderos_osm_geom ON public.paraderos_osm USING gist (geom)` |
| `raw_routes` | `raw_routes_route_idx` | `raw_routes_route_idx ON public.raw_routes USING btree (route_id)` |
| `raw_trips` | `raw_trips_shape_idx` | `raw_trips_shape_idx ON public.raw_trips USING btree (shape_id)` |
| `raw_trips` | `raw_trips_trip_idx` | `raw_trips_trip_idx ON public.raw_trips USING btree (trip_id)` |
| `recorridos` | `idx_recorridos_geom` | `idx_recorridos_geom ON public.recorridos USING gist (geom)` |
| `recorridos` | `idx_recorridos_ruta` | `idx_recorridos_ruta ON public.recorridos USING btree (route_short_name)` |
| `recorridos` | `recorridos_pkey` | `recorridos_pkey ON public.recorridos USING btree (shape_id)` |
