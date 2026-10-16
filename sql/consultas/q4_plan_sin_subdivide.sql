-- Q4 (versión SIN ST_Subdivide): mismo cálculo contra la geometría entera de cada comuna.
-- Debe dar los mismos km; lo que cambia es el tiempo (ST_Intersection contra polígonos de decenas de miles de vértices).
DROP TABLE IF EXISTS res_q4_sin;
EXPLAIN (ANALYZE, BUFFERS)
CREATE TABLE res_q4_sin AS
WITH tramos AS MATERIALIZED (
  SELECT c.comuna, r.route_short_name, r.route_type,
         ST_Length(ST_Intersection(r.geom, c.geom_caja)) AS m
  FROM recorridos r
  JOIN comunas_caja c ON ST_Intersects(r.geom, c.geom_caja)
)
SELECT comuna,
       round((sum(m) / 1000)::numeric, 1)                                  AS km_total,
       round((sum(m) FILTER (WHERE route_type = 3) / 1000)::numeric, 1)    AS km_bus,
       count(DISTINCT route_short_name)                                    AS rutas_distintas
FROM tramos
GROUP BY comuna;
