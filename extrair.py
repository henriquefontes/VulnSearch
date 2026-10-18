# extrair.py - limpeza dos documentos: HTML -> campos de texto indexáveis
#
# Para cada página do corpus, devolve um dicionário com os campos:
#   titulo     título da vulnerabilidade/aviso (sem o nome do site)
#   descricao  meta description, quando o site a preenche com conteúdo útil
#   texto      texto do conteúdo principal, sem menus, rodapés, scripts e
#              textos de ajuda repetidos em todas as páginas
#   codigo     código-fonte da página (exploits e blocos <pre>), indexado
#              em um campo separado, com regras léxicas próprias
#   alt        atributo alt das imagens do conteúdo principal
#   cves, cwes identificadores encontrados na página (para uso futuro)
#
# O conteúdo principal de cada site foi identificado analisando páginas de
# amostra (ver amostras_extrator.py). Sites não reconhecidos usam uma regra
# genérica: <body> sem <nav>, <header>, <footer> e <aside>.
import re
from urllib.parse import urlparse

from selectolax.lexbor import LexborHTMLParser

CVE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.I)
CWE = re.compile(r"\bCWE-\d{1,4}\b", re.I)
ESPACOS = re.compile(r"[ \t\r\f\v]+")
LINHAS_VAZIAS = re.compile(r"\n\s*\n+")

# Elementos que nunca têm conteúdo indexável
SEMPRE_REMOVER = "script, style, noscript, svg, template, iframe"

# Perfil por site:
#   conteudo  seletor(es) do conteúdo principal, testados em ordem
#   remover   elementos de interface dentro do conteúdo (ajuda, promoções,
#             diálogos, navegação entre artigos)
#   titulo    seletor do título; se ausente, usa <title> limpo por 'sufixo'
#   sufixo    regex removida do <title> (nome do site)
#   codigo    seletor dos blocos de código, gravados no campo 'codigo'
#   meta      se a meta description traz conteúdo novo (e não um texto fixo
#             do site ou a repetição do título/texto)
#   palavras  se a meta keywords é útil
#   alt       se as imagens do conteúdo têm alt descritivo (nos 6 sites, os
#             alt são ícones ou avatares, então ficam de fora)
PERFIS = {
    "www.exploit-db.com": {
        "conteudo": ["div.content > div.row > div > div.card"],
        "todos": True,  # o conteúdo está em vários cartões: título/metadados e código
        "remover": "a[href^='/download'], a[href^='/raw'], button",
        "titulo": "h1.card-title",
        "codigo": "pre code, pre",
        "meta": False,  # repete título, tipo e plataforma
        "palavras": True,
    },
    "github.com": {
        "conteudo": ["main div.container-xl"],
        "remover": "nav, dialog, dialog-helper, include-fragment, .blankslate, "
                   "details-dialog, .Popover, button",
        "titulo": "h2.Subhead-heading",
        "codigo": "div.markdown-body pre",
        "meta": False,  # meta description é o texto padrão do GitHub
    },
    "www.rapid7.com": {
        "conteudo": ["main section:nth-of-type(2)", "main"],
        "remover": "div.group, a[href*='demo'], button",  # bloco de propaganda
        "titulo": "main h1",
        "codigo": "pre",
        "meta": False,  # repete o título
    },
    "cwe.mitre.org": {
        "conteudo": ["#CWEDefinition"],
        "remover": "#Filter_Menu, #Content_History, #More_Message_Custom, "
                   ".custom-filter-modal, span.tip, span.filter-tip",
        "sufixo": r"^\s*CWE\s*-\s*|\s*\(\d+(\.\d+)*\)\s*$",
        "codigo": "div.top, div.bottom, pre",  # exemplos de código das CWEs
        "meta": False,  # texto padrão do site
    },
    "www.drupal.org": {
        "conteudo": ["div.node-sa > div.content", "#content"],
        "remover": "ul.links, .field-name-field-sa-advisory-contributors-org",
        "titulo": "h1#page-subtitle, h1",
        "codigo": "pre",
        "meta": False,  # repete o início do texto
    },
    "developer.joomla.org": {
        "conteudo": ["div.com-content-article", "main#content"],
        "remover": "nav.pagenavigation, ul.pagenav, div.article-info, h1",
        "codigo": "pre",
        "meta": True,
    },
}
GENERICO = {"conteudo": ["body"], "remover": "nav, header, footer, aside",
            "codigo": "pre", "meta": True, "palavras": True, "alt": True}


def _limpa(texto):
    texto = ESPACOS.sub(" ", texto)
    return LINHAS_VAZIAS.sub("\n", texto).strip()


def _texto(no):
    return _limpa(no.text(separator="\n", strip=True)) if no else ""


def _meta(arvore, nome):
    no = arvore.css_first(f"meta[name='{nome}'], meta[property='og:{nome}']")
    return (no.attributes.get("content") or "").strip() if no else ""


def site_da_url(url):
    return urlparse(url).netloc.lower()


def extrair(url, html):
    """Extrai os campos indexáveis de uma página. Nunca levanta exceção por
    HTML malformado: o pior caso é devolver campos vazios."""
    perfil = PERFIS.get(site_da_url(url), GENERICO)
    arvore = LexborHTMLParser(html)
    for no in arvore.css(SEMPRE_REMOVER):
        no.decompose()

    # título
    titulo = ""
    if perfil.get("titulo"):
        titulo = _texto(arvore.css_first(perfil["titulo"]))
    if not titulo:
        no = arvore.css_first("title")
        titulo = _texto(no)
        if perfil.get("sufixo"):
            titulo = re.sub(perfil["sufixo"], "", titulo)
        titulo = re.split(r"\s+[|·]\s+", titulo)[0].strip()
    titulo = ESPACOS.sub(" ", titulo.replace("\n", " "))

    descricao = _meta(arvore, "description") if perfil.get("meta") else ""
    palavras = _meta(arvore, "keywords") if perfil.get("palavras") else ""

    # conteúdo principal: primeiro seletor que encontrar algo
    nos = []
    for seletor in perfil["conteudo"]:
        nos = arvore.css(seletor) if perfil.get("todos") else [arvore.css_first(seletor)]
        nos = [n for n in nos if n is not None]
        if nos:
            break

    codigo, texto, alt = [], [], []
    for no in nos:
        if perfil.get("remover"):
            for lixo in no.css(perfil["remover"]):
                lixo.decompose()
        # o código vai para o campo próprio e sai do texto
        for bloco in no.css(perfil.get("codigo", "pre")):
            if bloco.parent is not None:
                trecho = bloco.text(strip=False)
                if trecho.strip():
                    codigo.append(trecho.strip("\n"))
                bloco.decompose()
        if perfil.get("alt"):
            alt += [img.attributes.get("alt") or "" for img in no.css("img[alt]")]
        texto.append(_texto(no))

    # no exploit-db, o 3º cartão em diante é o menu do rodapé
    if site_da_url(url) == "www.exploit-db.com":
        texto = texto[:2]

    texto = "\n".join(t for t in texto if t)
    tudo = "\n".join([titulo, descricao, texto] + codigo)
    return {
        "titulo": titulo,
        "descricao": descricao,
        "palavras_chave": palavras,
        "texto": texto,
        "codigo": "\n\n".join(codigo),
        "alt": " ".join(a.strip() for a in alt if a.strip()),
        "cves": sorted({c.upper() for c in CVE.findall(tudo)}),
        "cwes": sorted({c.upper() for c in CWE.findall(tudo)}),
    }


if __name__ == "__main__":
    # Teste rápido: python extrair.py pagina.html URL
    import sys
    campos = extrair(sys.argv[2], open(sys.argv[1], encoding="utf-8").read())
    for chave, valor in campos.items():
        print(f"== {chave} ({len(valor)})")
        print(valor if isinstance(valor, list) else valor[:1500])
