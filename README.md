# VulnSearch — coletor

Coletor de páginas sobre vulnerabilidades de *software* e *hardware*, primeira
etapa do **VulnSearch**, um mecanismo de busca vertical desenvolvido no trabalho
da disciplina de Recuperação da Informação na Web e Redes Sociais (PUC Minas).

A coleta usa o [Katana](https://github.com/projectdiscovery/katana) e scripts
Python (somente biblioteca padrão) que implementam as políticas de boas maneiras
(`robots.txt`, *Crawl-delay*, limite de requisições por servidor) e a seleção de
documentos.

## Resultado da coleta

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

## Download do corpus

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

## Como funciona

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

## Como executar

### Instalação

1. **Python 3.8+**: não precisa instalar pacotes.
2. **Katana**: baixe o `.zip` do seu sistema na página de
   [releases](https://github.com/projectdiscovery/katana/releases) e extraia o
   executável nesta pasta ou em uma pasta do `PATH`. Se tiver Go instalado:
   `go install github.com/projectdiscovery/katana/cmd/katana@latest`.
3. Edite `CONTATO` no início de `coletar.py` com um e-mail de contato. Ele vai no
   *User-Agent*, para que os administradores dos sites saibam quem está coletando.

### Teste rápido (~5 minutos)

```bash
python coletar.py --teste
python processar.py "teste_*.jsonl"
```

O teste coleta no máximo 50 páginas por site. Para testar um site só:
`python coletar.py --teste --sites ghsa`.

### Coleta completa

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

### Interrupções

- **Ctrl+C**: o Katana grava um arquivo de retomada para cada site, e o resumo
  mostra o comando para continuar (`python coletar.py --sites <site> --retomar <arquivo>`).
- **Queda de energia ou processo encerrado à força**: rode `python retomar.py`.
  Ele lê os arquivos já coletados, mostra o progresso de cada site e grava em
  `retomada.json` só o que falta. Depois, `python coletar.py --retomada` continua
  a coleta em arquivos novos.

Cada execução grava arquivos próprios (`coleta_<site>_1.jsonl`, `_2`, ...), porque
o Katana sobrescreve o arquivo de saída. As páginas coletadas mais de uma vez são
removidas pelo `processar.py`.

## Adicionar um site

Crie um perfil em `SITES` (`sites.py`), seguindo os comentários do arquivo.
Antes, verifique se a listagem do site é HTML estático (links no código-fonte)
ou montada por JavaScript. No modo padrão, o Katana não enxerga *links* gerados
por JavaScript. Rode `python coletar.py --teste --sites <novo>` e confira as URLs
antes da coleta completa.

Sites avaliados e **não** incluídos: NVD e CVE.org (listagens montadas por JavaScript),
CVE Details e VulDB (bloqueiam acesso automatizado), VulnDB (conteúdo atrás de *login*),
WPScan (listagem não existe mais), MITRE ATT&CK e anúncios do WordPress (não
documentam vulnerabilidades).
