-- Q2. Cobertura: % de edificios (OSM) a MÁS de 500 m de cualquier paradero, por comuna, con paraderos
-- GTFS y con paraderos OSM. Patrón: anti-join (NOT EXISTS + ST_DWithin) sobre el punto interior.
-- Solo edificios a >= 500 m del borde de la caja (ver 00_preparacion.sql). Comunas con < 100
-- edificios en esa zona se omiten del listado (porcentajes inestables), no de res_q2.
DROP TABLE IF EXISTS res_q2;
CREATE TABLE res_q2 AS
WITH base AS (
  SELECT ec.id, ec.comuna, ec.punto
  FROM edificios_comuna ec
  WHERE ST_Within(ec.punto, (SELECT geom FROM caja_interior_500))
), cobertura AS (
  SELECT b.comuna,
         NOT EXISTS (SELECT 1 FROM paraderos_gtfs p WHERE ST_DWithin(b.punto, p.geom, 500)) AS sin_gtfs,
         NOT EXISTS (SELECT 1 FROM paraderos_osm  o WHERE ST_DWithin(b.punto, o.geom, 500)) AS sin_osm
  FROM base b
)
SELECT comuna,
       count(*)                                                         AS edificios,
       count(*) FILTER (WHERE sin_gtfs)                                 AS sin_cobertura_gtfs,
       round(100.0 * count(*) FILTER (WHERE sin_gtfs) / count(*), 1)    AS pct_sin_gtfs,
       count(*) FILTER (WHERE sin_osm)                                  AS sin_cobertura_osm,
       round(100.0 * count(*) FILTER (WHERE sin_osm)  / count(*), 1)    AS pct_sin_osm
FROM cobertura
GROUP BY comuna;

SELECT comuna, edificios, pct_sin_gtfs, pct_sin_osm,
       round(pct_sin_osm - pct_sin_gtfs, 1)            AS dif_pp_osm_menos_gtfs,
       rank() OVER (ORDER BY pct_sin_gtfs DESC)        AS puesto_gtfs,
       rank() OVER (ORDER BY pct_sin_osm  DESC)        AS puesto_osm
FROM res_q2
WHERE edificios >= 100
ORDER BY pct_sin_gtfs DESC;
