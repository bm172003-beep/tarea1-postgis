-- 00_preparacion.sql — tablas auxiliares comunes a las consultas. Variables: :xmin :ymin :xmax :ymax
-- Efecto de borde: OSM y GTFS están recortados a la MISMA caja. Un edificio a menos de 500 m del
-- borde de la caja puede parecer "sin paradero" solo porque su paradero quedó afuera. Por eso
-- Q2 mide solo edificios a >= 500 m del borde (caja_interior_500), y las comunas se
-- recortan a la caja (comunas_caja) para que áreas y conteos hablen de lo mismo.

DROP TABLE IF EXISTS caja_zona, caja_interior_500, comunas_caja, comunas_caja_sub, edificios_comuna CASCADE;

-- La caja (definida en lon/lat) llevada a 5361; ST_Segmentize evita que los lados se curven mal.
CREATE TABLE caja_zona AS
SELECT ST_Transform(ST_Segmentize(ST_MakeEnvelope(:xmin, :ymin, :xmax, :ymax, 4326), 0.005), 5361)::geometry(Polygon, 5361) AS geom;
CREATE INDEX idx_caja_zona_geom ON caja_zona USING GIST (geom);

CREATE TABLE caja_interior_500 AS
SELECT ST_Buffer(geom, -500)::geometry(Polygon, 5361) AS geom FROM caja_zona;

-- Comunas de la zona: geometría completa, geometría recortada a la caja y sus áreas.
CREATE TABLE comunas_caja AS
WITH i AS (
  SELECT z.gid, z.cut_com, z.comuna, z.geom,
         ST_Multi(ST_CollectionExtract(ST_Intersection(ST_MakeValid(z.geom), c.geom), 3)) AS gc
  FROM comunas_zona z CROSS JOIN caja_zona c
)
SELECT gid, cut_com, comuna,
       geom::geometry(MultiPolygon, 5361)    AS geom,
       ST_Area(geom) / 1e6                   AS area_km2,
       gc::geometry(MultiPolygon, 5361)      AS geom_caja,
       ST_Area(gc) / 1e6                     AS area_caja_km2
FROM i
WHERE NOT ST_IsEmpty(gc);
ALTER TABLE comunas_caja ADD PRIMARY KEY (gid);
CREATE INDEX idx_comunas_caja_geom  ON comunas_caja USING GIST (geom);
CREATE INDEX idx_comunas_caja_gcaja ON comunas_caja USING GIST (geom_caja);

-- Lo mismo, subdividido: piezas de <= 128 vértices (para Q4, y para asignar edificios a comunas).
CREATE TABLE comunas_caja_sub AS
SELECT gid, comuna, ST_Subdivide(geom_caja, 128)::geometry(Geometry, 5361) AS geom
FROM comunas_caja;
CREATE INDEX idx_comunas_caja_sub_geom ON comunas_caja_sub USING GIST (geom);

-- Cada edificio en UNA comuna (por su punto interior). Se asigna con comunas_sub (polígonos
-- chicos): con las comunas enteras, cada punto-en-polígono recorre decenas de miles de vértices.
-- DISTINCT ON descarta el doble conteo de un punto que cayera justo en un corte de la subdivisión.
CREATE TABLE edificios_comuna AS
SELECT DISTINCT ON (e.id) e.id, s.comuna, e.punto
FROM edificios e
JOIN comunas_sub s ON ST_Intersects(e.punto, s.geom)
ORDER BY e.id, s.comuna;

-- Índice parcial solo para los establecimientos de salud (Q5): más chico y exacto para ese filtro.
DROP INDEX IF EXISTS idx_amenidades_salud_geom;
CREATE INDEX idx_amenidades_salud_geom ON amenidades USING GIST (geom)
  WHERE amenity IN ('pharmacy', 'hospital', 'clinic', 'doctors');

ANALYZE caja_zona; ANALYZE caja_interior_500; ANALYZE comunas_caja; ANALYZE comunas_caja_sub;
ANALYZE edificios_comuna; ANALYZE amenidades;
