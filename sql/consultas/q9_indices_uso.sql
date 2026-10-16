-- Uso de los índices tras correr las consultas (pg_stat_user_indexes). idx_scan = 0 → índice que ninguna consulta usó (un hallazgo para el informe).
SELECT relname AS tabla, indexrelname AS indice, idx_scan AS usos,
       pg_size_pretty(pg_relation_size(indexrelid)) AS tamano
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND relname IN ('calles', 'edificios', 'paraderos_osm', 'amenidades', 'comunas_zona', 'comunas_sub',
                  'paraderos_gtfs', 'estaciones_gtfs', 'recorridos', 'comunas_caja', 'comunas_caja_sub',
                  'grilla_hex', 'recorridos_bus_buf15', 'caja_zona')
ORDER BY idx_scan, pg_relation_size(indexrelid) DESC;
