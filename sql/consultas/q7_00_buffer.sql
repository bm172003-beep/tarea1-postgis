-- Q7 (preparación): zona de 15 m alrededor de los trazados de BUS, en piezas pequeñas para el join.
-- 15 m absorbe la diferencia entre el trazado que declara el operador y la geometría que dibujó OSM.
DROP TABLE IF EXISTS recorridos_bus_buf15 CASCADE;
CREATE TABLE recorridos_bus_buf15 AS
SELECT ST_Subdivide(ST_Union(ST_Buffer(geom, 15)), 256)::geometry(Geometry, 5361) AS geom
FROM recorridos
WHERE route_type = 3;
CREATE INDEX idx_rec_bus_buf15_geom ON recorridos_bus_buf15 USING GIST (geom);
ANALYZE recorridos_bus_buf15;
