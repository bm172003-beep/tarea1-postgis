-- 02_gtfs.sql — del GTFS crudo (raw_*, todo texto, cargado con COPY) a geometrías en 5361.
-- Variables (psql -v): :xmin :ymin :xmax :ymax  (la caja se aplica AQUÍ, en la base).

DROP TABLE IF EXISTS paraderos_gtfs, estaciones_gtfs, recorridos, gtfs_stops, gtfs_stop_modos CASCADE;

CREATE INDEX IF NOT EXISTS raw_trips_trip_idx   ON raw_trips (trip_id);
CREATE INDEX IF NOT EXISTS raw_trips_shape_idx  ON raw_trips (shape_id);
CREATE INDEX IF NOT EXISTS raw_routes_route_idx ON raw_routes (route_id);

-- Qué modo (route_type: 0 tranvía/tren, 1 metro, 3 bus) sirve a cada parada, según stop_times.
-- n_viajes_plantilla cuenta viajes de stop_times; el feed opera por frecuencias
-- (frequencies.txt), así que NO son salidas reales por día.
CREATE TABLE gtfs_stop_modos AS
SELECT st.stop_id, r.route_type::int AS route_type, count(*) AS n_viajes_plantilla
FROM raw_stop_times st
JOIN raw_trips  t ON t.trip_id  = st.trip_id
JOIN raw_routes r ON r.route_id = t.route_id
GROUP BY st.stop_id, r.route_type::int;
CREATE INDEX ON gtfs_stop_modos (stop_id);

-- Todas las paradas CON coordenadas dentro de la caja, ya como punto 5361.
-- (stops.txt trae nodos genéricos y áreas de embarque sin lat/lon: se descartan aquí.)
CREATE TABLE gtfs_stops AS
SELECT stop_id, stop_name,
       NULLIF(location_type, '')::int AS location_type,
       ST_Transform(ST_SetSRID(ST_MakePoint(NULLIF(stop_lon, '')::float8, NULLIF(stop_lat, '')::float8), 4326), 5361)::geometry(Point, 5361) AS geom
FROM raw_stops
WHERE NULLIF(stop_lon, '')::float8 BETWEEN :xmin AND :xmax     -- NULL (sin coordenadas) queda fuera
  AND NULLIF(stop_lat, '')::float8 BETWEEN :ymin AND :ymax;

-- paraderos_gtfs = paradas atendidas por al menos un viaje de BUS (route_type = 3).
-- Es lo comparable con highway=bus_stop de OSM.
CREATE TABLE paraderos_gtfs AS
SELECT g.stop_id, g.stop_name, g.location_type, m.n_viajes_plantilla, g.geom
FROM gtfs_stops g
JOIN (SELECT stop_id, sum(n_viajes_plantilla) AS n_viajes_plantilla
      FROM gtfs_stop_modos WHERE route_type = 3 GROUP BY stop_id) m USING (stop_id);
ALTER TABLE paraderos_gtfs ADD PRIMARY KEY (stop_id);
CREATE INDEX idx_paraderos_gtfs_geom ON paraderos_gtfs USING GIST (geom);

-- estaciones_gtfs = el resto de las paradas con coordenadas (metro, tren, estaciones, accesos).
-- No entran a las preguntas de paraderos de bus; se conservan por completitud.
CREATE TABLE estaciones_gtfs AS
SELECT g.stop_id, g.stop_name, g.location_type,
       (SELECT string_agg(DISTINCT m.route_type::text, ',') FROM gtfs_stop_modos m WHERE m.stop_id = g.stop_id) AS modos,
       g.geom
FROM gtfs_stops g
WHERE NOT EXISTS (SELECT 1 FROM paraderos_gtfs p WHERE p.stop_id = g.stop_id);
CREATE INDEX idx_estaciones_gtfs_geom ON estaciones_gtfs USING GIST (geom);
DROP TABLE gtfs_stops;

-- recorridos: UNA LineString por shape_id. Los vértices se ordenan con
-- ST_MakeLine(punto ORDER BY shape_pt_sequence). Cada shape se asocia a su ruta vía
-- trips → routes. Un route_short_name tiene 1 a 5 shapes (ida, vuelta, variantes): se
-- conservan TODOS (una fila por shape) y las preguntas cuentan rutas con
-- count(DISTINCT route_short_name). Los shapes sin ningún viaje (huérfanos) se descartan.
-- Se conservan los shapes que intersectan la caja, completos (no recortados).
CREATE TABLE recorridos AS
WITH lineas AS (
  SELECT shape_id,
         ST_MakeLine(ST_SetSRID(ST_MakePoint(shape_pt_lon::float8, shape_pt_lat::float8), 4326)
                     ORDER BY shape_pt_sequence::int) AS geom,
         count(*) AS n_puntos
  FROM raw_shapes
  GROUP BY shape_id
), viajes AS (
  SELECT shape_id, route_id,
         min(NULLIF(direction_id, '')::int) AS direction_id,
         count(*) AS n_viajes
  FROM raw_trips
  GROUP BY shape_id, route_id
)
SELECT l.shape_id, v.route_id, r.route_short_name, r.route_long_name,
       r.route_type::int AS route_type, v.direction_id, v.n_viajes, l.n_puntos,
       ST_Transform(l.geom, 5361)::geometry(LineString, 5361) AS geom
FROM lineas l
JOIN viajes v USING (shape_id)
JOIN raw_routes r ON r.route_id = v.route_id
WHERE ST_Intersects(l.geom, ST_MakeEnvelope(:xmin, :ymin, :xmax, :ymax, 4326));
ALTER TABLE recorridos ADD PRIMARY KEY (shape_id);     -- falla si un shape quedara en dos rutas
CREATE INDEX idx_recorridos_geom  ON recorridos USING GIST (geom);
CREATE INDEX idx_recorridos_ruta  ON recorridos (route_short_name);
