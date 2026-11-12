Seleção do top-10: min-heap de tamanho k (O(N log k), slides 07-20 a 07-36) × ordenar todos os candidatos (O(N log N)). BM25 com IDF log(1 + ·), para que todos os candidatos tenham escore > 0. Mediana de 5 execuções; os dois dão o mesmo top-k.

| consulta | candidatos (N) | min-heap ms | sorted ms | heapq.nlargest ms | sorted / min-heap |
|---|---:|---:|---:|---:|---:|
| exploit | 50304 | 5.57 | 20.01 | 5.79 | 3.60 |
| vulnerability | 59469 | 6.58 | 24.01 | 6.91 | 3.65 |
| cve | 62311 | 6.91 | 23.05 | 7.38 | 3.34 |
| remote code execution | 42142 | 4.67 | 17.56 | 4.98 | 3.76 |
| sql injection | 15623 | 1.72 | 5.74 | 1.85 | 3.34 |
