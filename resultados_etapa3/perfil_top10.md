Site e tamanho dos documentos no top-10 de cada modelo (todas as consultas somadas). Hipótese (slide 08-38): sem normalização (TF-IDF, BM15) os documentos longos são favorecidos.

| modelo | documentos | % exploit-db | % github | % rapid7 | % cwe | % drupal | % joomla | termos de texto (média) | termos de código (média) | total (média) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| jaccard | 188 | 70 | 19 | 3 | 5 | 3 | 1 | 159 | 470 | 629 |
| tfidf | 188 | 70 | 15 | 0 | 12 | 3 | 0 | 1247 | 2030 | 3277 |
| vetorial | 188 | 76 | 4 | 14 | 3 | 3 | 1 | 99 | 529 | 628 |
| bm1 | 188 | 79 | 8 | 0 | 10 | 3 | 0 | 208 | 852 | 1060 |
| bm15 | 188 | 77 | 16 | 0 | 5 | 3 | 0 | 227 | 1728 | 1956 |
| bm11 | 188 | 84 | 10 | 0 | 4 | 3 | 0 | 117 | 653 | 771 |
| bm25 | 188 | 86 | 10 | 0 | 2 | 3 | 0 | 108 | 723 | 832 |
| bm25f | 188 | 82 | 10 | 0 | 3 | 5 | 0 | 143 | 734 | 878 |
| (coleção) | 64180 | 65 | 16 | 15 | 2 | 1 | 1 | 131 | 317 | 448 |
