-- Plan de Q5 SIN índice: para cada paradero hay que calcular la distancia a TODAS las amenidades de salud y ordenarlas (top-N heapsort).
BEGIN;
SET LOCAL enable_indexscan = off;
SET LOCAL enable_bitmapscan = off;
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*)
FROM paraderos_gtfs p
CROSS JOIN LATERAL (
  SELECT am.id FROM amenidades am
  WHERE am.amenity IN ('pharmacy', 'hospital', 'clinic', 'doctors')
  ORDER BY am.geom <-> p.geom LIMIT 1
) a
WHERE p.stop_id IN (
  SELECT st.stop_id FROM raw_stop_times st
  JOIN raw_trips t ON t.trip_id = st.trip_id
  JOIN raw_routes r ON r.route_id = t.route_id
  WHERE r.route_short_name = :'ruta'
);
COMMIT;
