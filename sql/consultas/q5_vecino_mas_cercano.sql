-- Q5. Para cada paradero de UNA ruta (:ruta = route_short_name), la farmacia o centro de salud más
-- cercano (pharmacy, hospital, clinic, doctors) y la distancia. Patrón: CROSS JOIN LATERAL + <-> + LIMIT 1.
-- El predicado del WHERE es el mismo del índice parcial idx_amenidades_salud_geom.
DROP TABLE IF EXISTS res_q5;
CREATE TABLE res_q5 AS
SELECT p.stop_id, p.stop_name, a.nombre, a.amenity, round(a.dist::numeric) AS dist_m, p.geom
FROM paraderos_gtfs p
CROSS JOIN LATERAL (
  SELECT am.name AS nombre, am.amenity, ST_Distance(am.geom, p.geom) AS dist
  FROM amenidades am
  WHERE am.amenity IN ('pharmacy', 'hospital', 'clinic', 'doctors')
  ORDER BY am.geom <-> p.geom
  LIMIT 1
) a
WHERE p.stop_id IN (
  SELECT st.stop_id
  FROM raw_stop_times st
  JOIN raw_trips  t ON t.trip_id  = st.trip_id
  JOIN raw_routes r ON r.route_id = t.route_id
  WHERE r.route_short_name = :'ruta'
);

SELECT stop_id, stop_name, nombre, amenity, dist_m
FROM res_q5
ORDER BY dist_m DESC, stop_id;
