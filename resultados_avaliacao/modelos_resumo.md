Média das 20 consultas. 'top-10 julgado' = fração do top-10 que está nos julgamentos; documento não julgado conta como não relevante.

| modelo | formou o pool | P@10 | MAP | nDCG@10 | top-10 julgado | p (permutação, nDCG@10 × BM25F) |
|---|---:|---:|---:|---:|---:|---:|
| jaccard | não | 0.3150 | 0.2906 | 0.3746 | 0.3750 | 0.0000 |
| tfidf | sim | 0.8650 | 0.6635 | 0.8535 | 1.0000 | 0.4050 |
| vetorial | sim | 0.8800 | 0.6168 | 0.8468 | 1.0000 | 0.0429 |
| bm1 | não | 0.4400 | 0.4250 | 0.4790 | 0.5200 | 0.0000 |
| bm15 | não | 0.7500 | 0.6413 | 0.8348 | 0.8650 | 0.2777 |
| bm11 | não | 0.7500 | 0.6015 | 0.7957 | 0.8400 | 0.0339 |
| bm25 | sim | 0.8800 | 0.6619 | 0.9129 | 1.0000 | 0.9053 |
| bm25f | sim | 0.8650 | 0.6492 | 0.9083 | 1.0000 | — |
