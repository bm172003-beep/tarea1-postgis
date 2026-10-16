-- Q3. Dos fuentes, un objeto. Anti-join en los dos sentidos con 50 m.
WITH gtfs_chk AS (
  SELECT p.stop_id,
         NOT EXISTS (SELECT 1 FROM paraderos_osm o WHERE ST_DWithin(p.geom, o.geom, 50)) AS sin
  FROM paraderos_gtfs p
), osm_chk AS (
  SELECT o.id,
         NOT EXISTS (SELECT 1 FROM paraderos_gtfs p WHERE ST_DWithin(o.geom, p.geom, 50)) AS sin
  FROM paraderos_osm o
)
SELECT 'paraderos GTFS sin bus_stop OSM a <= 50 m' AS caso,
       count(*) AS total, count(*) FILTER (WHERE sin) AS sin_contraparte,
       round(100.0 * count(*) FILTER (WHERE sin) / count(*), 1) AS pct
FROM gtfs_chk
UNION ALL
SELECT 'bus_stop OSM sin paradero GTFS a <= 50 m',
       count(*), count(*) FILTER (WHERE sin),
       round(100.0 * count(*) FILTER (WHERE sin) / count(*), 1)
FROM osm_chk;
