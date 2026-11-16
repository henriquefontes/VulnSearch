Vazão com clientes simultâneos (cada cliente faz as 20 consultas, sem cache). O lock serializa o ranqueamento: mais clientes aumentam a latência, não a vazão.

| clientes | requisições | segundos | req/s | mediana ms | p95 ms | máx. ms | erros |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 20 | 1.7 | 11.9 | 60.4 | 224.4 | 260.4 | 0 |
| 4 | 80 | 6.3 | 12.7 | 290.9 | 452.2 | 522.2 | 0 |
| 8 | 160 | 12.9 | 12.4 | 623.3 | 1124.2 | 1301.0 | 0 |
