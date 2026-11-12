Latência por consulta (mediana de 3 repetições, sem cache, 10 resultados por página, BM25F). Cliente = ponta a ponta (urllib); servidor = tempo dentro do /api/busca; o resto é serialização JSON + HTTP.

| id | consulta | total | resultados | cliente ms | ranqueamento ms | trechos ms | servidor ms | serialização + HTTP ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| q01 | CVE-2021-44228 | 6 | 6 | 12.6 | 0.1 | 10.1 | 10.3 | 2.0 |
| q02 | MS17-010 | 5 | 5 | 5.3 | 0.1 | 2.9 | 3.2 | 2.1 |
| q03 | CWE-79 | 809 | 10 | 19.1 | 2.3 | 13.9 | 16.5 | 2.5 |
| q04 | SA-CORE-2018-002 | 7 | 7 | 7.7 | 0.1 | 5.6 | 5.8 | 1.9 |
| q05 | sql injection wordpress plugin | 18291 | 10 | 157.6 | 141.2 | 2.4 | 152.9 | 3.2 |
| q06 | remote code execution apache struts | 42772 | 10 | 239.5 | 224.0 | 2.5 | 236.0 | 3.7 |
| q07 | cross site scripting drupal | 20032 | 10 | 134.2 | 121.5 | 4.4 | 131.3 | 2.9 |
| q08 | joomla sql injection | 16318 | 10 | 132.6 | 123.3 | 2.2 | 129.7 | 2.9 |
| q09 | buffer overflow windows smb | 19156 | 10 | 112.1 | 100.0 | 3.1 | 108.7 | 3.4 |
| q10 | openssh vulnerability | 62 | 10 | 208.5 | 199.0 | 3.2 | 205.7 | 2.7 |
| q11 | privilege escalation linux kernel | 22812 | 10 | 90.0 | 79.9 | 2.3 | 86.9 | 2.9 |
| q12 | log4j | 16 | 10 | 9.6 | 0.2 | 7.1 | 7.4 | 2.1 |
| q13 | path traversal | 16657 | 10 | 72.7 | 59.1 | 7.0 | 69.9 | 2.8 |
| q14 | java deserialization | 2271 | 10 | 12.8 | 7.7 | 2.3 | 10.5 | 2.3 |
| q15 | denial of service | 11132 | 10 | 60.1 | 51.9 | 2.5 | 57.2 | 2.8 |
| q16 | csrf token bypass | 11959 | 10 | 59.4 | 43.1 | 10.6 | 56.3 | 2.9 |
| q17 | use after free | 25756 | 10 | 104.7 | 88.2 | 5.9 | 101.3 | 3.1 |
| q18 | strcpy stack overflow | 8378 | 10 | 51.0 | 39.4 | 6.2 | 48.3 | 2.5 |
| q19 | codigo:shellcode | 2983 | 10 | 19.9 | 8.3 | 7.2 | 17.5 | 2.2 |
| q20 | codigo:system | 10048 | 10 | 30.3 | 23.4 | 3.1 | 28.1 | 2.1 |
