-- Q5 (resumen): distribución de las distancias de la ruta elegida.
SELECT count(*)                                                        AS paraderos,
       round(avg(dist_m))                                              AS media_m,
       round((percentile_cont(0.5) WITHIN GROUP (ORDER BY dist_m))::numeric) AS mediana_m,
       max(dist_m)                                                     AS maxima_m,
       count(*) FILTER (WHERE dist_m > 500)                            AS a_mas_de_500m,
       count(*) FILTER (WHERE amenity = 'pharmacy')                    AS mas_cercano_farmacia,
       count(*) FILTER (WHERE amenity IN ('hospital', 'clinic', 'doctors')) AS mas_cercano_otro_salud
FROM res_q5;
