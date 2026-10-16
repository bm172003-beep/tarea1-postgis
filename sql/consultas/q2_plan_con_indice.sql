-- Plan de Q2 CON índice, sobre una muestra fija de 2.000 edificios (la misma en la versión sin
-- índice, para poder compararlas). Se espera: Nested Loop Anti Join, edificios afuera y
-- Index Scan sobre el GiST de paraderos_gtfs adentro.
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) AS sin_cobertura
FROM (SELECT punto FROM edificios_comuna ORDER BY id LIMIT 2000) b
WHERE NOT EXISTS (SELECT 1 FROM paraderos_gtfs p WHERE ST_DWithin(b.punto, p.geom, 500));
