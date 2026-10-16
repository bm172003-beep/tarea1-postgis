-- Q6. Las 10 celdas con más edificios y menos recorridos. Criterio: edificios por (recorridos + 1), solo celdas completas.
-- Una celda con 800 edificios y 2 recorridos (267) supera a una con 30 edificios y 0 (30), y una con 800 y 40 recorridos (20) queda abajo.
DROP TABLE IF EXISTS res_q6_top10;
CREATE TABLE res_q6_top10 AS
SELECT g.i, g.j, g.n_edificios, g.n_rutas,
       round(g.n_edificios::numeric / (g.n_rutas + 1), 1) AS edificios_por_ruta,
       (SELECT s.comuna FROM comunas_sub s WHERE ST_Intersects(ST_Centroid(g.geom), s.geom) LIMIT 1) AS comuna,
       g.geom
FROM grilla_hex g
WHERE g.completa
ORDER BY g.n_edificios::numeric / (g.n_rutas + 1) DESC, g.n_edificios DESC
LIMIT 10;

SELECT i, j, comuna, n_edificios, n_rutas, edificios_por_ruta
FROM res_q6_top10
ORDER BY edificios_por_ruta DESC, n_edificios DESC;
