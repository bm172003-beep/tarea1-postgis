-- Q7 (propia). ¿Qué parte de las vías principales dibujadas en OSM tiene un recorrido de bus del GTFS encima?
-- Cruza la red vial (OSM) con los trazados declarados por el operador (GTFS): líneas contra líneas, con una tolerancia de 15 m.
-- Por clase de vía (highway): km totales, km con algún recorrido de bus a <= 15 m, y %.
DROP TABLE IF EXISTS res_q7;
CREATE TABLE res_q7 AS
WITH vias AS (
  SELECT id, name, highway, geom, ST_Length(geom) AS largo_m
  FROM calles
  WHERE highway IN ('motorway', 'trunk', 'primary', 'secondary', 'tertiary')
), cubierto AS (
  SELECT v.id, sum(ST_Length(ST_Intersection(v.geom, b.geom))) AS m_cubiertos
  FROM vias v
  JOIN recorridos_bus_buf15 b ON ST_Intersects(v.geom, b.geom)
  GROUP BY v.id
)
SELECT v.id, v.name, v.highway, v.largo_m,
       least(coalesce(c.m_cubiertos, 0), v.largo_m) AS m_con_bus
FROM vias v
LEFT JOIN cubierto c USING (id);

SELECT highway AS clase_via,
       count(*) AS tramos,
       round((sum(largo_m) / 1000)::numeric, 1)                        AS km_total,
       round((sum(m_con_bus) / 1000)::numeric, 1)                      AS km_con_bus_15m,
       round((100 * sum(m_con_bus) / sum(largo_m))::numeric, 1)        AS pct_con_bus
FROM res_q7
GROUP BY highway
ORDER BY array_position(ARRAY['motorway', 'trunk', 'primary', 'secondary', 'tertiary']::text[], highway::text);
