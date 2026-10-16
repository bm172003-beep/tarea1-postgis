SELECT c.comuna, r.paraderos, r.paraderos_por_km2 AS dens_km2_comuna_completa, r.paraderos_por_km2_en_caja AS dens_km2_en_caja, c.geom_caja AS geom FROM comunas_caja c JOIN res_q1 r USING (gid)
