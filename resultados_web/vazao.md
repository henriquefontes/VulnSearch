Vazão com clientes simultâneos (cada cliente faz as 20 consultas, sem cache). O lock serializa o ranqueamento: mais clientes aumentam a latência, não a vazão.

| clientes | requisições | segundos | req/s | mediana ms | p95 ms | máx. ms | erros |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 20 | 1.6 | 12.3 | 71.3 | 220.5 | 242.7 | 0 |
| 4 | 80 | 6.4 | 12.4 | 290.8 | 527.6 | 660.7 | 0 |
| 8 | 160 | 13.4 | 12.0 | 625.1 | 1114.5 | 1398.4 | 0 |
