Lei de Heaps (V = K·n^b), ajustada em log-log; n = termos indexados (após stopwords e stemming). Na ordem do corpus as páginas vêm agrupadas por site e o vocabulário cresce aos saltos; a ordem aleatória (semente 42) é a estimativa representativa.

| ordem das páginas | vocabulário de | K | b | R² | pontos | n final | V final |
|---|---:|---:|---:|---:|---:|---:|---:|
| aleatória | texto | 1.19 | 0.772 | 0.9985 | 257 | 8420197 | 261881 |
| aleatória | texto + código | 0.93 | 0.799 | 0.9898 | 257 | 28740582 | 821068 |
| do corpus (agrupada por site) | texto | 0.02 | 1.045 | 0.8860 | 257 | 8420197 | 261881 |
| do corpus (agrupada por site) | texto + código | 0.03 | 1.010 | 0.9888 | 257 | 28740582 | 821068 |
