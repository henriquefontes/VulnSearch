Latência com e sem filtro (ponta a ponta, sem cache). O filtro restringe os candidatos antes do top-k; o ranqueamento é o mesmo.

| filtro | total médio | média ms | mediana ms | p95 ms | máx. ms |
|---|---:|---:|---:|---:|---:|
| sem filtro | 11474 | 76.0 | 69.3 | 206.7 | 238.6 |
| site=www.exploit-db.com | 7349 | 77.4 | 55.1 | 181.1 | 235.1 |
| site=github.com | 2564 | 93.3 | 99.1 | 243.6 | 246.0 |
| cve=CVE-2008-6543 | 4 | 77.5 | 59.9 | 187.7 | 240.0 |
