Tempo por etapa do índice principal (64180 páginas; pico de memória 332 MB; 5 blocos de 64 MB).

| etapa | tempo (s) | % |
|---|---:|---:|
| leitura (descompactação + JSON) | 52.9 | 24.6 |
| extração do HTML | 99.3 | 46.2 |
| análise léxica | 34.5 | 16.1 |
| inversão em memória | 23.9 | 11.1 |
| gravação dos blocos | 1.3 | 0.6 |
| intercalação (merge) | 2.5 | 1.2 |
| outros (laço, contagens, documentos.tsv) | 0.3 | 0.1 |
| total | 214.8 | 100.0 |
