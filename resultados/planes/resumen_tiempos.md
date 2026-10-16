# Tiempos de ejecución de los planes (EXPLAIN ANALYZE)

| archivo | ejecución (s) | planificación (ms) |
|---|---:|---:|
| `q1_plan.sql` | 0.01 | 8.5 |
| `q2_plan_con_indice.sql` | 0.04 | 8.2 |
| `q2_plan_sin_indice.sql` | 1.27 | 8.2 |
| `q4_plan_con_subdivide.sql` | 0.49 | 8.5 |
| `q4_plan_sin_subdivide.sql` | 0.44 | 9.4 |
| `q4_plan_completa_sin_subdivide.sql` | 0.54 | 9.1 |
| `q4_plan_completa_con_subdivide.sql` | 0.62 | 8.3 |
| `q5_plan_con_indice.sql` | 0.09 | 1.2 |
| `q5_plan_sin_indice.sql` | 0.97 | 1.2 |
