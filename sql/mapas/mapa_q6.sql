SELECT g.i, g.j, g.n_edificios, g.n_rutas, g.completa, (t.i IS NOT NULL) AS top10, g.geom FROM grilla_hex g LEFT JOIN res_q6_top10 t ON t.i = g.i AND t.j = g.j
