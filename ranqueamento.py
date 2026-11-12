# ranqueamento.py - modelos de ranqueamento sobre o índice da etapa 2
#
# Modelos (um método do Ranqueador para cada):
#   jaccard    similaridade de conjuntos (aula 07)
#   tfidf      R(q,d) = Σ w_{i,q}·w_{i,d}, sem normalização (aula 07)
#   vetorial   cosseno, esquemas 1, 2 e 3 de TF-IDF (aula 08)
#   bm1, bm15, bm11, bm25   família BM (aula 09)
#   bm25f      BM25 com campos título, corpo e código (aula 09, último slide)
#
# As fórmulas estão nas funções de peso logo abaixo, separadas dos laços que
# percorrem as listas, para que os testes (testar_ranking.py) possam conferi-las
# contra os exemplos dos slides.
#
# Termos de texto e de código são dimensões diferentes (o código usa o prefixo
# "c:"). Nos modelos sem campos, escore = escore_texto + α·escore_código, com
# α = peso_codigo. No BM25F, título, corpo e código são campos de uma mesma
# palavra da consulta.
#
# As estatísticas por documento (tamanho de cada campo, nº de termos distintos,
# normas dos vetores, limite do título) vêm de preparar_ranking.py.
import bisect
import heapq
import json
import math
import os
import struct
import time
from collections import defaultdict

import lexico
from buscar import PARTES, Buscador
from indice import PREFIXO_CODIGO, Indice

MODELOS = ("jaccard", "tfidf", "vetorial", "bm1", "bm15", "bm11", "bm25", "bm25f")
MODELO_PADRAO = "bm25f"

# parâmetros padrão (D2): K₁ e b usuais da literatura; pesos do BM25F (D7)
K1, B = 1.2, 0.75
PESOS_BM25F = {"titulo": 2.0, "corpo": 1.0, "codigo": 1.0}


# ======================================================== funções de peso
def log(x, base=2):
    if base == 2:
        return math.log2(x)
    if base == 10:
        return math.log10(x)
    return math.log(x) / math.log(base)


def tf_peso(f, modo="log", base=2, max_f=1):
    """Peso local (TF). 'log': 1 + log f (aula 07); 'bruto': f; 'aumentado':
    0,5 + 0,5·f/max f; 'binario': 1."""
    if f <= 0:
        return 0.0
    if modo == "log":
        return 1.0 + log(f, base)
    if modo == "bruto":
        return float(f)
    if modo == "aumentado":
        return 0.5 + 0.5 * f / max_f
    if modo == "binario":
        return 1.0
    raise ValueError(f"modo de TF desconhecido: {modo}")


def idf_peso(n, N, modo="log", base=2):
    """Peso global (IDF). 'log': log N/n (aula 07); 'suavizado': 1 + log N/n
    (exemplo 1 da aula 08); 'log1p': log(1 + N/n); 'um': sem IDF."""
    if modo == "log":
        return log(N / n, base)
    if modo == "suavizado":
        return 1.0 + log(N / n, base)
    if modo == "log1p":
        return log(1 + N / n, base)
    if modo == "um":
        return 1.0
    raise ValueError(f"modo de IDF desconhecido: {modo}")


# esquemas tradicionais de TF-IDF (aula 08): peso no documento e na consulta
ESQUEMAS = {
    1: {"tf_doc": "bruto", "idf_doc": "log", "tf_q": "aumentado", "idf_q": "log"},
    2: {"tf_doc": "log", "idf_doc": "um", "tf_q": "binario", "idf_q": "log1p"},
    3: {"tf_doc": "log", "idf_doc": "log", "tf_q": "log", "idf_q": "log"},
}


def jaccard(n_inter, n_q, n_d):
    """|q ∩ d| / |q ∪ d|, com |q ∪ d| = |q| + |d| − |q ∩ d|."""
    uniao = n_q + n_d - n_inter
    return n_inter / uniao if uniao else 0.0


def idf_bm(n, N, base=2, variante="limitado"):
    """IDF da família BM: log((N − n + 0,5)/(n + 0,5)). Fica negativo quando
    n > N/2 (D10). 'limitado': max(0, ·) [padrão]; 'log1p': log(1 + ·);
    'bruto': a fórmula do slide, sem correção."""
    x = (N - n + 0.5) / (n + 0.5)
    if variante == "limitado":
        return max(0.0, log(x, base))
    if variante == "log1p":
        return log(1 + x, base)
    if variante == "bruto":
        return log(x, base)
    raise ValueError(f"variante de IDF desconhecida: {variante}")


def bm1(idf):
    """BM1: só a informação global."""
    return idf


def bm15(tf, idf, k1):
    """BM15: saturação do tf, sem normalização pelo tamanho."""
    return (k1 + 1) * tf / (k1 + tf) * idf


def bm11(tf, idf, k1, razao):
    """BM11: tf saturado e normalizado pelo tamanho (razao = len(d)/avg_doclen)."""
    return (k1 + 1) * tf / (k1 * razao + tf) * idf


def bm25(tf, idf, k1, b, razao):
    """BM25: normalização parcial do tamanho, controlada por b
    (b = 0 → BM15; b = 1 → BM11)."""
    return (k1 + 1) * tf / (k1 * ((1 - b) + b * razao) + tf) * idf


def bm25f_tf_campo(tf, peso, b, razao):
    """Parcela de um campo no tf combinado do BM25F: w_f·tf_f / B_f."""
    return peso * tf / ((1 - b) + b * razao)


def bm25f(tf_comb, idf, k1):
    """BM25F: a saturação por K₁ é aplicada uma vez, sobre a soma dos campos."""
    return (k1 + 1) * tf_comb / (k1 + tf_comb) * idf


# ================================================================ top-k
def top_k(escores, k):
    """Os k maiores escores com um min-heap de tamanho k (slides 07-22 a 07-36):
    enche a heap até k; depois, cada documento com escore maior que o da raiz
    (o pior dos k) substitui a raiz. Desempate (D13): escore decrescente, depois
    id crescente; por isso a chave é (escore, −id). 'escores' é um dict
    doc → escore ou uma sequência de pares (doc, escore)."""
    pares = escores.items() if isinstance(escores, dict) else escores
    heap = []
    if k <= 0:
        return []
    for doc, s in pares:
        chave = (s, -doc)
        if len(heap) < k:
            heapq.heappush(heap, chave)
        elif chave > heap[0]:
            heapq.heapreplace(heap, chave)
    heap.sort(reverse=True)
    return [(-d, s) for s, d in heap]


# ============================================== estatísticas da coleção
COLUNAS_DOC = ("limite_titulo", "n_titulo", "n_corpo", "n_codigo", "distintos_texto",
               "distintos_codigo")


class Colecao:
    """Estatísticas por documento e da coleção usadas pelos modelos
    (geradas por preparar_ranking.py)."""

    def __init__(self, N, base, esquemas, docs, normas, medias, meta=None):
        self.N = N
        self.base = base
        self.esquemas = esquemas      # nome -> {"tf_doc", "idf_doc"} das normas
        for nome in COLUNAS_DOC:
            setattr(self, nome, docs[nome])
        self.n_texto = [a + b for a, b in zip(self.n_titulo, self.n_corpo)]
        self.normas2 = normas         # nome -> (texto[], codigo[])
        self.medias = medias          # titulo, corpo, texto, codigo
        self.meta = meta or {}

    # --- gravação e leitura (TSV ou binário de tamanho fixo)
    def colunas(self):
        cols = [(nome, getattr(self, nome), "I") for nome in COLUNAS_DOC]
        for e in sorted(self.normas2, key=str):
            t, c = self.normas2[e]
            cols += [(f"norma2_texto_e{e}", t, "d"), (f"norma2_codigo_e{e}", c, "d")]
        return cols

    def grava_tsv(self, caminho):
        cols = self.colunas()
        with open(caminho, "w", encoding="utf-8", newline="\n") as f:
            f.write("id\t" + "\t".join(n for n, _, _ in cols) + "\n")
            for i in range(self.N):
                f.write(f"{i}\t" + "\t".join(repr(v[i]) if t == "d" else str(v[i])
                                              for _, v, t in cols) + "\n")

    def grava_bin(self, caminho):
        cols = self.colunas()
        fmt = struct.Struct("<" + "".join(t for _, _, t in cols))
        with open(caminho, "wb") as f:
            f.write(struct.pack("<I", self.N))
            for i in range(self.N):
                f.write(fmt.pack(*(v[i] for _, v, _ in cols)))
        return fmt.size

    @staticmethod
    def _le_tsv(caminho):
        with open(caminho, encoding="utf-8") as f:
            nomes = next(f).rstrip("\n").split("\t")[1:]
            cols = [[] for _ in nomes]
            conv = [float if n.startswith("norma2") else int for n in nomes]
            for linha in f:
                partes = linha.rstrip("\n").split("\t")[1:]
                for c, cv, v in zip(cols, conv, partes):
                    c.append(cv(v))
        return dict(zip(nomes, cols))

    @staticmethod
    def _le_bin(caminho, nomes):
        fmt = struct.Struct("<" + "".join("d" if n.startswith("norma2") else "I"
                                          for n in nomes))
        with open(caminho, "rb") as f:
            dados = f.read()
        N = struct.unpack_from("<I", dados)[0]
        linhas = list(fmt.iter_unpack(memoryview(dados)[4:4 + N * fmt.size]))
        return {n: [l[j] for l in linhas] for j, n in enumerate(nomes)}

    @classmethod
    def carrega(cls, pasta):
        with open(os.path.join(pasta, "colecao.json"), encoding="utf-8") as f:
            meta = json.load(f)
        if meta["formato"] == "bin":
            cols = cls._le_bin(os.path.join(pasta, "documentos_ranking.bin"), meta["colunas"])
        else:
            cols = cls._le_tsv(os.path.join(pasta, "documentos_ranking.tsv"))
        esquemas = {int(k) if k.isdigit() else k: v for k, v in meta["esquemas"].items()}
        normas = {e: (cols[f"norma2_texto_e{e}"], cols[f"norma2_codigo_e{e}"])
                  for e in esquemas}
        return cls(meta["N"], meta["base_log"], esquemas, cols, normas, meta["medias"], meta)


# =========================================================== consulta
class Consulta:
    """Consulta analisada. 'palavras' tem um par (termo de texto, termo de
    código) por palavra, com repetições (para f_{i,q}); um dos dois pode ser
    None. 'frases' e 'negados' são partes da consulta usadas como filtro."""

    def __init__(self, texto="", palavras=None, frases=None, negados=None):
        self.texto = texto
        self.palavras = palavras or []
        self.frases = frases or []
        self.negados = negados or []

    @classmethod
    def de_termos(cls, termos):
        """Consulta direta com termos de texto já analisados (testes)."""
        return cls(" ".join(termos), [(t, None) for t in termos])


class ProcessadorConsulta:
    """Mesma análise léxica do índice (lexico.py). Sintaxe aceita, como no
    buscar.py: palavras soltas, "frase entre aspas" (filtro), -palavra ou NOT
    palavra (exclui), codigo:termo (só no código). OR e AND são ignorados:
    o ranqueamento já usa a união das listas (D4)."""

    def __init__(self, stopwords=lexico.STOPWORDS, stemming=True):
        self.stopwords = stopwords
        self.stemming = stemming

    def palavras(self, texto):
        saida = []
        for tok in lexico.tokens(texto):
            termos = [t for t, _ in lexico.termos_texto(tok, stopwords=self.stopwords,
                                                        stemming=self.stemming)]
            if not termos:  # stopword: ignorada também no código, como no buscar.py
                continue
            cod = [t for t, _ in lexico.termos_codigo(tok, tam_max=0)]
            if len(termos) == 1:
                saida.append((termos[0], PREFIXO_CODIGO + cod[0] if len(cod) == 1 else None))
            else:
                saida += [(t, None) for t in termos]
        return saida

    def analisa(self, texto):
        c = Consulta(texto)
        partes = PARTES.findall(texto)
        negar = False
        for parte in partes:
            if parte in ("OR", "AND"):
                continue
            if parte == "NOT":
                negar = True
                continue
            if parte.startswith("-") and len(parte) > 1:
                parte, negar = parte[1:], True
            if negar:
                c.negados.append(parte)
                negar = False
                continue
            if parte.lower().startswith("codigo:"):
                c.palavras += [(None, PREFIXO_CODIGO + t)
                               for t, _ in lexico.termos_codigo(parte[7:].strip('"'), tam_max=0)]
                continue
            if parte.startswith('"'):
                c.frases.append(parte)
            c.palavras += self.palavras(parte.strip('"'))
        return c


# ============================================================ resultado
class Resultado:
    def __init__(self, modelo, consulta, top, n_candidatos, n_positivos, postings, ms,
                 avisos, detalhes=None, params=None):
        self.modelo = modelo
        self.consulta = consulta
        self.top = top                  # [(doc, escore)]
        self.n_candidatos = n_candidatos
        self.n_positivos = n_positivos  # candidatos com escore > 0 (depois dos filtros)
        self.postings = postings        # postings lidos
        self.ms = ms
        self.avisos = avisos
        self.detalhes = detalhes or {}  # doc -> [parcelas]
        self.params = params or {}


class _Prep:
    """Termos presentes no vocabulário, com f_q, e listas lidas uma vez."""

    def __init__(self, ind, consulta):
        self.ind = ind
        self.avisos = []
        self.listas = {}
        self.texto, self.codigo, self.palavras = {}, {}, {}
        voc = ind.vocabulario
        ausentes = []
        for t0, c0 in consulta.palavras:
            t = t0 if t0 in voc else None
            c = c0 if c0 in voc else None
            if t is None and c is None:
                ausentes.append(t0 or c0)
                continue
            if t:
                self.texto[t] = self.texto.get(t, 0) + 1
            if c:
                self.codigo[c] = self.codigo.get(c, 0) + 1
            self.palavras[(t, c)] = self.palavras.get((t, c), 0) + 1
        for t in dict.fromkeys(ausentes):
            self.avisos.append(f"termo não encontrado: {t}")

    def df(self, termo):
        return self.ind.vocabulario[termo][0]

    def lista(self, termo):
        lst = self.listas.get(termo)
        if lst is None:
            lst = self.listas[termo] = self.ind.lista(termo)
        return lst

    def postings(self):
        return sum(len(l) for l in self.listas.values())


def _anota(detalhes, alvo, doc, parcela):
    if alvo is not None and doc in alvo:
        detalhes.setdefault(doc, []).append(parcela)


# ============================================================ ranqueador
class Ranqueador:
    def __init__(self, indice, colecao, processador=None):
        if getattr(indice, "trechos", None) is not None:
            raise ValueError("o ranqueamento usa a granularidade 'documento'")
        self.ind = indice
        self.col = colecao
        self.N = colecao.N
        self.base = colecao.base
        if processador is None:
            p = indice.estatisticas["parametros"]
            processador = ProcessadorConsulta(
                lexico.STOPWORDS if p.get("stopwords", True) else frozenset(),
                p.get("stemming", True))
        self.proc = processador
        self.buscador = Buscador.__new__(Buscador)  # reaproveita frase/NOT do buscar.py
        self.buscador.ind = indice

    @classmethod
    def abre(cls, pasta="indice"):
        return cls(Indice(pasta), Colecao.carrega(pasta))

    # ------------------------------------------------------------ geral
    def escores(self, consulta, modelo=MODELO_PADRAO, **params):
        """Escores de todos os candidatos (sem filtros nem top-k)."""
        if isinstance(consulta, str):
            consulta = self.proc.analisa(consulta)
        return dict(getattr(self, modelo)(_Prep(self.ind, consulta), **params))

    def prepara(self, consulta):
        """Consulta analisada + termos/listas, para reusar em várias chamadas
        (ranquear(..., prep=...)): as listas são lidas uma vez só."""
        if isinstance(consulta, str):
            consulta = self.proc.analisa(consulta)
        return consulta, _Prep(self.ind, consulta)

    def ranquear(self, consulta, modelo=MODELO_PADRAO, k=10, explicar=False, prep=None,
                 **params):
        t0 = time.perf_counter()
        if prep is None:
            consulta, q = self.prepara(consulta)
        else:
            consulta, q = prep
        metodo = getattr(self, modelo)
        escores = metodo(q, **params)
        n_candidatos = len(escores)
        # filtros: frases (D11) e termos negados
        permitidos = None
        for frase in consulta.frases:
            docs = self.buscador._item(frase)
            if docs is not None:
                permitidos = set(docs) if permitidos is None else permitidos & set(docs)
        excluidos = set()
        for parte in consulta.negados:
            excluidos.update(self.buscador._item(parte) or [])
        filtrados = {d: s for d, s in escores.items()
                     if s > 0 and d not in excluidos and (permitidos is None or d in permitidos)}
        top = top_k(filtrados, k)
        ms = (time.perf_counter() - t0) * 1000
        detalhes = None
        if explicar and top:
            detalhes = {}
            metodo(q, alvo={d for d, _ in top}, detalhes=detalhes, **params)
        return Resultado(modelo, consulta, top, n_candidatos, len(filtrados), q.postings(), ms,
                         q.avisos, detalhes, params)

    def _campos(self, q, alpha):
        """(nome, termos {termo: f_q}, peso) dos dois 'campos' dos modelos sem campos."""
        saida = [("texto", q.texto, 1.0)]
        if alpha:
            saida.append(("codigo", q.codigo, alpha))
        return saida

    # ---------------------------------------------------------- aula 07
    def jaccard(self, q, peso_codigo=1.0, alvo=None, detalhes=None):
        col = self.col
        escores = defaultdict(float)
        for campo, termos, peso in self._campos(q, peso_codigo):
            if not termos:
                continue
            inter = defaultdict(int)
            for t in termos:
                for d, _, _ in q.lista(t):
                    inter[d] += 1
            distintos = col.distintos_texto if campo == "texto" else col.distintos_codigo
            for d, n in inter.items():
                j = jaccard(n, len(termos), distintos[d])
                escores[d] += peso * j
                _anota(detalhes, alvo, d, {"campo": campo, "q∩d": n, "|q|": len(termos),
                                           "|d|": distintos[d], "jaccard": j, "peso": peso})
        return escores

    def tfidf(self, q, peso_codigo=1.0, tf="log", idf_consulta=True, alvo=None, detalhes=None):
        """R(q,d) = Σ w_{i,q}·w_{i,d}, w = TF·IDF, sem normalização. tf='bruto'
        e idf_consulta=False reproduzem o exemplo "Do what?" (slide 07-46)."""
        base, N = self.base, self.N
        escores = defaultdict(float)
        for campo, termos, peso in self._campos(q, peso_codigo):
            for t, fq in termos.items():
                idf = idf_peso(q.df(t), N, "log", base)
                wq = tf_peso(fq, tf, base) * (idf if idf_consulta else 1.0)
                for d, f, _ in q.lista(t):
                    wd = tf_peso(f, tf, base) * idf
                    escores[d] += peso * wq * wd
                    _anota(detalhes, alvo, d, {"termo": t, "tf": f, "TF": tf_peso(f, tf, base),
                                               "idf": idf, "w_q": wq, "w_d": wd,
                                               "parcela": peso * wq * wd})
        return escores

    # ---------------------------------------------------------- aula 08
    def vetorial(self, q, esquema=3, peso_codigo=1.0, alvo=None, detalhes=None):
        """Cosseno: Σ w_{i,d}·w_{i,q} / (|d|·|q|). A norma |d| vem pré-calculada
        (todos os termos do documento); com o peso α do código,
        |d|² = |d_texto|² + α²·|d_código|²."""
        base, N, col = self.base, self.N, self.col
        e = col.esquemas.get(esquema) or ESQUEMAS[esquema]
        if esquema not in col.normas2:
            raise ValueError(f"normas do esquema {esquema} não foram pré-calculadas")
        n2t, n2c = col.normas2[esquema]
        campos = self._campos(q, peso_codigo)
        max_f = max([f for _, termos, _ in campos for f in termos.values()] or [1])
        produto = defaultdict(float)
        q2 = 0.0
        for campo, termos, peso in campos:
            for t, fq in termos.items():
                n = q.df(t)
                wq = tf_peso(fq, e["tf_q"], base, max_f) * idf_peso(n, N, e["idf_q"], base)
                q2 += wq * wq
                idf_d = idf_peso(n, N, e["idf_doc"], base)
                for d, f, _ in q.lista(t):
                    wd = tf_peso(f, e["tf_doc"], base) * idf_d
                    produto[d] += peso * wq * wd
                    _anota(detalhes, alvo, d, {"termo": t, "tf": f, "w_d": wd, "w_q": wq,
                                               "peso": peso, "produto": peso * wq * wd})
        if q2 == 0:
            return {}
        nq = math.sqrt(q2)
        a2 = peso_codigo * peso_codigo
        escores = {}
        for d, p in produto.items():
            nd = math.sqrt(n2t[d] + a2 * n2c[d])
            escores[d] = p / (nd * nq) if nd else 0.0
            _anota(detalhes, alvo, d, {"|d|": nd, "|q|": nq, "cosseno": escores[d]})
        return escores

    # ---------------------------------------------------------- aula 09
    def _bm(self, q, parcela, peso_codigo, idf, alvo, detalhes):
        """Laço comum de BM1/BM15/BM11/BM25: cada termo é normalizado pelo
        tamanho do seu campo (texto ou código). A consulta é um conjunto."""
        base, N, col = self.base, self.N, self.col
        escores = defaultdict(float)
        for campo, termos, peso in self._campos(q, peso_codigo):
            lens = col.n_texto if campo == "texto" else col.n_codigo
            media = col.medias[campo]
            for t in termos:
                w_idf = idf_bm(q.df(t), N, base, idf)
                for d, f, _ in q.lista(t):
                    razao = lens[d] / media
                    p = parcela(f, w_idf, razao)
                    escores[d] += peso * p
                    _anota(detalhes, alvo, d, {"termo": t, "campo": campo, "tf": f,
                                               "len/avg": razao, "idf": w_idf, "peso": peso,
                                               "parcela": peso * p})
        return escores

    def bm1(self, q, peso_codigo=1.0, idf="limitado", alvo=None, detalhes=None):
        return self._bm(q, lambda f, i, r: bm1(i), peso_codigo, idf, alvo, detalhes)

    def bm15(self, q, k1=K1, peso_codigo=1.0, idf="limitado", alvo=None, detalhes=None):
        return self._bm(q, lambda f, i, r: bm15(f, i, k1), peso_codigo, idf, alvo, detalhes)

    def bm11(self, q, k1=K1, peso_codigo=1.0, idf="limitado", alvo=None, detalhes=None):
        return self._bm(q, lambda f, i, r: bm11(f, i, k1, r), peso_codigo, idf, alvo, detalhes)

    def bm25(self, q, k1=K1, b=B, peso_codigo=1.0, idf="limitado", alvo=None, detalhes=None):
        return self._bm(q, lambda f, i, r: bm25(f, i, k1, b, r), peso_codigo, idf, alvo,
                        detalhes)

    def bm25f(self, q, k1=K1, peso_titulo=None, peso_corpo=None, peso_codigo=None,
              b_titulo=B, b_corpo=B, b_codigo=B, idf="limitado", alvo=None, detalhes=None):
        """BM25F (Robertson e Zaragoza): por palavra da consulta,
        t̃f = Σ_f w_f·tf_f / ((1 − b_f) + b_f·len_f/avg_f), e o escore é
        (K₁ + 1)·t̃f/(K₁ + t̃f)·idf, com n = documentos com a palavra em
        qualquer campo. Título e corpo vêm do termo de texto, separados pela
        posição (< limite_titulo = título); o código, do termo 'c:'."""
        base, N, col = self.base, self.N, self.col
        w = {"titulo": PESOS_BM25F["titulo"] if peso_titulo is None else peso_titulo,
             "corpo": PESOS_BM25F["corpo"] if peso_corpo is None else peso_corpo,
             "codigo": PESOS_BM25F["codigo"] if peso_codigo is None else peso_codigo}
        bs = {"titulo": b_titulo, "corpo": b_corpo, "codigo": b_codigo}
        lens = {"titulo": col.n_titulo, "corpo": col.n_corpo, "codigo": col.n_codigo}
        medias = col.medias
        limite = col.limite_titulo
        posicoes = getattr(self.ind, "posicoes", True)
        escores = defaultdict(float)
        for (t, c), _fq in q.palavras.items():
            lt = q.lista(t) if t else []
            lc = q.lista(c) if c else []
            if lt and lc:
                n = len({d for d, _, _ in lt} | {d for d, _, _ in lc})
            else:
                n = len(lt) or len(lc)
            w_idf = idf_bm(n, N, base, idf)
            tfs = defaultdict(lambda: [0, 0, 0])  # doc -> tf título, corpo, código
            for d, f, pos in lt:
                nt = bisect.bisect_left(pos, limite[d]) if posicoes else 0
                x = tfs[d]
                x[0] += nt
                x[1] += f - nt
            for d, f, _ in lc:
                tfs[d][2] += f
            for d, x in tfs.items():
                comb = 0.0
                partes = {}
                for i, campo in enumerate(("titulo", "corpo", "codigo")):
                    if x[i] and w[campo]:
                        r = lens[campo][d] / medias[campo]
                        v = bm25f_tf_campo(x[i], w[campo], bs[campo], r)
                        comb += v
                        partes[campo] = {"tf": x[i], "len/avg": r, "w·tf/B": v}
                s = bm25f(comb, w_idf, k1)
                escores[d] += s
                _anota(detalhes, alvo, d, {"palavra": t or c, "campos": partes, "tf~": comb,
                                           "n": n, "idf": w_idf, "parcela": s})
        return escores

    # ------------------------------------------------------- utilidades
    def documento(self, d):
        return self.ind.documentos[d]
