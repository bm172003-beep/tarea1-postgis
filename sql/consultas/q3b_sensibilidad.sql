-- Q3 (complemento). ¿Cuánto depende el resultado del umbral de 50 m? Distancia al vecino más cercano
-- de la OTRA fuente (KNN con el índice GiST) y conteo de los que superan cada umbral.
WITH d_gtfs AS (
  SELECT (SELECT ST_Distance(p.geom, o.geom) FROM paraderos_osm o ORDER BY o.geom <-> p.geom LIMIT 1) AS dist
  FROM paraderos_gtfs p
), d_osm AS (
  SELECT (SELECT ST_Distance(o.geom, p.geom) FROM paraderos_gtfs p ORDER BY p.geom <-> o.geom LIMIT 1) AS dist
  FROM paraderos_osm o
)
SELECT u.umbral_m,
       (SELECT count(*) FROM d_gtfs WHERE dist > u.umbral_m) AS gtfs_sin_osm,
       round(100.0 * (SELECT count(*) FROM d_gtfs WHERE dist > u.umbral_m) / (SELECT count(*) FROM d_gtfs), 1) AS pct_gtfs_sin_osm,
       (SELECT count(*) FROM d_osm WHERE dist > u.umbral_m)  AS osm_sin_gtfs,
       round(100.0 * (SELECT count(*) FROM d_osm WHERE dist > u.umbral_m) / (SELECT count(*) FROM d_osm), 1) AS pct_osm_sin_gtfs
FROM (VALUES (10), (25), (50), (100), (200)) AS u(umbral_m)
ORDER BY u.umbral_m;
