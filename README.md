# VulnSearch

Mecanismo de busca vertical sobre vulnerabilidades de *software* e *hardware*,
desenvolvido no trabalho da disciplina de Recuperação da Informação na Web e Redes
Sociais (PUC Minas). O projeto é feito em etapas:

1. **Coleta** (concluída): coletor sobre o Katana; ver [Etapa 1](#etapa-1--coleta).
2. **Representação e indexação** (concluída): limpeza do HTML, análise léxica e índice
   invertido; ver [Etapa 2](#etapa-2--indexação).
3. **Ranqueamento** (atual): Jaccard, TF-IDF, modelo vetorial, BM1/BM15/BM11/BM25 e
   BM25F; ver [Etapa 3](#etapa-3--ranqueamento).
4. Interface de busca e avaliação (próximas etapas).

## Etapa 3 — ranqueamento

Ordena os resultados por relevância sobre o índice da etapa 2, sem alterar o formato dele:
esta etapa só acrescenta dois arquivos em `indice/`. Os modelos são implementados no
próprio projeto, sem bibliotecas de RI. As dependências são as mesmas (`selectolax` e
`snowballstemmer`), e o `matplotlib` é opcional, só para os gráficos.

### Como executar

```
# 1. estatísticas por documento (~30 s; o indexar.py já chama no final, salvo --sem-ranking)
python preparar_ranking.py

# 2. busca ranqueada
python ranquear.py "sql injection wordpress"                 # BM25F, top 10
python ranquear.py "buffer overflow" --modelo vetorial -k 20
python ranquear.py "log4j" --modelo bm25 --k1 1.2 --b 0.75
python ranquear.py "log4j" --modelo bm25f --peso-titulo 3 --peso-codigo 0.5
python ranquear.py "CVE-2021-44228" --explicar               # parcelas de cada termo e campo
python ranquear.py --comparar "remote code execution"        # top 10 dos 8 modelos lado a lado
python ranquear.py                                           # modo interativo
python buscar.py sql injection wordpress --ranking           # booleana, ordenada pelo BM25F

# 3. testes (exemplos dos slides + consistência com o índice real, ~10 s)
python indexar.py resultados/campos.jsonl.gz --passo 30 --saida indice_teste
python testar_ranking.py                      # usa indice_teste/
python testar_ranking.py --indice indice      # teste 11 no índice completo

# 4. experimentos (~1,5 min) e gráficos
python medir_ranking.py                       # tabelas em resultados_etapa3/
python graficos.py --etapa3                   # PNG (requer matplotlib)

# 5. avaliação (julgamentos feitos pelo grupo)
python pool.py                                # julgamentos/pool_<id>.tsv, coluna 'relevante' vazia
#    preencher 'relevante' com 0, 1 ou 2 em cada pool_<id>.tsv
python avaliar.py --juntar                    # -> julgamentos/qrels.tsv
python avaliar.py                             # P@10, MAP, nDCG@10 e busca em grade
```

No PowerShell, as aspas de uma frase passada como argumento se perdem. Use o modo
interativo, em que a linha é lida como foi digitada, ou `--frase "denial of service"`.

### Modelos e parâmetros (`ranquear.py --modelo`)

| Modelo | Escore | Parâmetros |
|---|---|---|
| `jaccard` | \|q ∩ d\| / \|q ∪ d\| (conjuntos de termos) | `--peso-codigo` (α) |
| `tfidf` | Σ w_q·w_d, w = (1 + log₂ tf)·log₂(N/n), sem normalização | `--tf log\|bruto`, α |
| `vetorial` | cosseno com os esquemas 1, 2 e 3 de TF-IDF (padrão: 3) | `--esquema`, α |
| `bm1`, `bm15`, `bm11`, `bm25` | família BM (BM25 com b = 0 é o BM15; com b = 1, o BM11) | `--k1` (1,2), `--b` (0,75), `--idf`, α |
| `bm25f` (padrão) | BM25 com campos título, corpo e código | `--k1`, `--b`, `--peso-titulo` (2), `--peso-corpo` (1), `--peso-codigo` (1), `--idf` |

- Nos modelos sem campos, termos de texto e de código são dimensões separadas:
  escore = texto + α·código (`--peso-codigo`, padrão 1).
- No BM25F, título e corpo são separados pela posição: o título vem primeiro no índice, e
  `limite_titulo` marca onde ele acaba.
- O IDF da família BM, log₂((N − n + 0,5)/(n + 0,5)), fica negativo quando n > N/2
  (`cve`, `vulner`, `exploit`...). Por padrão ele é limitado a 0; `--idf log1p` usa
  log₂(1 + ·) e `--idf bruto` usa a fórmula sem correção.
- Candidatos são os documentos com ao menos um termo da consulta (união das listas). Só
  entram no resultado os que têm escore > 0.
- O top-k é escolhido com um min-heap de tamanho k (`ranqueamento.top_k`). Em caso de
  empate, vence o menor id de documento.
- Sintaxe da consulta: palavras soltas, `"frase"` (filtro por posição), `-palavra` ou
  `NOT palavra` (exclusão) e `codigo:termo` (só no código).

### Arquivos

| Arquivo | Função |
|---|---|
| `ranqueamento.py` | fórmulas (funções separadas), `top_k`, `Colecao`, `ProcessadorConsulta`, `Ranqueador` |
| `preparar_ranking.py` | limite do título e passada única sobre as ocorrências; grava as estatísticas e confere o título |
| `ranquear.py` | linha de comando: busca, `--explicar`, `--comparar`, modo interativo |
| `testar_ranking.py` | exemplos dos slides 07, 08 e 09 em índices em memória; consistência com o índice real |
| `medir_ranking.py` | custo, sobreposição entre modelos, sensibilidade de K₁/b, pesos do BM25F, α, variantes do IDF, exemplos |
| `consultas.tsv` | as 20 consultas dos experimentos (id, tipo, consulta) |
| `pool.py`, `avaliar.py` | *pooling* para os julgamentos; P@10, MAP, nDCG@10 e busca em grade |
| `julgamentos/` | `pool_<id>.tsv` (a preencher pelo grupo) e `qrels.tsv` |
| `resultados_etapa3/` | tabelas (CSV/Markdown), gráficos (PNG) e `resumo.json` |

### Arquivos novos em `indice/`

- `documentos_ranking.bin` (4,4 MB): um registro de tamanho fixo por documento
  (`<6I6d>`, little-endian, precedido do N em 4 bytes). Campos: `limite_titulo`,
  `n_titulo`, `n_corpo`, `n_codigo`, `distintos_texto`, `distintos_codigo` e
  `norma2_{texto,codigo}_e{1,2,3}` (soma dos quadrados dos pesos de cada esquema). A
  ordem das colunas está em `colecao.json`. Com `preparar_ranking.py --formato tsv`, sai
  um TSV equivalente (7,0 MB, leitura 4× mais lenta).
- `colecao.json`: N, base do log, esquemas, médias de tamanho por campo (sobre os
  documentos que têm o campo), nº de documentos com cada campo, tempos, pico de memória
  e resultado das verificações.

## Etapa 2 — indexação

### Instalação

Python 3.8+ e dois pacotes:

```bash
pip install selectolax snowballstemmer
```

O `graficos.py` precisa também do `matplotlib` (opcional: as tabelas em CSV/Markdown
saem sem ele). Não há banco de dados: o índice é um conjunto de arquivos próprios.

### Como executar

Com o `corpus.jsonl.gz` (release `coleta-v1`) nesta pasta:

```bash
python indexar.py                      # índice principal em indice/ (~4 min, ~350 MB de RAM)
python buscar.py "sql injection wordpress"
python buscar.py                       # modo interativo
```

Teste rápido, com 1 página a cada 30 (o corpus está agrupado por site, então
`--limite` sozinho pegaria só os primeiros sites):

```bash
python indexar.py --passo 30 --saida indice_teste --salvar-campos campos_teste.jsonl.gz
python verificar_indice.py campos_teste.jsonl.gz --indice indice_teste
```

Experimentos para o relatório (todas as variações, ~45 min):

```bash
python medir.py          # tabelas em resultados/*.csv e *.md
python graficos.py       # gráficos em resultados/*.png
```

`medir.py --passo 50` roda tudo numa amostra em poucos minutos.

### Sintaxe da busca (`buscar.py`)

| Consulta | Significado |
|---|---|
| `sql injection` | AND implícito |
| `wordpress OR joomla` | OR entre termos vizinhos |
| `xss -wordpress` ou `xss NOT wordpress` | exclusão |
| `"denial of service"` | frase (usa as posições) |
| `codigo:strcpy` | só no código dos *exploits*/exemplos |
| `CVE-2021-44228`, `GHSA-...`, `CWE-79`, `2.4.1` | identificadores e versões inteiros |

A busca é booleana e serve para verificar o índice; o ranqueamento é a próxima etapa.

### Arquivos

| Arquivo | Função |
|---|---|
| `extrair.py` | Limpeza: HTML → campos (título, descrição, palavras-chave, texto, código), com um perfil por site |
| `lexico.py` | Análise léxica: tokenização, acentos, caixa, stopwords, stemming; regras próprias para o código |
| `stopwords_en.txt` | 150 stopwords em inglês, em ordem de frequência |
| `indexar.py` | Construção do índice por ordenação externa (blocos + *k-way merge*) |
| `indice.py` | Formato do índice: *variable byte*, leitura das listas, medição de memória |
| `buscar.py` | Busca booleana (interseção de listas ordenadas, frases) |
| `verificar_indice.py` | Confere as listas gravadas contra um índice montado em memória |
| `etapas.py` | Tabela no modelo Reuters-RCV1 (vocabulário/ocorrências após cada etapa) |
| `medir.py` | Experimentos: tempo, espaço, Heaps e variações dos hiperparâmetros |
| `graficos.py` | Gráficos PNG a partir de `resultados/` |
| `amostras_extrator.py` | Separa páginas de amostra de cada site, usadas para calibrar o `extrair.py` |

### Como funciona

```
corpus.jsonl.gz ─► leitura em ─► extrair.py ─► lexico.py ─► inversão em blocos ─► k-way merge ─► indice/
                   streaming     (campos)      (termos e    (até --bloco MB;      (heapq.merge)
                                               posições)    ordena e grava)
```

- **Campos**: título, descrição (meta), palavras-chave (meta) e texto formam o texto
  indexado; o código (*exploits*, exemplos das CWEs, blocos `<pre>`) vai para um campo
  separado, gravado com prefixo `c:` no vocabulário (`c:strcpy`).
- **Análise léxica do texto**: minúsculas, sem acentos e pontuação; hífen separa palavras
  (`use-after-free` vira três termos, e a busca por frase os reencontra); 150 stopwords;
  stemming Snowball (inglês). **Números não são removidos** e identificadores do domínio
  ficam inteiros: CVE, GHSA, CWE, SA-CORE/SA-CONTRIB, MS17-010, versões (`2.4.1`) e
  pacotes (`@scope/nome`).
- **Código**: sem stopwords e sem *stemming*; tokens de 2 a 24 caracteres (`--tam-max-codigo`),
  para que *shellcode*, hexadecimais e base64 não inflem o vocabulário.
- **Granularidade**: documento com posições (permite frase); as posições contam também as
  stopwords. Variações: sem posições e trechos de N tokens (`--granularidade trecho`).
- **Construção**: as ocorrências são acumuladas em memória, já codificadas, até o bloco
  atingir `--bloco` MB; então os termos são ordenados e o bloco vai para o disco. No final,
  os blocos são intercalados (*k-way merge*) e apagados.
- **Compressão**: diferenças (*gaps*) entre documentos e entre posições + *variable byte*.
  `--sem-compressao` grava inteiros de 4 bytes.

### Formato do índice (`indice/`)

| Arquivo | Conteúdo |
|---|---|
| `vocabulario.tsv` | `termo, df, cf, offset, bytes` (carregado inteiro na memória) |
| `ocorrencias.bin` | listas ⟨doc, tf, pos₁…pos_tf⟩ de cada termo, doc crescente |
| `documentos.tsv` | `id, url, site, nº de termos do texto, nº de termos do código, título` |
| `trechos.tsv` | só na granularidade por trecho: trecho → página |
| `estatisticas.json` | parâmetros, contagens, tempo por etapa, pico de memória, tamanhos |
| `heaps.csv` | (tokens, vocabulário) a cada 250 páginas |

## Etapa 1 — coleta

A coleta usa o [Katana](https://github.com/projectdiscovery/katana) e scripts
Python (somente biblioteca padrão) que implementam as políticas de boas maneiras
(`robots.txt`, *Crawl-delay*, limite de requisições por servidor) e a seleção de
documentos.

### Resultado da coleta

**64.180 páginas** de 6 sites especializados, com 11,1 GB de HTML (1,4 GB compactado).
A coleta levou cerca de 6 horas.

| Site | Conteúdo | Páginas no corpus |
|---|---|---:|
| [Exploit Database](https://www.exploit-db.com) | *exploits* públicos (`/exploits/<id>`) | 41.643 |
| [GitHub Advisory Database](https://github.com/advisories) | alertas de segurança de pacotes (`GHSA-...`) | 9.990 |
| [Rapid7 Vulnerability & Exploit DB](https://www.rapid7.com/db/) | vulnerabilidades (`/db/vulnerabilities/...`) | 9.915 |
| [MITRE CWE](https://cwe.mitre.org) | tipos de fraqueza (`CWE-<n>`) | 1.375 |
| [Drupal Security Advisories](https://www.drupal.org/security) | avisos `SA-CORE` / `SA-CONTRIB` | 931 |
| [Joomla Security Centre](https://developer.joomla.org/security-centre.html) | anúncios de segurança | 326 |
| **Total** | | **64.180** |

Das 64.474 URLs distintas visitadas, 294 (0,5%) foram descartadas na seleção de
documentos (HTTP diferente de 200 ou conteúdo que não é HTML).

### Download do corpus

O corpus está na [release **coleta-v1**](../../releases/latest), e não no Git,
porque o GitHub não aceita arquivos acima de 100 MiB no repositório.

| Arquivo | Conteúdo |
|---|---|
| `corpus.jsonl.gz` | Corpus final, já filtrado: um registro por página |
| `coleta_<site>_<n>.jsonl.gz` | Saída bruta do Katana de cada execução (opcional, para reproduzir o pós-processamento) |

Cada linha do `corpus.jsonl.gz` é um objeto JSON:

```json
{"url": "https://www.exploit-db.com/exploits/12345",
 "status": 200,
 "headers": {"content_type": "text/html; charset=UTF-8", "...": "..."},
 "html": "<!DOCTYPE html>..."}
```

Leitura em Python, linha a linha, sem carregar o arquivo inteiro na memória:

```python
import gzip, json

with gzip.open("corpus.jsonl.gz", "rt", encoding="utf-8") as f:
    for linha in f:
        pagina = json.loads(linha)
        print(pagina["url"], len(pagina["html"]))
```

### Como funciona

```
sites.py ──► robots_escopo.py ──► Katana (um processo por site, em paralelo) ──► coleta_<site>_<n>.jsonl ──► processar.py ──► corpus.jsonl.gz
             (robots.txt →                                                        (URL, status,              (seleção de
              exclusões e                                                          cabeçalhos, HTML)          documentos)
              Crawl-delay)
```

| Arquivo | Função |
|---|---|
| `sites.py` | Perfil de coleta de cada site: sementes, profundidade, escopo, exclusões e limites |
| `robots_escopo.py` | Lê o `robots.txt` de cada site e gera as exclusões e o intervalo entre requisições |
| `coletar.py` | Executa a coleta: um processo do Katana por site, em paralelo, com progresso no terminal |
| `retomar.py` | Descobre onde uma coleta interrompida parou e monta o plano para continuar |
| `processar.py` | Seleção de documentos e estatísticas; gera `corpus.jsonl.gz` |

Principais decisões:

- **Coletor vertical**: só segue *links* dentro do domínio de cada site, e só grava
  as páginas de detalhe (alertas, vulnerabilidades, *exploits*). As páginas de listagem
  servem apenas para descobrir *links*.
- **Busca em largura.** Nos sites com listagem em HTML estático, as sementes são as
  páginas da listagem, com profundidade 1. No Exploit Database, cada *exploit* só
  aponta para o anterior e o seguinte; por isso, as sementes ficam a cada 500
  identificadores, com profundidade 500.
- **Boas maneiras**: *User-Agent* próprio (`VulnSearchBot/1.0`) e 1 ou 2 requisições
  por segundo por site. As regras `Disallow` do `robots.txt` são convertidas em
  exclusões, porque o Katana não as aplica, e o *Crawl-delay* é respeitado.
- **Seleção de documentos** (`processar.py`): mantém só respostas HTTP 200 em HTML e
  remove *soft*-404 e páginas repetidas (pela URL e pelo *hash* do conteúdo).

### Como executar

#### Instalação

1. **Python 3.8+**: não precisa instalar pacotes.
2. **Katana**: baixe o `.zip` do seu sistema na página de
   [releases](https://github.com/projectdiscovery/katana/releases) e extraia o
   executável nesta pasta ou em uma pasta do `PATH`. Se tiver Go instalado:
   `go install github.com/projectdiscovery/katana/cmd/katana@latest`.
3. Edite `CONTATO` no início de `coletar.py` com um e-mail de contato. Ele vai no
   *User-Agent*, para que os administradores dos sites saibam quem está coletando.

#### Teste rápido (~5 minutos)

```bash
python coletar.py --teste
python processar.py "teste_*.jsonl"
```

O teste coleta no máximo 50 páginas por site. Para testar um site só:
`python coletar.py --teste --sites ghsa`.

#### Coleta completa

```bash
python coletar.py
python processar.py "coleta_*.jsonl*"
```

- Reserve uns **15 GB** livres para os arquivos brutos.
- Para coletar só alguns sites: `python coletar.py --sites ghsa,rapid7`.
- Antes de rodar, ajuste `EXPLOITDB_ULTIMO_ID` em `sites.py` para o *exploit*
  mais recente do site.
- Em um servidor remoto, rode dentro de `screen` ou `tmux`, para que a coleta
  continue se a conexão SSH cair.

#### Interrupções

- **Ctrl+C**: o Katana grava um arquivo de retomada para cada site, e o resumo
  mostra o comando para continuar (`python coletar.py --sites <site> --retomar <arquivo>`).
- **Queda de energia ou processo encerrado à força**: rode `python retomar.py`.
  Ele lê os arquivos já coletados, mostra o progresso de cada site e grava em
  `retomada.json` só o que falta. Depois, `python coletar.py --retomada` continua
  a coleta em arquivos novos.

Cada execução grava arquivos próprios (`coleta_<site>_1.jsonl`, `_2`, ...), porque
o Katana sobrescreve o arquivo de saída. As páginas coletadas mais de uma vez são
removidas pelo `processar.py`.

### Adicionar um site

Crie um perfil em `SITES` (`sites.py`), seguindo os comentários do arquivo.
Antes, verifique se a listagem do site é HTML estático (links no código-fonte)
ou montada por JavaScript. No modo padrão, o Katana não enxerga *links* gerados
por JavaScript. Rode `python coletar.py --teste --sites <novo>` e confira as URLs
antes da coleta completa.

Sites avaliados e **não** incluídos: NVD e CVE.org (listagens montadas por JavaScript),
CVE Details e VulDB (bloqueiam acesso automatizado), VulnDB (conteúdo atrás de *login*),
WPScan (listagem não existe mais), MITRE ATT&CK e anúncios do WordPress (não
documentam vulnerabilidades).
