# sites.py - perfis de coleta, um por site
#
# Cada site tem uma estrutura de links própria, então sementes, profundidade,
# escopo e limites são definidos por site. O coletar.py executa um processo do
# Katana por site, em paralelo: assim o intervalo entre requisições de um site
# não atrasa os outros (como as filas por servidor da fila de Mercator).
#
# Campos de cada perfil:
#   sementes               função que devolve a lista de URLs iniciais
#   profundidade           -depth
#   max_paginas            -max-domain-pages (conta também as páginas de listagem)
#   requisicoes_por_segundo -host-rate-limit (se o robots.txt declarar Crawl-delay,
#                          o coletar.py faz uma requisição por vez com esse intervalo)
#   ignorar_parametros     -ignore-query-params
#   sitemap                -known-files sitemapxml (exige profundidade >= 3)
#   escopo                 regex de URLs que podem ser coletadas (-crawl-scope);
#                          vazio = todo o domínio da semente. As sementes são
#                          sempre visitadas, mas só entram na saída se casarem.
#   exclusoes              regex de URLs que não devem ser coletadas, além das
#                          geradas a partir do robots.txt (-crawl-out-scope)
#   teste                  valores usados com --teste
#
# Atenção: o Katana separa as regex também por vírgula; não use vírgulas nelas.

# --- Exploit Database ------------------------------------------------------
# A listagem da página inicial é carregada por JavaScript, e cada página
# /exploits/<id> aponta apenas para o exploit anterior e o seguinte. Sementes
# a cada PASSO ids com profundidade >= PASSO: cada cadeia alcança a semente
# vizinha, mesmo que uma semente caia em um id inexistente (ex.: 501 = 404).
EXPLOITDB_ULTIMO_ID = 53000  # confira o exploit mais recente no site
EXPLOITDB_PASSO = 500


def _sementes_exploitdb():
    return ["https://www.exploit-db.com/"] + [
        f"https://www.exploit-db.com/exploits/{i}"
        for i in range(1, EXPLOITDB_ULTIMO_ID + 1, EXPLOITDB_PASSO)]


# --- GitHub Advisory Database ------------------------------------------------
# A listagem é HTML estático: 30 alertas por página, paginação até a página
# 400 (cerca de 12 mil alertas). Cada alerta (/advisories/GHSA-...) traz
# descrição, severidade, pacotes afetados, CVE e CWE no HTML. As páginas de
# listagem são as sementes; com profundidade 1 o coletor visita os alertas e
# não segue os filtros (?query=...) que aparecem dentro deles.
GHSA_PAGINAS = 400


def _sementes_ghsa():
    return [f"https://github.com/advisories?page={p}"
            for p in range(1, GHSA_PAGINAS + 1)]


# --- Rapid7 Vulnerability & Exploit Database ----------------------------------
# Listagem estática com 25 vulnerabilidades por página (~400 mil no total).
# Coletamos as primeiras RAPID7_PAGINAS páginas da listagem.
RAPID7_PAGINAS = 400


def _sementes_rapid7():
    return [f"https://www.rapid7.com/db/?type=nexpose&page={p}"
            for p in range(1, RAPID7_PAGINAS + 1)]


# --- MITRE CWE -----------------------------------------------------------------
# A página com a lista completa (/data/slices/2000.html) passa de 30 MB, acima
# do limite de resposta do Katana (4 MB). As sementes são as páginas das visões
# principais (pesquisa, desenvolvimento de software e hardware); cada CWE
# aponta para as fraquezas relacionadas (pai, filhas), e o coletor percorre a
# hierarquia até a profundidade máxima.
def _sementes_cwe():
    return [f"https://cwe.mitre.org/data/definitions/{v}.html"
            for v in (1000, 699, 1194)]


# --- Drupal Security Advisories --------------------------------------------------
# Listagem estática (?page=0 a 42), ~43 avisos por página. O robots.txt pede
# Crawl-delay de 10 s, aplicado automaticamente por robots_escopo.py.
DRUPAL_PAGINAS = 43


def _sementes_drupal():
    return [f"https://www.drupal.org/security?page={p}" for p in range(DRUPAL_PAGINAS)]


# --- Joomla Security Centre ------------------------------------------------------
# Listagem estática, 25 anúncios por página, 14 páginas (?start=0, 25, ...).
JOOMLA_PAGINAS = 14


def _sementes_joomla():
    return [f"https://developer.joomla.org/security-centre.html?start={25 * p}"
            for p in range(JOOMLA_PAGINAS)]


# Sites avaliados e NÃO incluídos (links das páginas de detalhe não aparecem
# no HTML ou acesso automatizado bloqueado):
#   nvd.nist.gov      listagens /vuln/full-listing montadas por JavaScript
#   cve.org           registros de CVE carregados por JavaScript
#   cvedetails.com    listagem sem links para os CVEs; robots.txt responde 403
#   wpscan.com        /vulnerabilities/ não existe mais (404); sitemap com erro
#   vulndb.cyberriskanalytics.com   base comercial, conteúdo atrás de login
#   vuldb.com         responde 403 com página "Security Check" (bloqueio anti-robô)
# Removidos por não documentarem vulnerabilidades (fora do tema do buscador):
#   attack.mitre.org  táticas e técnicas de atacantes, não vulnerabilidades
#   wordpress.org     anúncios de versão, com pouco detalhe sobre as falhas

SITES = {
    "exploitdb": {
        "sementes": _sementes_exploitdb,
        "profundidade": EXPLOITDB_PASSO,
        "max_paginas": 60000,
        "requisicoes_por_segundo": 2,
        "ignorar_parametros": True,
        "sitemap": True,
        "escopo": [],
        "exclusoes": [
            # arquivos do exploit, aplicativos vulneráveis, busca, envio, login
            r"^https?://www\.exploit-db\.com/download/",
            r"^https?://www\.exploit-db\.com/raw/",
            r"^https?://www\.exploit-db\.com/apps/",
            r"^https?://www\.exploit-db\.com/search",
            r"^https?://www\.exploit-db\.com/submit",
            r"^https?://www\.exploit-db\.com/login",
            # listagens filtradas (?author= ?type=...): mesmo HTML da inicial
            r"^https?://www\.exploit-db\.com/\?",
        ],
        "teste": {"sementes": 3, "profundidade": 5, "max_paginas": 50},
    },
    "ghsa": {
        "sementes": _sementes_ghsa,
        "profundidade": 1,
        "max_paginas": 13000,
        "requisicoes_por_segundo": 1,
        "ignorar_parametros": False,
        "sitemap": False,
        "escopo": [r"^https://github\.com/advisories/GHSA-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}$"],
        "exclusoes": [],
        "teste": {"sementes": 2, "profundidade": 1, "max_paginas": 40},
    },
    "rapid7": {
        "sementes": _sementes_rapid7,
        "profundidade": 1,
        "max_paginas": RAPID7_PAGINAS * 26,
        "requisicoes_por_segundo": 2,
        "ignorar_parametros": False,
        "sitemap": False,
        "escopo": [r"^https://www\.rapid7\.com/db/vulnerabilities/[^/?#]+/?$"],
        "exclusoes": [],
        "teste": {"sementes": 1, "profundidade": 1, "max_paginas": 20},
    },
    "cwe": {
        "sementes": _sementes_cwe,
        "profundidade": 10,
        "max_paginas": 2000,
        "requisicoes_por_segundo": 2,
        "ignorar_parametros": True,
        "sitemap": False,
        "escopo": [r"^https://cwe\.mitre\.org/data/definitions/\d+\.html$"],
        "exclusoes": [],
        "teste": {"sementes": 1, "profundidade": 2, "max_paginas": 20},
    },
    "drupal": {
        "sementes": _sementes_drupal,
        "profundidade": 1,
        "max_paginas": 2500,
        "requisicoes_por_segundo": 1,
        "ignorar_parametros": False,
        "sitemap": False,
        "escopo": [r"^https://www\.drupal\.org/p?sa-[a-z0-9-]+$"],
        "exclusoes": [],
        "teste": {"sementes": 1, "profundidade": 1, "max_paginas": 5},
    },
    "joomla": {
        "sementes": _sementes_joomla,
        "profundidade": 1,
        "max_paginas": 500,
        "requisicoes_por_segundo": 1,
        "ignorar_parametros": False,
        "sitemap": False,
        "escopo": [r"^https://developer\.joomla\.org/security-centre/\d+-[^/?#]+\.html$"],
        "exclusoes": [],
        "teste": {"sementes": 1, "profundidade": 1, "max_paginas": 10},
    },
}
