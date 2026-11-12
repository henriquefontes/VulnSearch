# trechos.py - trechos (snippets) com destaque dos termos da consulta
#
# Módulo separado de propósito: no cronograma, a geração de trechos é do
# integrante do processamento de consultas; ele pode revisar ou substituir
# este arquivo sem mexer no servidor. Interface:
#
#   d = Destaque.de_consulta(consulta)        consulta: ranqueamento.Consulta
#   gera(campos, d) -> {"titulo": [...], "trecho": [...], "trecho_codigo": [...] | None}
#
# Cada trecho é uma lista de segmentos {"texto": str, "destaque": bool}, com
# vizinhos do mesmo tipo unidos. Nunca há HTML: quem exibe escapa o texto e
# marca só os segmentos com destaque.
#
# Casamento (as regras são as do lexico, não reescritas aqui):
#   texto   token do texto original (lexico.tokens_com_posicao), normalizado e
#           com stemming, pertence aos termos de texto da consulta;
#           stopwords nunca são destacadas, mas contam posição (frases)
#   código  token do código (lexico.tokens_codigo_com_posicao), minúsculo e sem
#           stemming, de 2 a 24 caracteres, pertence aos termos 'c:' da consulta
#   frases  a sequência inteira é destacada, inclusive stopwords internas
#           ("denial of service")
# Tokens casados vizinhos formam um só destaque ("SQL Injection").
#
# Janela: ~220 caracteres com mais termos DISTINTOS da consulta (desempate:
# mais casamentos, depois a primeira); se ela não cobre todos os termos que
# aparecem no campo, entra uma segunda janela, separada por " … ".
# Ordem de busca do trecho: texto -> descrição -> palavras-chave -> código.
# Sem casamento: os primeiros ~220 caracteres, sem destaque.
# trecho_codigo: até 5 linhas em volta da primeira linha com casamento, cada
# uma cortada em 120 caracteres, preservando as quebras de linha.
import re

import lexico
from indice import PREFIXO_CODIGO

JANELA = 220            # caracteres de cada janela do trecho
RECUO = 60              # a janela começa até RECUO caracteres antes do 1º casamento
LINHAS_CODIGO = 5
LARGURA_LINHA = 120
RET = "…"
ESPACOS = re.compile(r"\s+")


class Destaque:
    """Termos da consulta para destacar: texto (com stemming), código (sem o
    prefixo 'c:') e frases [(termo, deslocamento)]."""

    def __init__(self, texto=(), codigo=(), frases=(), stopwords=lexico.STOPWORDS,
                 stemming=True):
        self.texto = set(texto)
        self.codigo = set(codigo)
        self.frases = [f for f in frases if len(f) > 1]
        self.stopwords = stopwords
        self.stemming = stemming

    @classmethod
    def de_consulta(cls, consulta, stopwords=lexico.STOPWORDS, stemming=True):
        texto = {t for t, _ in consulta.palavras if t}
        codigo = {c[len(PREFIXO_CODIGO):] for _, c in consulta.palavras if c}
        frases = []
        for f in consulta.frases:
            termos = lexico.termos_texto(f.strip('"'), stopwords=stopwords, stemming=stemming)
            if termos:
                base = termos[0][1]
                frases.append([(t, p - base) for t, p in termos])
        return cls(texto, codigo, frases, stopwords, stemming)

    def termo(self, token):
        """Termo de texto de um token (None se descartado ou stopword)."""
        if len(token) > lexico.TAM_MAX_TEXTO:
            return None
        t = lexico.normaliza(token)
        if t in self.stopwords:
            return None
        return lexico.stem(t) if self.stemming else t

    def termo_codigo(self, token):
        if lexico.TAM_MIN_CODIGO <= len(token) <= lexico.TAM_MAX_CODIGO:
            return lexico.normaliza(token)
        return None


# ------------------------------------------------------------- segmentos
def junta(segmentos):
    """Une vizinhos do mesmo tipo e descarta textos vazios."""
    saida = []
    for s in segmentos:
        if not s["texto"]:
            continue
        if saida and saida[-1]["destaque"] == s["destaque"]:
            saida[-1]["texto"] += s["texto"]
        else:
            saida.append(dict(s))
    return saida


def segmentos(texto, ini, fim, intervalos, colapsar=True):
    """Segmentos de texto[ini:fim], destacando os intervalos (ini, fim) dados
    (ordenados, sem sobreposição). colapsar troca sequências de espaços e
    quebras de linha por um espaço."""
    saida, pos = [], ini
    for a, b in intervalos:
        a, b = max(a, ini), min(b, fim)
        if a >= b:
            continue
        saida.append({"texto": texto[pos:a], "destaque": False})
        saida.append({"texto": texto[a:b], "destaque": True})
        pos = b
    saida.append({"texto": texto[pos:fim], "destaque": False})
    if colapsar:
        for s in saida:
            s["texto"] = ESPACOS.sub(" ", s["texto"])
    return junta(saida)


# ------------------------------------------------------------- casamentos
def casamentos_texto(texto, d):
    """(tokens [(tok, ini, fim)], marcas [chave ou None]) de um campo de texto.
    A chave é o termo casado; tokens internos de uma frase recebem a chave
    da frase."""
    toks = lexico.tokens_com_posicao(texto)
    termos = [d.termo(t) for t, _, _ in toks]
    marcas = [t if t in d.texto else None for t in termos]
    for k, frase in enumerate(d.frases):
        fim_rel = max(dl for _, dl in frase)
        for i in range(len(toks) - fim_rel):
            if all(termos[i + dl] == t for t, dl in frase):
                for j in range(i, i + fim_rel + 1):
                    marcas[j] = marcas[j] or f"frase{k}"
    return toks, marcas


def casamentos_codigo(codigo, d, ini=0, fim=None):
    """Igual a casamentos_texto, para um pedaço do código."""
    pedaco = codigo[ini:fim]
    toks = [(t, a + ini, b + ini) for t, a, b in lexico.tokens_codigo_com_posicao(pedaco)]
    marcas = []
    for t, _, _ in toks:
        x = d.termo_codigo(t)
        marcas.append(x if x in d.codigo else None)
    return toks, marcas


def intervalos(toks, marcas, i=0, j=None):
    """Intervalos de destaque nos tokens i..j: casados vizinhos são unidos."""
    j = len(toks) - 1 if j is None else j
    saida = []
    ant = False
    for k in range(i, j + 1):
        if marcas[k]:
            if ant and saida:
                saida[-1][1] = toks[k][2]
            else:
                saida.append([toks[k][1], toks[k][2]])
            ant = True
        else:
            ant = False
    return [tuple(x) for x in saida]


# ----------------------------------------------------------------- janela
def _janelas(toks, marcas, alvo):
    """Melhor janela (i, j) de até JANELA caracteres: mais chaves distintas de
    'alvo', depois mais casamentos, depois a primeira. Duas pontas, O(n)."""
    melhor, chave_melhor = None, None
    cont = {}
    distintas = total = 0
    j = -1
    n = len(toks)
    for i in range(n):
        while j + 1 < n and toks[j + 1][2] - toks[i][1] <= JANELA:
            j += 1
            m = marcas[j]
            if m in alvo:
                cont[m] = cont.get(m, 0) + 1
                distintas += cont[m] == 1
                total += 1
        if j < i:  # token maior que a janela
            j = i
            continue
        chave = (distintas, total)
        if total and (chave_melhor is None or chave > chave_melhor):
            melhor, chave_melhor = (i, j), chave
        m = marcas[i]
        if m in alvo:
            cont[m] -= 1
            distintas -= cont[m] == 0
            total -= 1
    return melhor


def _recua(toks, marcas, i, j):
    """Desloca a janela para o primeiro casamento não ficar colado no início."""
    primeiro = next(k for k in range(i, j + 1) if marcas[k])
    alvo_ini = toks[primeiro][1] - RECUO
    a = primeiro
    while a > 0 and toks[a - 1][1] >= alvo_ini:
        a -= 1
    b = a
    while b + 1 < len(toks) and toks[b + 1][2] - toks[a][1] <= JANELA:
        b += 1
    # não perder casamentos do fim da janela original
    ultimo = max(k for k in range(i, j + 1) if marcas[k])
    if b < ultimo:
        return i, j
    return a, b


def trecho_de_campo(texto, toks, marcas):
    """Uma ou duas janelas com destaque; None se não há casamento."""
    presentes = {m for m in marcas if m}
    if not presentes:
        return None
    i, j = _recua(toks, marcas, *_janelas(toks, marcas, presentes))
    janelas = [(i, j)]
    faltam = presentes - {marcas[k] for k in range(i, j + 1) if marcas[k]}
    if faltam:
        # segunda janela: só tokens fora da primeira
        fora = [None if i <= k <= j else m for k, m in enumerate(marcas)]
        seg = _janelas(toks, fora, faltam)
        if seg:
            a, b = _recua(toks, fora, *seg)
            if b < i or a > j:
                janelas.append((a, b))
    janelas.sort()
    saida = []
    for n, (a, b) in enumerate(janelas):
        ini, fim = toks[a][1], toks[b][2]
        segs = segmentos(texto, ini, fim, intervalos(toks, marcas, a, b))
        if n:
            saida.append({"texto": " " + RET + " ", "destaque": False})
            antes = []
        else:
            antes = [{"texto": RET + " ", "destaque": False}] if texto[:ini].strip() else []
        saida += antes + segs
    ultimo_fim = toks[janelas[-1][1]][2]
    if texto[ultimo_fim:].strip():
        saida.append({"texto": " " + RET, "destaque": False})
    return junta(saida)


def inicio_sem_destaque(texto):
    """Os primeiros ~JANELA caracteres, cortados em limite de palavra."""
    t = ESPACOS.sub(" ", texto).strip()
    if len(t) <= JANELA:
        return [{"texto": t, "destaque": False}] if t else []
    corte = t.rfind(" ", 0, JANELA)
    corte = corte if corte > JANELA // 2 else JANELA
    return [{"texto": t[:corte].rstrip() + " " + RET, "destaque": False}]


# ----------------------------------------------------------------- código
def _linhas(codigo):
    """[(início, fim)] de cada linha (sem a quebra)."""
    saida, pos = [], 0
    for linha in codigo.split("\n"):
        saida.append((pos, pos + len(linha)))
        pos += len(linha) + 1
    return saida


def primeira_linha_com_casamento(codigo, d, linhas=None):
    """(índice da linha, tokens, marcas) da primeira linha com um termo de
    código da consulta, ou None. Antes de tokenizar uma linha, confere por
    substring (rápido mesmo em códigos de vários MB)."""
    if not d.codigo or not codigo:
        return None
    linhas = linhas or _linhas(codigo)
    termos = list(d.codigo)
    baixo = codigo.lower()
    for n, (a, b) in enumerate(linhas):
        trecho = baixo[a:b]
        if any(t in trecho for t in termos):
            toks, marcas = casamentos_codigo(codigo, d, a, b)
            if any(marcas):
                return n, toks, marcas
    return None


def trecho_codigo(codigo, d):
    """Até LINHAS_CODIGO linhas em volta da primeira linha com casamento, cada
    uma cortada em LARGURA_LINHA caracteres; quebras de linha preservadas."""
    linhas = _linhas(codigo)
    achado = primeira_linha_com_casamento(codigo, d, linhas)
    if achado is None:
        return None
    n = achado[0]
    ini = max(0, min(n - LINHAS_CODIGO // 2, len(linhas) - LINHAS_CODIGO))
    fim = min(len(linhas), ini + LINHAS_CODIGO)
    vazia = lambda k: not codigo[linhas[k][0]:linhas[k][1]].strip()
    while ini < n and vazia(ini):
        ini += 1
    while fim - 1 > n and vazia(fim - 1):
        fim -= 1
    saida = []
    for k in range(ini, fim):
        a, b = linhas[k]
        toks, marcas = casamentos_codigo(codigo, d, a, b)
        ivs = intervalos(toks, marcas)
        comeco = a
        # casamento além da largura: a linha mostrada começa um pouco antes dele
        if ivs and ivs[0][0] >= a + LARGURA_LINHA:
            comeco = max(a, ivs[0][0] - LARGURA_LINHA // 3)
        corte = min(b, comeco + LARGURA_LINHA)
        if k > ini:
            saida.append({"texto": "\n", "destaque": False})
        if comeco > a:
            saida.append({"texto": RET, "destaque": False})
        saida += segmentos(codigo, comeco, corte, ivs, colapsar=False)
        if b > corte:
            saida.append({"texto": RET, "destaque": False})
    return junta(saida)


def trecho_de_codigo_em_linha(codigo, d):
    """Trecho de uma linha (espaços colapsados) em volta do primeiro casamento
    no código, para quando o texto não casa."""
    achado = primeira_linha_com_casamento(codigo, d)
    if achado is None:
        return None
    n = achado[0]
    linhas = _linhas(codigo)
    a = linhas[max(0, n - 2)][0]
    b = linhas[min(len(linhas) - 1, n + 2)][1]
    toks, marcas = casamentos_codigo(codigo, d, a, b)
    return trecho_de_campo(codigo, toks, marcas)


# ----------------------------------------------------------------- geral
def titulo(texto, d):
    toks, marcas = casamentos_texto(texto, d)
    return segmentos(texto, 0, len(texto), intervalos(toks, marcas))


def trecho(campos, d):
    for nome in ("texto", "descricao", "palavras_chave"):
        texto = campos.get(nome) or ""
        if texto:
            t = trecho_de_campo(texto, *casamentos_texto(texto, d))
            if t:
                return t
    codigo = campos.get("codigo") or ""
    t = trecho_de_codigo_em_linha(codigo, d) if codigo else None
    if t:
        return t
    for nome in ("texto", "descricao", "palavras_chave", "codigo"):
        if (campos.get(nome) or "").strip():
            return inicio_sem_destaque(campos[nome])
    return []


def gera(campos, d):
    codigo = campos.get("codigo") or ""
    return {"titulo": titulo(campos.get("titulo") or "", d),
            "trecho": trecho(campos, d),
            "trecho_codigo": trecho_codigo(codigo, d) if codigo else None}
