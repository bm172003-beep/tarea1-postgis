-- Q6. Grilla hexagonal de 500 m (ST_HexagonGrid, como en el Lab 05) sobre la caja de la zona, con vista materializada.
-- Por celda: edificios (por punto interior) y recorridos DISTINTOS que la cruzan (route_short_name, todos los modos).
-- LEFT JOIN: las celdas sin recorridos (n_rutas = 0) son justamente las que interesan y no deben desaparecer.
-- `completa` marca las celdas enteramente dentro de la caja (las del borde ven una parte de la ciudad).
DROP MATERIALIZED VIEW IF EXISTS grilla_hex CASCADE;
CREATE MATERIALIZED VIEW grilla_hex AS
WITH celdas AS (
  SELECT h.i, h.j, h.geom
  FROM caja_zona c CROSS JOIN LATERAL ST_HexagonGrid(500, c.geom) AS h
), ed AS (
  SELECT c.i, c.j, count(*) AS n
  FROM celdas c JOIN edificios e ON ST_Intersects(e.punto, c.geom)
  GROUP BY c.i, c.j
), ru AS (
  SELECT c.i, c.j, count(DISTINCT r.route_short_name) AS n
  FROM celdas c JOIN recorridos r ON ST_Intersects(r.geom, c.geom)
  GROUP BY c.i, c.j
)
SELECT c.i, c.j, c.geom,
       coalesce(ed.n, 0) AS n_edificios,
       coalesce(ru.n, 0) AS n_rutas,
       ST_Within(c.geom, (SELECT geom FROM caja_zona)) AS completa
FROM celdas c
LEFT JOIN ed USING (i, j)
LEFT JOIN ru USING (i, j);
CREATE INDEX idx_grilla_hex_geom ON grilla_hex USING GIST (geom);
ANALYZE grilla_hex;
