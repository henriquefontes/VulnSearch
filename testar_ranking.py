# testar_ranking.py - testes de corretude do ranqueamento
# Uso: python testar_ranking.py [--indice indice_teste] [--docs 200] [--sem-indice]
#
# Testes 1-10: exemplos dos slides (aulas 07, 08 e 09) com índices pequenos
#   montados em memória (sem stemming e sem stopwords, com a base de log de cada
#   exemplo). Os documentos passam pelo mesmo cálculo de estatísticas do
#   preparar_ranking.py e pelos mesmos métodos do Ranqueador do índice real.
# Teste 12: métricas de avaliação (avaliar.py), com qrels inventado só no teste.
# Teste 11: consistência com o índice real. Para documentos sorteados, recalcula
#   BM25, BM25F e cosseno "na força bruta" a partir dos campos
#   (resultados/campos.jsonl.gz passado pelo lexico) e compara com o Ranqueador
#   (tolerância 1e-9); confere também normas, tamanhos e limite do título.
import argparse
import math
import os
import random
import re
import sys
from collections import Counter, defaultdict

import lexico
from indexar import CAMPOS_TEXTO, le_registros
from indice import PREFIXO_CODIGO
from preparar_ranking import CAMPOS_PADRAO, calcula, limite_do_titulo
from ranqueamento import (Consulta, ProcessadorConsulta, Ranqueador, _Prep, bm25, bm25f,
                          bm25f_tf_campo, idf_bm, idf_peso, jaccard, tf_peso, top_k)

FALHAS = []
N_OK = 0


def confere(nome, obtido, esperado, tol=5e-4):
    global N_OK
    ok = abs(obtido - esperado) <= tol
    if ok:
        N_OK += 1
    else:
        FALHAS.append(f"{nome}: obtido {obtido:.6f}, esperado {esperado:.6f}")
    return ok


def verdadeiro(nome, cond):
    global N_OK
    if cond:
        N_OK += 1
    else:
        FALHAS.append(nome)


def toks(s):
    """Tokenizador dos exemplos: minúsculas, mantém acentos (no exemplo 1 da
    aula 08, 'e' e 'é' são termos diferentes)."""
    return re.findall(r"\w+", s.lower())


class IndiceMemoria:
    """Índice posicional em memória com a mesma interface do Indice
    (vocabulario, lista, documentos). Posições como no indexar.py: título
    primeiro, uma posição vazia, depois o corpo; código à parte, com 'c:'."""

    def __init__(self, docs):
        self.posicoes, self.trechos = True, None
        self.estatisticas = {"parametros": {"stopwords": False, "stemming": False}}
        listas = defaultdict(lambda: defaultdict(list))
        self.documentos, self.limites = [], []
        for d, doc in enumerate(docs):
            if isinstance(doc, str):
                doc = {"corpo": doc}
            tit, corpo, cod = (toks(doc.get(c, "")) for c in ("titulo", "corpo", "codigo"))
            pos = 0
            for i, t in enumerate(tit):
                listas[t][d].append(i)
            if tit:
                pos = len(tit) + 1
            for i, t in enumerate(corpo):
                listas[t][d].append(pos + i)
            for i, t in enumerate(cod):
                listas[PREFIXO_CODIGO + t][d].append(i)
            self.limites.append(len(tit))
            self.documentos.append({"url": f"d{d + 1}", "site": "teste", "titulo": "",
                                    "n_texto": len(tit) + len(corpo), "n_codigo": len(cod)})
        self._listas = {t: [(d, len(p), p) for d, p in sorted(ds.items())]
                        for t, ds in sorted(listas.items())}
        self.vocabulario = {t: (len(l), sum(f for _, f, _ in l), 0, 0)
                            for t, l in self._listas.items()}

    def lista(self, termo):
        return self._listas.get(termo, [])


def ranqueador(docs, base=2, esquemas=None):
    ind = IndiceMemoria(docs)
    col, _, _ = calcula(ind, ind.limites, base, esquemas)
    return Ranqueador(ind, col, ProcessadorConsulta(frozenset(), False))


def escores(r, termos, modelo, **params):
    return r.escores(Consulta.de_termos(termos), modelo, **params)


SHAKESPEARE = ["To do is to be. To be is to do.",
               "To be or not to be. I am what I am.",
               "I think therefore I am. Do be do be do.",
               "Do do do, da da da. Let it be, let it be."]


# ======================================================== testes 1 a 10
def teste_1():
    r = ranqueador(SHAKESPEARE)
    e = escores(r, ["to", "do", "be"], "jaccard")
    for d, esp in enumerate([0.75, 0.25, 2 / 7, 1 / 3]):
        confere(f"T1 Jaccard d{d + 1}", e.get(d, 0), esp)


def teste_2():
    di, dj = {"t1", "t2", "t3", "t4", "t5"}, {"t2", "t4", "t6", "t8"}
    confere("T2 Jaccard dᵢ,dⱼ", jaccard(len(di & dj), len(di), len(dj)), 2 / 7)


def teste_3():
    r = ranqueador(SHAKESPEARE)
    confere("T3 IDF do", idf_peso(3, 4), 0.415)
    confere("T3 IDF what", idf_peso(1, 4), 2.0)
    e = escores(r, ["do", "what"], "tfidf", tf="bruto", idf_consulta=False)
    for d, esp in enumerate([0.830, 2.000, 1.245, 1.245]):
        confere(f"T3 'Do what?' d{d + 1}", e.get(d, 0), esp, 1e-3)


def teste_4():
    confere("T4 TF suavizado tf=3", tf_peso(3, "log"), 2.585)
    confere("T4 TF suavizado tf=2", tf_peso(2, "log"), 2.0)


EXEMPLO1 = {"ex1": {"tf_doc": "bruto", "idf_doc": "suavizado",
                    "tf_q": "bruto", "idf_q": "suavizado"}}


def teste_5():
    docs = ["A casa verde é verde", "Casa é feia", "A casa verde é velha", "A casa feia é verde"]
    r = ranqueador(docs, esquemas=EXEMPLO1)
    det = {}
    q = _Prep(r.ind, Consulta.de_termos(["casa", "verde", "e", "velha"]))
    cos = r.vetorial(q, esquema="ex1", alvo={0, 1, 2, 3}, detalhes=det)
    norma_q = [p for p in det[0] if "|q|" in p][0]["|q|"]
    esperado = [(5.0, 3.466, 1.444), (1.0, 2.449, 0.408), (12.0, 3.874, 3.099),
                (3.0, 3.163, 0.949)]
    for d, (prod, norma, norm) in enumerate(esperado):
        nd = [p for p in det[d] if "|d|" in p][0]["|d|"]
        confere(f"T5 norma d{d + 1}", nd, norma, 2e-3)
        # o slide arredonda o IDF (1,415); exato: 1 + log₂(4/3) = 1,41504 -> produto 5,0047
        confere(f"T5 produto d{d + 1}", cos[d] * nd * norma_q, prod, 1e-2)
        confere(f"T5 escore normalizado d{d + 1}", cos[d] * norma_q, norm, 2e-3)
    ordem = sorted(cos, key=lambda d: -cos[d])
    verdadeiro("T5 ranking d3 > d1 > d4 > d2", ordem == [2, 0, 3, 1])


def teste_6():
    r = ranqueador(["a a a b", "a a c", "a a", "b b"], base=10)
    e = escores(r, ["a", "b"], "vetorial", esquema=3)
    for d, esp in enumerate([0.9878, 0.0999, 0.3833, 0.9236]):
        confere(f"T6 cosseno d{d + 1}", e[d], esp, 2e-4)
    verdadeiro("T6 ranking d1, d4, d3, d2", sorted(e, key=lambda d: -e[d]) == [0, 3, 2, 1])


BM_DOCS = ["feia verde feia verde feia", "casa é feia", "é casa é é", "verde", "a velha"]


def teste_7():
    r = ranqueador(BM_DOCS)
    verdadeiro("T7 avg_doclen = 3", abs(r.col.medias["texto"] - 3) < 1e-12)
    e = escores(r, ["casa", "verde"], "bm25", k1=1, b=0.75)
    for d, esp in enumerate([0.555, 0.485, 0.431, 0.647, 0.0]):
        confere(f"T7 BM25 d{d + 1}", e.get(d, 0), esp, 1e-3)


def teste_8():
    r = ranqueador(BM_DOCS)
    q = ["casa", "verde", "feia"]
    for k1 in (0.5, 1.2, 2.0):
        e0, e15 = escores(r, q, "bm25", k1=k1, b=0), escores(r, q, "bm15", k1=k1)
        e1, e11 = escores(r, q, "bm25", k1=k1, b=1), escores(r, q, "bm11", k1=k1)
        verdadeiro(f"T8 BM25(b=0) = BM15, K1={k1}",
                   all(abs(e0[d] - e15[d]) < 1e-12 for d in e15) and e0.keys() == e15.keys())
        verdadeiro(f"T8 BM25(b=1) = BM11, K1={k1}",
                   all(abs(e1[d] - e11[d]) < 1e-12 for d in e11) and e1.keys() == e11.keys())
        for b in (0.0, 0.5, 0.75, 1.0):
            ef = r.escores(Consulta.de_termos(q), "bm25f", k1=k1, b_corpo=b,
                           peso_corpo=1.0)
            e = escores(r, q, "bm25", k1=k1, b=b)
            verdadeiro(f"T8 BM25F 1 campo = BM25, K1={k1} b={b}",
                       all(abs(ef[d] - e[d]) < 1e-12 for d in e) and ef.keys() == e.keys())
    # BM25F com dois campos: conta à mão para um documento
    r2 = ranqueador([{"titulo": "casa verde", "corpo": "casa feia"}, {"corpo": "verde"},
                     {"titulo": "feia", "corpo": "velha casa casa"}])
    e = r2.escores(Consulta.de_termos(["casa"]), "bm25f", k1=1.2, peso_titulo=2.0)
    m = r2.col.medias
    tft = (bm25f_tf_campo(1, 2.0, 0.75, 2 / m["titulo"])
           + bm25f_tf_campo(1, 1.0, 0.75, 2 / m["corpo"]))
    confere("T8 BM25F título+corpo d1", e[0], bm25f(tft, idf_bm(2, 3), 1.2), 1e-12)


def teste_9():
    docs = ["A verde casa verde é verde verde", "casa é feia", "a verde feia",
            "a casa feia é verde"]
    print("\n--- 9. Exercício de fixação (slide 07-48), para o grupo conferir ---")
    conj = [set(toks(d)) for d in docs]
    for j in range(1, 4):
        n = len(conj[0] & conj[j])
        print(f"  Jaccard(d1, d{j + 1}) = {n}/{len(conj[0] | conj[j])} = "
              f"{jaccard(n, len(conj[0]), len(conj[j])):.4f}")
    voc = sorted(set().union(*conj))
    print("  Matriz TF suavizada (1 + log₂ tf):")
    print("    " + "".join(f"{t:>8}" for t in voc))
    for d, doc in enumerate(docs):
        c = Counter(toks(doc))
        print(f"    d{d + 1}" + "".join(f"{tf_peso(c[t]):8.3f}" for t in voc))
    r = ranqueador(docs)
    print("  IDF (log₂ N/n): " + ", ".join(f"{t} {idf_peso(r.ind.vocabulario[t][0], 4):.3f}"
                                           for t in voc))
    for consulta in ("a casa verde", "a casa verde verde verde"):
        e = escores(r, toks(consulta), "tfidf")
        print(f"  TF-IDF '{consulta}' (consulta e documento ponderados): "
              + ", ".join(f"d{d + 1} {e.get(d, 0):.3f}" for d in range(4)))


def teste_10():
    rnd = random.Random(7)
    iguais = True
    for _ in range(1000):
        n = rnd.randint(0, 60)
        esc = {d: rnd.choice([rnd.random(), round(rnd.random(), 1)]) for d in
               rnd.sample(range(500), n)}
        k = rnd.randint(1, 15)
        esperado = sorted(esc.items(), key=lambda x: (-x[1], x[0]))[:k]
        if top_k(esc, k) != esperado:
            iguais = False
            break
    verdadeiro("T10 top_k = sorted(...)[:k] em 1000 listas (com empates)", iguais)
    jac = [0.012, 0.983, 0.111, 0.323, 0.523, 0.155, 0.653, 0.623, 0.734, 0.331]
    top = top_k(list(enumerate(jac, 1)), 3)
    verdadeiro("T10 slides 07-23 a 07-36: top-3 = d2, d9, d7", [d for d, _ in top] == [2, 9, 7])


# ============================================================ teste 11
CONSULTAS_11 = ["sql injection wordpress plugin", "remote code execution apache struts",
                "cross site scripting drupal", "buffer overflow windows smb", "log4j",
                "path traversal", "denial of service", "use after free",
                "strcpy stack overflow", "CVE-2021-44228 jndi"]


def teste_11(pasta, n_docs):
    r = Ranqueador.abre(pasta)
    ind, col = r.ind, r.col
    N, base = col.N, col.base
    p = ind.estatisticas["parametros"]
    stop = lexico.STOPWORDS if p["stopwords"] else frozenset()
    rnd = random.Random(11)
    amostra = set(rnd.sample(range(N), min(n_docs, N)))
    fonte = CAMPOS_PADRAO if os.path.exists(CAMPOS_PADRAO) else p["entrada"]
    docs = {}
    for d, reg in enumerate(le_registros(fonte, p["limite"], p["passo"], {"leitura": 0.0})):
        if d in amostra:
            if "html" in reg:
                from extrair import extrair
                reg = extrair(reg["url"], reg["html"])
            texto, _ = lexico.termos_campos([reg[k] for k in CAMPOS_TEXTO], stop, p["stemming"])
            lim, tit = limite_do_titulo(reg["titulo"], stop, p["stemming"])
            cod = (lexico.termos_codigo(reg["codigo"], tam_max=p["tam_max_codigo"])
                   if p["codigo"] and reg["codigo"] else [])
            docs[d] = {"texto": Counter(t for t, _ in texto),
                       "titulo": Counter(t for t, _ in tit), "limite": lim,
                       "codigo": Counter(PREFIXO_CODIGO + t for t, _ in cod)}
    df = lambda t: ind.vocabulario[t][0]

    # estatísticas pré-calculadas
    erros = 0
    for d, x in docs.items():
        n_t, n_tit, n_c = sum(x["texto"].values()), sum(x["titulo"].values()), sum(x["codigo"].values())
        erros += (col.limite_titulo[d] != x["limite"]) + (col.n_titulo[d] != n_tit)
        erros += (col.n_texto[d] != n_t) + (col.n_codigo[d] != n_c)
        erros += (col.distintos_texto[d] != len(x["texto"]))
        erros += (col.distintos_codigo[d] != len(x["codigo"]))
        for e, (n2t, n2c) in col.normas2.items():
            esq = col.esquemas[e]
            for cont, alvo in ((x["texto"], n2t[d]), (x["codigo"], n2c[d])):
                s = sum((tf_peso(f, esq["tf_doc"], base)
                         * idf_peso(df(t), N, esq["idf_doc"], base)) ** 2 for t, f in cont.items())
                erros += abs(s - alvo) > 1e-9 * max(1.0, s)
    verdadeiro(f"T11 tamanhos, distintos, limite do título e normas ({len(docs)} docs)",
               erros == 0)

    m = col.medias
    piores = {"bm25": 0.0, "bm25f": 0.0, "vetorial": 0.0}
    for consulta in CONSULTAS_11:
        cq = r.proc.analisa(consulta)
        q = _Prep(ind, cq)
        T, C = set(q.texto), set(q.codigo)
        obtido = {mod: r.escores(cq, mod) for mod in piores}
        # documentos de cada palavra (para o n do BM25F)
        docs_de = {t: {dd for dd, _, _ in ind.lista(t)} for t in T | C}
        for d, x in docs.items():
            # BM25 simples (texto + código, α = 1)
            s = 0.0
            for t in T:
                if x["texto"][t]:
                    s += bm25(x["texto"][t], idf_bm(df(t), N, base), 1.2, 0.75,
                              sum(x["texto"].values()) / m["texto"])
            for c in C:
                if x["codigo"][c]:
                    s += bm25(x["codigo"][c], idf_bm(df(c), N, base), 1.2, 0.75,
                              sum(x["codigo"].values()) / m["codigo"])
            piores["bm25"] = max(piores["bm25"], abs(s - obtido["bm25"].get(d, 0.0)))
            # BM25F
            s = 0.0
            len_tit = sum(x["titulo"].values())
            len_corpo = sum(x["texto"].values()) - len_tit
            for t, c in q.palavras:
                n = len(docs_de.get(t, set()) | docs_de.get(c, set()))
                tit = x["titulo"][t] if t else 0
                corpo = x["texto"][t] - tit if t else 0
                cd = x["codigo"][c] if c else 0
                comb = 0.0
                if tit:
                    comb += bm25f_tf_campo(tit, 2.0, 0.75, len_tit / m["titulo"])
                if corpo:
                    comb += bm25f_tf_campo(corpo, 1.0, 0.75, len_corpo / m["corpo"])
                if cd:
                    comb += bm25f_tf_campo(cd, 1.0, 0.75, sum(x["codigo"].values()) / m["codigo"])
                if comb:
                    s += bm25f(comb, idf_bm(n, N, base), 1.2)
            piores["bm25f"] = max(piores["bm25f"], abs(s - obtido["bm25f"].get(d, 0.0)))
            # cosseno, esquema 3
            idf = lambda t: idf_peso(df(t), N, "log", base)
            prod = sum(tf_peso(fq) * idf(t) * tf_peso(x["texto"][t]) * idf(t)
                       for t, fq in q.texto.items() if x["texto"][t])
            prod += sum(tf_peso(fq) * idf(t) * tf_peso(x["codigo"][t]) * idf(t)
                        for t, fq in q.codigo.items() if x["codigo"][t])
            nd = math.sqrt(sum((tf_peso(f) * idf(t)) ** 2 for t, f in x["texto"].items())
                           + sum((tf_peso(f) * idf(t)) ** 2 for t, f in x["codigo"].items()))
            nq = math.sqrt(sum((tf_peso(f) * idf(t)) ** 2
                               for t, f in list(q.texto.items()) + list(q.codigo.items())))
            s = prod / (nd * nq) if prod else 0.0
            piores["vetorial"] = max(piores["vetorial"], abs(s - obtido["vetorial"].get(d, 0.0)))
    for mod, dif in piores.items():
        verdadeiro(f"T11 {mod}: força bruta = Ranqueador (maior diferença {dif:.2e})", dif <= 1e-9)
    print(f"  T11: {len(docs)} documentos x {len(CONSULTAS_11)} consultas em {pasta}; "
          + ", ".join(f"{k} dif. máx. {v:.1e}" for k, v in piores.items()))


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = argparse.ArgumentParser()
    a.add_argument("--indice", default="indice_teste")
    a.add_argument("--docs", type=int, default=200)
    a.add_argument("--sem-indice", action="store_true", help="pula o teste 11")
    args = a.parse_args()
    for teste in (teste_1, teste_2, teste_3, teste_4, teste_5, teste_6, teste_7, teste_8,
                  teste_10, teste_9):
        teste()
    import avaliar
    for falha in avaliar.testes():
        FALHAS.append("T12 avaliar.py: " + falha)
    verdadeiro("T12 P@k, AP, nDCG e leitura dos julgamentos (avaliar.py)", True)
    if not args.sem_indice:
        teste_11(args.indice, args.docs)
    print(f"\n{N_OK} verificações OK, {len(FALHAS)} falhas")
    for f in FALHAS:
        print("  FALHA:", f)
    sys.exit(1 if FALHAS else 0)


if __name__ == "__main__":
    main()
