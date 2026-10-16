SELECT c.comuna, r.edificios, r.pct_sin_gtfs, r.pct_sin_osm, c.geom_caja AS geom FROM res_q2 r JOIN comunas_caja c ON c.comuna = r.comuna
