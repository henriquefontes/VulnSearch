# VulnSearch — contrato da API (backend da interface Web)

Servidor: `python servidor.py` (padrão `http://127.0.0.1:8000`). A documentação interativa,
gerada automaticamente, fica em **`/docs`**. Respostas reais de cada rota estão em
[`exemplos_api/`](exemplos_api/), cada arquivo com a requisição, o status e a resposta.

**Regras gerais**

- Todas as rotas são `GET` e respondem **JSON em UTF-8**.
- Erros: `{"erro": "mensagem em português"}`, com status **400** (parâmetro inválido),
  **404** (documento ou rota inexistente) ou **500** (erro interno; o detalhe fica só no log
  do servidor).
- **O servidor nunca devolve HTML.** Títulos e trechos são listas de **segmentos**
  `{"texto": str, "destaque": bool}`. O frontend deve escapar `texto` e envolver em `<mark>`
  só os segmentos com `destaque: true`. O texto vem do documento original e **pode conter
  `<`, `>` e `&`** (exploits de XSS, código): nunca use `innerHTML` com ele sem escapar.
- CORS liberado só para as origens configuradas (padrão `http://localhost:5173` e
  `http://127.0.0.1:5500`; mude com `--cors`). Quem usa a página servida pelo próprio
  servidor (`/`) não precisa de CORS.

---

## `GET /api/busca`

| Parâmetro | Tipo | Padrão | Observação |
|---|---|---|---|
| `q` | texto | (obrigatório) | 1 a 200 caracteres. Sintaxe: palavras soltas, `"frase exata"`, `-termo` ou `NOT termo` (exclui), `codigo:termo` (só no código). Mais de 32 palavras: usa as 32 primeiras e avisa |
| `modelo` | texto | `bm25f` | `jaccard`, `tfidf`, `vetorial`, `bm1`, `bm15`, `bm11`, `bm25`, `bm25f` |
| `pagina` | inteiro | 1 | ≥ 1 |
| `por_pagina` | inteiro | 10 | 1 a 50 |
| `site` | texto, pode repetir | — | `www.exploit-db.com`, `github.com`, `www.rapid7.com`, `cwe.mitre.org`, `www.drupal.org`, `developer.joomla.org` (ver `/api/sites`) |
| `cve` | texto, pode repetir | — | `CVE-2021-44228` (maiúsculas ou minúsculas) |
| `cwe` | texto, pode repetir | — | `CWE-79` (maiúsculas ou minúsculas) |
| `k1` | número | 1,2 | (0, 10]. Família BM (bm15, bm11, bm25, bm25f) |
| `b` | número | 0,75 | [0, 1]. bm25; no bm25f vale para os três campos |
| `peso_titulo` | número | 2 | [0, 100]. Só bm25f |
| `peso_codigo` | número | 1 | [0, 100]. Peso do campo código no bm25f; α do código nos demais modelos |
| `explicar` | `true`/`false` | `false` | Inclui as parcelas do escore de cada resultado |

Parâmetros que o modelo não usa são ignorados (não dão erro).

**Filtros**: dentro de um mesmo tipo, união (`site=a&site=b` = a **ou** b); entre tipos,
interseção (`site=a&cve=X` = a **e** X). Os filtros são aplicados **antes** do top-k, então
toda página vem cheia enquanto houver resultados.

### Resposta

```json
{
  "consulta": "sql injection wordpress",
  "modelo": "bm25f",
  "parametros": {"k1": 1.2, "b": 0.75, "peso_titulo": 2.0, "peso_codigo": 1.0},
  "total": 17143,
  "pagina": 1, "por_pagina": 10, "paginas": 50,
  "tempo_ms": {"ranqueamento": 116.15, "trechos": 5.67, "total": 127.28},
  "cache": false,
  "avisos": [],
  "filtros": {"site": [], "cve": [], "cwe": []},
  "facetas": {"sites": {"www.exploit-db.com": 12680, "github.com": 2491, "www.rapid7.com": 1560,
                        "cwe.mitre.org": 307, "www.drupal.org": 73, "developer.joomla.org": 32}},
  "resultados": [
    {
      "posicao": 1,
      "id": 6579,
      "url": "https://www.exploit-db.com/exploits/17465",
      "site": "www.exploit-db.com",
      "titulo": [{"texto": "WordPress", "destaque": true},
                 {"texto": " Core 3.1.3 - ", "destaque": false},
                 {"texto": "SQL Injection", "destaque": true}],
      "escore": 18.044772,
      "trecho": [{"texto": "WordPress", "destaque": true}, {"texto": " Core 3.1.3 - ", "destaque": false},
                 {"texto": "SQL Injection", "destaque": true},
                 {"texto": " EDB-ID: 17465 CVE: EDB Verified: Author: SEC Consult Type: webapps …", "destaque": false}],
      "trecho_codigo": [{"texto": "              title: Multiple ", "destaque": false},
                        {"texto": "SQL Injection", "destaque": true},
                        {"texto": " Vulnerabilities\n            product: ", "destaque": false},
                        {"texto": "WordPress", "destaque": true}, {"texto": "\n …", "destaque": false}],
      "cves": [],
      "cwes": [],
      "explicacao": null
    }
  ]
}
```

(Resumido; a resposta completa está em `exemplos_api/busca.json`.)

| Campo | Significado |
|---|---|
| `parametros` | Parâmetros **efetivos** do modelo (os enviados ou os padrões); só os que o modelo usa |
| `total` | Documentos com escore > 0 depois de **todos** os filtros (frase, negação, site, cve, cwe) |
| `paginas` | ⌈min(`total`, 500) / `por_pagina`⌉: a paginação vai até o 500º resultado |
| `tempo_ms` | Tempo no servidor: ranqueamento, geração dos trechos e total (sem a serialização e a rede) |
| `cache` | `true` quando o ranqueamento veio do cache (mesma consulta, modelo e parâmetros; ex.: página 2 ou outro filtro) |
| `avisos` | Lista de textos para mostrar ao usuário (abaixo) |
| `filtros` | Os filtros aplicados, normalizados (CVE/CWE em maiúsculas) |
| `facetas.sites` | Nº de resultados por site **sem o filtro de site** (mas com cve/cwe), em ordem decrescente: serve para "exploit-db (12680) · github (2491)…". Com `site=x`, `total` = `facetas.sites[x]` |
| `resultados[].posicao` | Posição global (página 2 começa em 11) |
| `resultados[].id` | Id do documento (para `/api/documento/{id}`) |
| `resultados[].titulo` | Título completo, em segmentos com destaque |
| `resultados[].escore` | Escore do modelo (escalas diferentes entre modelos; só serve para ordenar) |
| `resultados[].trecho` | ~220 caracteres em volta dos termos (uma ou duas janelas separadas por ` … `); espaços e quebras de linha colapsados. Sem casamento: início do texto, sem destaque |
| `resultados[].trecho_codigo` | Até 5 linhas do código em volta do primeiro casamento com um termo de código, **com `\n`** (use `white-space: pre` ou `<pre>`); cada linha cortada em 120 caracteres com `…`. `null` quando a consulta não casou no código |
| `resultados[].cves`, `cwes` | Identificadores encontrados na página (ordenados) |
| `resultados[].explicacao` | `null`, ou (com `explicar=true`) lista de parcelas do escore, uma por termo/palavra; as chaves dependem do modelo (ex.: bm25f: `palavra`, `campos`, `tf~`, `n`, `idf`, `parcela`; algumas chaves têm símbolos, como `"len/avg"`, então use `obj["len/avg"]`) |

**Avisos possíveis** (`avisos`), todos com status 200:

- `termo não encontrado: xyz`: a palavra não existe no índice (ignorada);
- `recurso do IDF: todas as palavras têm n > N/2 ...`: consulta só com termos muito comuns
  (`vulnerability`, `exploit`, `cve`); os escores usam outra variante do IDF;
- `A consulta não tem termos indexáveis (só stopwords ou sinais).`: `total` 0;
- `A consulta tem N palavras; só as 32 primeiras foram usadas.`;
- `Página além do limite de 500 resultados.` / `Página P além da última (U).`: `resultados` vazio.

**Erros 400** (exemplos): `q` vazio ou ausente, mais de 200 caracteres, modelo
desconhecido (a mensagem lista os válidos), `pagina` < 1, `por_pagina` fora de 1–50, número
inválido, site desconhecido, CVE/CWE mal formado, `k1`/`b`/pesos fora do intervalo.

```json
{"erro": "O parâmetro 'pagina' deve ser ≥ 1."}
```

### Exemplos de requisição

| Requisição | Arquivo |
|---|---|
| `/api/busca?q=sql injection wordpress` | `busca.json` |
| `/api/busca?q=sql injection wordpress&pagina=2` | `busca_pagina2.json` (`cache: true`) |
| `/api/busca?q=log4j&site=www.exploit-db.com&cve=CVE-2021-44228` | `busca_filtro.json` |
| `/api/busca?q=codigo:strcpy&por_pagina=3` | `busca_codigo.json` (`trecho_codigo`) |
| `/api/busca?q="denial of service" -wordpress&por_pagina=3` | `busca_frase.json` |
| `/api/busca?q=buffer overflow&modelo=bm25&k1=1.5&b=0.5&por_pagina=3` | `busca_modelo.json` |
| `/api/busca?q=CVE-2021-44228&explicar=true&por_pagina=2` | `busca_explicar.json` |
| `/api/busca?q=vulnerability&por_pagina=3` | `busca_recurso_idf.json` (aviso) |
| `/api/busca?q=the of and` | `busca_vazia.json` (aviso, `total: 0`) |
| `/api/busca?q=x&pagina=0` | `erro_400.json` |

Na URL, codifique espaços e aspas (`encodeURIComponent` no JS):
`/api/busca?q=%22denial%20of%20service%22%20-wordpress`.

---

## `GET /api/documento/{id}`

Documento completo, para uma página de detalhes ou uma visualização "em cache".

```json
{
  "id": 38165,
  "url": "https://www.exploit-db.com/exploits/50592",
  "site": "www.exploit-db.com", "nome_site": "Exploit Database",
  "titulo": "Apache Log4j 2 - Remote Code Execution (RCE)",
  "descricao": "", "palavras_chave": "Java,remote,CVE-2021-44228",
  "texto": "Apache Log4j 2 - Remote Code Execution (RCE)\nEDB-ID:\n50592\n...",
  "codigo": "# Exploit Title: Apache Log4j 2 - Remote Code Execution (RCE)\n...",
  "codigo_truncado": false, "tamanho_codigo": 3532,
  "cves": ["CVE-2021-44228"], "cwes": [],
  "n_termos_texto": 41, "n_termos_codigo": 439
}
```

- `texto` e `codigo` vêm sem destaque e preservam as quebras de linha.
- `codigo` é cortado em 20.000 caracteres; nesse caso, `codigo_truncado: true`, e
  `tamanho_codigo` informa o tamanho original.
- Id inexistente: **404** `{"erro": "O documento 999999 não existe."}`; id não numérico:
  400.

Arquivos: `documento.json`, `erro_404.json`.

## `GET /api/modelos`

```json
{"padrao": "bm25f", "modelos": [
  {"id": "bm25f", "nome": "BM25F", "aula": "09",
   "descricao": "BM25 com campos: título, corpo e código, com pesos por campo. Padrão.",
   "parametros": {"k1": 1.2, "b": 0.75, "peso_titulo": 2.0, "peso_codigo": 1.0}}, ...]}
```

`parametros` lista os parâmetros que o modelo aceita, com o valor padrão (serve para montar
o seletor de modelo e os campos de ajuste). Arquivo: `modelos.json`.

## `GET /api/sites`

```json
{"sites": [{"id": "www.exploit-db.com", "nome": "Exploit Database", "documentos": 41643}, ...]}
```

Os 6 sites do corpus, para os filtros. `id` é o valor do parâmetro `site`. Arquivo:
`sites.json`.

## `GET /api/estatisticas`

Números do índice para uma página "sobre": `documentos`, `vocabulario` (total, texto,
código), `postings`, `ocorrencias`, `indice_mb` (arquivos do índice, do ranqueamento e dos
textos), `data_indexacao`, `tempo_indexacao_s`, `medias_tamanho` e `docs_com_campo` por
campo, e `textos` (razão de compressão, documentos com CVE). Arquivo: `estatisticas.json`.

## `GET /api/saude`

```json
{"ok": true, "documentos": 64180, "carregado_em_s": 0.871, "memoria_mb": 314.4}
```

Para verificar se o servidor está no ar. `memoria_mb` é o pico de memória do processo
depois da carga.

## `GET /` e `/static/...`

Arquivos da pasta `web/`. `/` devolve `web/index.html` quando existir; senão, a página de
teste `web/teste.html`. Arquivos auxiliares (CSS, JS, imagens) ficam em `web/` e são
acessados como `/static/arquivo.css`.
