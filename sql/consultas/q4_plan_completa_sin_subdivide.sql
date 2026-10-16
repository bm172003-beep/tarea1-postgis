-- Q4 (experimento de tiempo con geometrías COMPLETAS, sin Subdivide): los trazados contra las comunas enteras
-- (comunas_zona.geom, decenas de miles de vértices cada una), sin recortar a la caja.
-- Solo mide tiempo: los km incluyen lo que cae fuera de la caja, así que NO reemplazan a los de q4_km_por_comuna.
EXPLAIN (ANALYZE, BUFFERS)
WITH tramos AS MATERIALIZED (
  SELECT c.comuna, ST_Length(ST_Intersection(r.geom, c.geom)) AS m
  FROM recorridos r
  JOIN comunas_zona c ON ST_Intersects(r.geom, c.geom)
)
SELECT comuna, round((sum(m) / 1000)::numeric, 1) AS km
FROM tramos
GROUP BY comuna;
