# lexico.py - análise léxica: texto -> termos do índice
#
# Duas regras, uma para o texto em linguagem natural e outra para o código:
#
#   termos_texto(texto)   tokenização, remoção de acentos, minúsculas,
#                         stopwords e stemming (Snowball, inglês)
#   termos_codigo(codigo) tokenização de identificadores, minúsculas,
#                         sem stopwords, sem stemming e com limite de tamanho
#
# As duas devolvem a lista de termos com a posição de cada um no texto
# original. As stopwords deixam um "buraco" na sequência de posições, para
# que a busca por frase continue funcionando ("denial of service" casa com
# "denial service" separados por uma posição).
#
# Identificadores do domínio são preservados inteiros, porque são o que o
# usuário mais busca: CVE-2024-3094, GHSA-xxxx-xxxx-xxxx, CWE-79,
# SA-CORE-2024-001, MS17-010, versões (2.4.1) e pacotes (@scope/nome).
# Por isso NÃO removemos números (o slide sugere removê-los): eles fazem
# parte de CVEs, versões e IDs de exploit.
import os
import re
import unicodedata

import snowballstemmer

PASTA = os.path.dirname(os.path.abspath(__file__))

# Ordem importa: os identificadores vêm antes da regra geral de palavra.
_IDS = (r"cve-\d{4}-\d{4,7}"
        r"|ghsa(?:-[a-z0-9]{4}){3}"
        r"|cwe-\d{1,4}"
        r"|(?:sa-core|sa-contrib|psa)-\d{4}-\d{2,3}(?:-\d{2})?"
        r"|ms\d{2}-\d{3}"
        r"|@[a-z0-9][\w.-]*/[a-z0-9][\w.-]*[a-z0-9]")
_VERSAO = r"v?\d+(?:\.\d+)+[a-z]*\d*"
# palavra: letras/dígitos de qualquer alfabeto, com "_" interno
# (com_contenthistory, array_class); hífen e ponto separam palavras
_PALAVRA = r"[^\W_]+(?:_+[^\W_]+)*"
TOKEN = re.compile(f"(?:{_IDS}|{_VERSAO}|{_PALAVRA})", re.I)

# no código, "_" no início/fim faz parte do nome (__init__, _start)
TOKEN_CODIGO = re.compile(f"(?:{_IDS}|{_VERSAO}|\\w+)", re.I)

# apóstrofo dentro de palavra é removido: parser's -> parsers, don't -> dont
APOSTROFO = re.compile(r"(?<=[^\W\d_])['’](?=[^\W\d_])")
# a ficha do exploit-db mostra o CVE sem prefixo ("CVE:\n2006-0660")
CVE_FICHA = re.compile(r"(CVE:\s*)((?:(?:19|20)\d\d-\d{4,7}\s*)+)")

TAM_MAX_TEXTO = 64      # tokens maiores que isso no texto são lixo (base64, hashes)
TAM_MAX_CODIGO = 24     # hiperparâmetro: limite de tamanho de token no código
TAM_MIN_CODIGO = 2      # variáveis de uma letra (i, x) não ajudam a busca


def carrega_stopwords(caminho=None, quantas=None):
    """Lê o arquivo de stopwords (uma por linha, '#' comenta). 'quantas'
    pega só as N primeiras (as mais frequentes)."""
    caminho = caminho or os.path.join(PASTA, "stopwords_en.txt")
    with open(caminho, encoding="utf-8") as f:
        palavras = [l.strip() for l in f if l.strip() and not l.startswith("#")]
    return frozenset(palavras[:quantas] if quantas else palavras)


STOPWORDS = carrega_stopwords()
_stemmer = snowballstemmer.stemmer("english")
_cache_stem = {}
_cache_norm = {}


def sem_acentos(s):
    if s.isascii():
        return s
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def normaliza(token):
    """Minúsculas e sem acentos (com cache: o vocabulário é pequeno perto do
    número de tokens)."""
    n = _cache_norm.get(token)
    if n is None:
        n = sem_acentos(token).lower()
        if n[0] == "v" and n[1:2].isdigit() and "." in n:
            n = n[1:]  # v1.2.3 -> 1.2.3
        if len(_cache_norm) < 2_000_000:
            _cache_norm[token] = n
    return n


def stem(termo):
    """Stemming só de palavras: identificadores, versões, números e termos
    com dígitos (log4j, x86) ficam como estão."""
    s = _cache_stem.get(termo)
    if s is None:
        if termo.isalpha() and termo.isascii():
            s = _stemmer.stemWord(termo)
        else:
            s = termo
        if len(_cache_stem) < 2_000_000:
            _cache_stem[termo] = s
    return s


def tokens(texto):
    """Tokenização sem nenhuma normalização (caixa e acentos preservados).
    Usada pela tabela de etapas; o índice usa termos_texto()."""
    texto = APOSTROFO.sub("", texto)
    texto = CVE_FICHA.sub(lambda m: m.group(1) + re.sub(r"(\d{4}-)", r"CVE-\1", m.group(2)),
                          texto)
    return TOKEN.findall(texto)


def eh_numero(token):
    """Número ou versão (começa com dígito e não tem letras)."""
    return token[0].isdigit() and not any(c.isalpha() for c in token)


def _analisa(toks, inicio, stopwords, stemming):
    saida = []
    for pos, tok in enumerate(toks, inicio):
        if len(tok) > TAM_MAX_TEXTO:
            continue
        t = normaliza(tok)
        if t in stopwords:
            continue
        if stemming:
            t = stem(t)
        saida.append((t, pos))
    return saida


def termos_texto(texto, inicio=0, stopwords=STOPWORDS, stemming=True):
    """Devolve [(termo, posição)]. A posição conta todos os tokens,
    inclusive stopwords e tokens descartados."""
    return _analisa(tokens(texto), inicio, stopwords, stemming)


def termos_campos(textos, stopwords=STOPWORDS, stemming=True):
    """Analisa vários campos (título, descrição, ...) como um texto só,
    deixando uma posição vazia entre eles para que uma frase não case
    atravessando dois campos. Devolve ([(termo, posição)], nº de tokens)."""
    saida, pos = [], 0
    for texto in textos:
        if texto:
            toks = tokens(texto)
            saida += _analisa(toks, pos, stopwords, stemming)
            pos += len(toks) + 1
    return saida, pos


def tokens_codigo(codigo):
    return TOKEN_CODIGO.findall(codigo)


def termos_codigo(codigo, inicio=0, tam_max=None):
    """Código: sem stopwords e sem stemming (strcpy, eval e system são
    exatamente o que se busca), mas com limite de tamanho, porque shellcode,
    hexadecimais e base64 geram milhares de termos únicos. tam_max=0 desliga
    o limite."""
    tam_max = TAM_MAX_CODIGO if tam_max is None else (tam_max or 10**9)
    saida = []
    for pos, tok in enumerate(tokens_codigo(codigo), inicio):
        if TAM_MIN_CODIGO <= len(tok) <= tam_max:
            saida.append((normaliza(tok), pos))
    return saida


def termos_consulta(consulta):
    """Mesma análise do texto, para os termos de uma consulta."""
    return [t for t, _ in termos_texto(consulta)]


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    exemplo = " ".join(sys.argv[1:]) or (
        "Heap-based buffer overflow in OpenSSH's sshd (CVE-2024-6387, CWE-122) "
        "affects versions < 9.8p1 and v8.5.0; see GHSA-xvwq-p3wq-7x4j, "
        "SA-CORE-2024-001, MS17-010 and @openzeppelin/wizard. Configuração "
        "não é segura.\nCVE:\n2006-0660")
    print("tokens:", tokens(exemplo))
    print("termos:", termos_texto(exemplo))
    print("código:", termos_codigo("char buf[64]; strcpy(buf, argv[1]); "
                                   "__init__ \\x31\\xc0 0x4141414141414141414141414141"))
