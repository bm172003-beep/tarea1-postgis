-- Q4 (versión CON ST_Subdivide). Km de trazado por comuna, recortando cada recorrido en el límite
-- comunal (comuna ∩ caja) con ST_Intersection. Las comunas van en piezas de <= 128 vértices.
-- Es "km de trazado acumulado": cada shape (ruta y sentido) cuenta, así que dos rutas por la misma calle suman dos veces.
-- MATERIALIZED evita que el planificador calcule ST_Intersection una vez por cada agregado.
DROP TABLE IF EXISTS res_q4_con;
EXPLAIN (ANALYZE, BUFFERS)
CREATE TABLE res_q4_con AS
WITH tramos AS MATERIALIZED (
  SELECT s.comuna, r.route_short_name, r.route_type,
         ST_Length(ST_Intersection(r.geom, s.geom)) AS m
  FROM recorridos r
  JOIN comunas_caja_sub s ON ST_Intersects(r.geom, s.geom)
)
SELECT comuna,
       round((sum(m) / 1000)::numeric, 1)                                  AS km_total,
       round((sum(m) FILTER (WHERE route_type = 3) / 1000)::numeric, 1)    AS km_bus,
       count(DISTINCT route_short_name)                                    AS rutas_distintas
FROM tramos
GROUP BY comuna;
