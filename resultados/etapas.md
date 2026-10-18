Efeito das etapas de pré-processamento (campos de texto, 64180 páginas). Δ% = variação em relação à linha anterior; T% = em relação à primeira linha. A última linha é o pipeline do VulnSearch, comparado à primeira.

| etapa | vocabulário | Δ% | T% | postings (sem posições) | Δ% | T% | tokens (com posições) | Δ% | T% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| sem filtro | 295197 | - | - | 6010558 | - | - | 10554280 | - | - |
| sem números | 228115 | -22.7 | -22.7 | 5531856 | -8.0 | -8.0 | 9784189 | -7.3 | -7.3 |
| minúsculas e sem acentos | 207843 | -8.9 | -29.6 | 5182091 | -6.3 | -13.8 | 9784189 | 0.0 | -7.3 |
| 30 stopwords | 207813 | -0.0 | -29.6 | 4797451 | -7.4 | -20.2 | 8117716 | -17.0 | -23.1 |
| 150 stopwords | 207695 | -0.1 | -29.6 | 4516804 | -5.8 | -24.9 | 7650175 | -5.8 | -27.5 |
| stemming | 196736 | -5.3 | -33.4 | 4215065 | -6.7 | -29.9 | 7650175 | 0.0 | -27.5 |
| VulnSearch (com números, 150 stopwords, stemming) | 261881 | -11.3 | -11.3 | 4689042 | -22.0 | -22.0 | 8420197 | -20.2 | -20.2 |
