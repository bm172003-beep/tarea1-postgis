-- Q6 (resumen y tamaño real de la celda: el `500` de ST_HexagonGrid, medido en metros).
SELECT count(*)                                                     AS celdas,
       count(*) FILTER (WHERE completa)                             AS celdas_completas,
       count(*) FILTER (WHERE n_edificios = 0)                      AS sin_edificios,
       count(*) FILTER (WHERE n_rutas = 0)                          AS sin_recorridos,
       count(*) FILTER (WHERE n_rutas = 0 AND n_edificios > 0)      AS con_edificios_y_sin_recorridos,
       max(n_edificios)                                             AS max_edificios,
       max(n_rutas)                                                 AS max_rutas,
       round(avg(ST_Area(geom)))                                    AS area_celda_m2,
       round((avg(ST_Perimeter(geom)) / 6)::numeric)                AS lado_celda_m
FROM grilla_hex;
