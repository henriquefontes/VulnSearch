Latência por consulta (mediana de 3 repetições, sem cache, 10 resultados por página, BM25F). Cliente = ponta a ponta (urllib); servidor = tempo dentro do /api/busca; o resto é serialização JSON + HTTP.

| id | consulta | total | resultados | cliente ms | ranqueamento ms | trechos ms | servidor ms | serialização + HTTP ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| q01 | CVE-2021-44228 | 6 | 6 | 12.1 | 0.1 | 10.1 | 10.3 | 1.8 |
| q02 | MS17-010 | 5 | 5 | 5.4 | 0.1 | 3.4 | 3.6 | 1.8 |
| q03 | CWE-79 | 809 | 10 | 18.9 | 2.5 | 14.0 | 16.7 | 2.2 |
| q04 | SA-CORE-2018-002 | 7 | 7 | 8.1 | 0.1 | 6.3 | 6.4 | 1.7 |
| q05 | sql injection wordpress plugin | 18291 | 10 | 156.2 | 144.6 | 3.0 | 152.5 | 3.7 |
| q06 | remote code execution apache struts | 42772 | 10 | 237.9 | 221.5 | 3.5 | 234.2 | 3.6 |
| q07 | cross site scripting drupal | 20032 | 10 | 137.5 | 123.6 | 5.3 | 134.1 | 3.0 |
| q08 | joomla sql injection | 16318 | 10 | 111.2 | 99.0 | 2.8 | 107.6 | 3.3 |
| q09 | buffer overflow windows smb | 19156 | 10 | 151.7 | 137.1 | 5.6 | 148.1 | 3.7 |
| q10 | openssh vulnerability | 62 | 10 | 211.7 | 200.5 | 4.6 | 208.8 | 2.9 |
| q11 | privilege escalation linux kernel | 22812 | 10 | 95.9 | 83.1 | 3.4 | 92.8 | 3.3 |
| q12 | log4j | 16 | 10 | 9.9 | 0.1 | 7.7 | 7.9 | 2.1 |
| q13 | path traversal | 16657 | 10 | 69.7 | 56.6 | 7.7 | 66.8 | 2.8 |
| q14 | java deserialization | 2271 | 10 | 14.1 | 7.8 | 3.5 | 11.8 | 2.4 |
| q15 | denial of service | 11132 | 10 | 61.9 | 52.1 | 3.9 | 59.1 | 3.0 |
| q16 | csrf token bypass | 11959 | 10 | 61.3 | 43.2 | 12.0 | 58.6 | 2.7 |
| q17 | use after free | 25756 | 10 | 101.7 | 86.7 | 7.2 | 98.8 | 3.0 |
| q18 | strcpy stack overflow | 8378 | 10 | 49.5 | 37.7 | 7.3 | 47.1 | 2.5 |
| q19 | codigo:shellcode | 2983 | 10 | 20.3 | 8.7 | 7.9 | 18.1 | 2.4 |
| q20 | codigo:system | 10048 | 10 | 32.2 | 24.9 | 3.1 | 29.9 | 2.3 |
