-- 01_osm.sql — capas derivadas de OSM + comunas de la zona.
-- Se ejecuta DESPUÉS de cargar osm_puntos/osm_lineas/osm_poligonos y de reparar las
-- geometrías inválidas (lo hace cargar.py, que cuenta y documenta las filas reparadas).
-- Variables (psql -v): :xmin :ymin :xmax :ymax  (caja de la zona, lon/lat, SRID 4326)
-- Todo en SRID 5361. Cada geometría con tipo y SRID declarados (geometry(Tipo, 5361)).

DROP TABLE IF EXISTS calles, edificios, paraderos_osm, amenidades, comunas_zona, comunas_sub CASCADE;

-- Calles: toda línea con etiqueta highway.
CREATE TABLE calles AS
SELECT id, osm_id, name, highway,
       other_tags -> 'maxspeed' AS maxspeed,
       other_tags -> 'oneway'   AS oneway,
       ST_Length(geom)          AS largo_m,
       geom
FROM osm_lineas
WHERE highway IS NOT NULL;
CREATE INDEX idx_calles_geom ON calles USING GIST (geom);

-- Edificios: polígono + punto interior. ST_PointOnSurface (no centroide): garantiza que el
-- punto cae DENTRO del polígono, y asigna cada edificio a una sola comuna (sin doble conteo
-- en los límites comunales). Los vacíos (resultado de ST_MakeValid) se excluyen.
CREATE TABLE edificios AS
SELECT id,
       coalesce(osm_id, osm_way_id)             AS osm_id,
       name, building,
       other_tags -> 'building:levels'          AS pisos,
       ST_Area(geom)                            AS area_m2,
       geom,
       ST_PointOnSurface(geom)::geometry(Point, 5361) AS punto
FROM osm_poligonos
WHERE building IS NOT NULL AND NOT ST_IsEmpty(geom);
CREATE INDEX idx_edificios_geom  ON edificios USING GIST (geom);
CREATE INDEX idx_edificios_punto ON edificios USING GIST (punto);

-- Paraderos de OSM: nodos con highway = 'bus_stop' (los que alguien dibujó).
CREATE TABLE paraderos_osm AS
SELECT id, osm_id, name, geom
FROM osm_puntos
WHERE highway = 'bus_stop';
CREATE INDEX idx_paraderos_osm_geom ON paraderos_osm USING GIST (geom);

-- Amenidades: nodos con amenity (vive en other_tags) + polígonos con amenity (columna),
-- estos últimos reducidos a su punto interior.
CREATE TABLE amenidades AS
SELECT id, osm_id, name, other_tags -> 'amenity' AS amenity,
       geom::geometry(Point, 5361) AS geom
FROM osm_puntos
WHERE other_tags ? 'amenity'
UNION ALL
SELECT id, coalesce(osm_id, osm_way_id), name, amenity,
       ST_PointOnSurface(geom)::geometry(Point, 5361)
FROM osm_poligonos
WHERE amenity IS NOT NULL AND NOT ST_IsEmpty(geom);
CREATE INDEX idx_amenidades_geom    ON amenidades USING GIST (geom);
CREATE INDEX idx_amenidades_amenity ON amenidades (amenity);

-- Comunas que tocan la caja de la zona (de las 345 del país quedan unas 30). La caja se
-- define en lon/lat y se lleva a 5361 para comparar con comunas_cl.
CREATE TABLE comunas_zona AS
SELECT *
FROM comunas_cl
WHERE ST_Intersects(geom, ST_Transform(ST_MakeEnvelope(:xmin, :ymin, :xmax, :ymax, 4326), 5361));
CREATE INDEX idx_comunas_zona_geom ON comunas_zona USING GIST (geom);

-- Comunas subdivididas (≤128 vértices por parte) para los joins pesados (Q4).
-- Sirve para recorte/intersección; NO para área, centroide ni count(DISTINCT) por comuna.
CREATE TABLE comunas_sub AS
SELECT gid, comuna, cut_reg,
       ST_Subdivide(geom, 128)::geometry(Geometry, 5361) AS geom
FROM comunas_zona;
CREATE INDEX idx_comunas_sub_geom ON comunas_sub USING GIST (geom);
