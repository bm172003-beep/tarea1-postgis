-- Q4 (experimento de tiempo con geometrías COMPLETAS, CON Subdivide): las mismas comunas enteras, pero en piezas
-- de <= 128 vértices (tabla comunas_sub, creada en sql/01_osm.sql). Mismo cálculo y mismos km que la versión sin Subdivide.
EXPLAIN (ANALYZE, BUFFERS)
WITH tramos AS MATERIALIZED (
  SELECT s.comuna, ST_Length(ST_Intersection(r.geom, s.geom)) AS m
  FROM recorridos r
  JOIN comunas_sub s ON ST_Intersects(r.geom, s.geom)
)
SELECT comuna, round((sum(m) / 1000)::numeric, 1) AS km
FROM tramos
GROUP BY comuna;
