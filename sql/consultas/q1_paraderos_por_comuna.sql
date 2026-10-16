-- Q1. Paraderos GTFS (bus) por comuna y densidad por km². Patrón: join punto-en-polígono.
-- Dos densidades: sobre el área TOTAL de la comuna (lo que pide el enunciado) y sobre el área que
-- cae dentro de la caja. En comunas cortadas por la caja (Las Condes, La Florida, Peñalolén…)
-- la primera subestima, porque el GTFS solo se cargó dentro de la caja.
DROP TABLE IF EXISTS res_q1;
CREATE TABLE res_q1 AS
SELECT c.gid, c.comuna,
       count(p.stop_id)                                         AS paraderos,
       round(c.area_km2::numeric, 1)                            AS area_km2,
       round((count(p.stop_id) / c.area_km2)::numeric, 2)       AS paraderos_por_km2,
       round(c.area_caja_km2::numeric, 1)                       AS area_en_caja_km2,
       round((count(p.stop_id) / c.area_caja_km2)::numeric, 2)  AS paraderos_por_km2_en_caja
FROM comunas_caja c
LEFT JOIN paraderos_gtfs p ON ST_Within(p.geom, c.geom)
GROUP BY c.gid, c.comuna, c.area_km2, c.area_caja_km2;

SELECT comuna, paraderos, area_km2, paraderos_por_km2, area_en_caja_km2, paraderos_por_km2_en_caja
FROM res_q1
ORDER BY paraderos_por_km2_en_caja DESC;
