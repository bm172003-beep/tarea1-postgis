-- Plan de Q2 SIN índice (se apagan index scan y bitmap scan SOLO dentro de esta transacción).
-- Misma muestra de 2.000 edificios: sin índice cada edificio se compara con los 6.569 paraderos.
BEGIN;
SET LOCAL enable_indexscan = off;
SET LOCAL enable_bitmapscan = off;
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) AS sin_cobertura
FROM (SELECT punto FROM edificios_comuna ORDER BY id LIMIT 2000) b
WHERE NOT EXISTS (SELECT 1 FROM paraderos_gtfs p WHERE ST_DWithin(b.punto, p.geom, 500));
COMMIT;
