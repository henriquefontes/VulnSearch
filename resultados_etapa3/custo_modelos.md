Custo por modelo nas 20 consultas de consultas.tsv (5 repetições cada, cache do disco aquecido; inclui análise da consulta, leitura das listas, acumulação e top-k).

| modelo | ms média | ms mediana (das medianas) | ms máx. | candidatos (média) | postings lidos (média) |
|---|---:|---:|---:|---:|---:|
| jaccard | 37.67 | 27.46 | 136.74 | 14444 | 25690 |
| tfidf | 44.47 | 31.64 | 149.62 | 14444 | 25690 |
| vetorial | 46.02 | 32.73 | 159.89 | 14444 | 25690 |
| bm1 | 37.77 | 26.09 | 123.42 | 14444 | 25690 |
| bm15 | 40.12 | 29.00 | 132.36 | 14444 | 25690 |
| bm11 | 41.27 | 29.24 | 136.28 | 14444 | 25690 |
| bm25 | 43.00 | 29.53 | 152.19 | 14444 | 25690 |
| bm25f | 62.97 | 45.64 | 219.13 | 14444 | 25690 |
