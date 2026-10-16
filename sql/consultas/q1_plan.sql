-- Plan de Q1: ¿de qué lado se usa el índice GiST? (comunas afuera, paraderos adentro)
EXPLAIN (ANALYZE, BUFFERS)
SELECT c.comuna, count(p.stop_id)
FROM comunas_caja c
LEFT JOIN paraderos_gtfs p ON ST_Within(p.geom, c.geom)
GROUP BY c.comuna;
