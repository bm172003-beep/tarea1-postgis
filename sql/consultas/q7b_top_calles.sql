-- Q7 (detalle). Las 15 vías con nombre (motorway a secondary) de >= 1 km con más kilómetros SIN recorrido de bus a <= 15 m.
SELECT name AS calle, highway AS clase,
       round((sum(largo_m) / 1000)::numeric, 2)                         AS km,
       round((sum(m_con_bus) / 1000)::numeric, 2)                       AS km_con_bus,
       round(((sum(largo_m) - sum(m_con_bus)) / 1000)::numeric, 2)      AS km_sin_bus,
       round((100 * sum(m_con_bus) / sum(largo_m))::numeric, 1)         AS pct_con_bus
FROM res_q7
WHERE highway IN ('motorway', 'trunk', 'primary', 'secondary') AND name IS NOT NULL
GROUP BY name, highway
HAVING sum(largo_m) >= 1000
ORDER BY km_sin_bus DESC
LIMIT 15;
