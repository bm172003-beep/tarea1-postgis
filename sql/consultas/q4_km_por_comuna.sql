-- Q4. Resultado (versión con Subdivide) y verificación contra la versión sin Subdivide.
-- Requiere que antes hayan corrido q4_plan_con_subdivide.sql y q4_plan_sin_subdivide.sql.
SELECT c.comuna, c.km_total AS km_total_con_sub, s.km_total AS km_total_sin_sub,
       round(c.km_total - s.km_total, 1) AS dif_km, c.km_bus, c.rutas_distintas
FROM res_q4_con c
JOIN res_q4_sin s USING (comuna)
ORDER BY c.km_total DESC;
