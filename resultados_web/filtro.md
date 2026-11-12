Latência com e sem filtro (ponta a ponta, sem cache). O filtro restringe os candidatos antes do top-k; o ranqueamento é o mesmo.

| filtro | total médio | média ms | mediana ms | p95 ms | máx. ms |
|---|---:|---:|---:|---:|---:|
| sem filtro | 11474 | 79.0 | 63.2 | 226.3 | 241.8 |
| site=www.exploit-db.com | 7349 | 78.2 | 58.7 | 182.9 | 252.4 |
| site=github.com | 2564 | 87.0 | 75.6 | 237.4 | 249.0 |
| cve=CVE-2008-6543 | 4 | 71.4 | 57.0 | 212.8 | 231.1 |
