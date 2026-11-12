# avaliar.py - avaliação dos modelos com julgamentos de relevância
# Uso:
#   python avaliar.py --juntar     julgamentos/pool_*.tsv preenchidos -> julgamentos/qrels.tsv
#   python avaliar.py              P@10, MAP e nDCG@10 por modelo + busca em grade
#                                  (K₁ e b do BM25; pesos e K₁ do BM25F)
#   python avaliar.py --testar     testes das métricas (qrels inventado só no teste)
#
# qrels.tsv: consulta (id de consultas.tsv), url, relevancia (0, 1 ou 2). A URL
# identifica o documento (os ids mudam se o índice for reconstruído).
# Métricas (relevante = relevância ≥ 1; documento não julgado = não relevante):
#   P@10     relevantes entre os 10 primeiros / 10
#   AP       média das precisões nas posições dos relevantes recuperados, dividida
#            pelo total de relevantes julgados da consulta; MAP = média dos AP
#   nDCG@10  DCG = Σ rel_i / log₂(i + 1), dividido pelo DCG da ordenação ideal
# Atenção: escolher K₁, b e pesos pelas mesmas consultas usadas para medir
# superestima o resultado (sobreajuste); com poucas consultas, use validação
# cruzada ou separe consultas de treino e de teste.
import argparse
import csv
import glob
import math
import os
import sys
import tempfile

from etapas import grava

PASTA_JULG = "julgamentos"
QRELS = os.path.join(PASTA_JULG, "qrels.tsv")
PROFUNDIDADE = 100  # documentos ranqueados usados no AP


def le_consultas(caminho="consultas.tsv"):
    with open(caminho, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


# ----------------------------------------------------------------- métricas
def precisao_em(ranking, rel, k=10):
    return sum(1 for d in ranking[:k] if rel.get(d, 0) > 0) / k


def precisao_media(ranking, rel):
    n_rel = sum(1 for v in rel.values() if v > 0)
    if not n_rel:
        return None
    acertos, soma = 0, 0.0
    for i, d in enumerate(ranking, 1):
        if rel.get(d, 0) > 0:
            acertos += 1
            soma += acertos / i
    return soma / n_rel


def dcg(ganhos):
    return sum(g / math.log2(i + 1) for i, g in enumerate(ganhos, 1))


def ndcg_em(ranking, rel, k=10):
    ideal = dcg(sorted(rel.values(), reverse=True)[:k])
    return dcg([rel.get(d, 0) for d in ranking[:k]]) / ideal if ideal else None


# --------------------------------------------------------------- arquivos
def juntar(pasta=PASTA_JULG, saida=QRELS):
    linhas, invalidos = [], 0
    for caminho in sorted(glob.glob(os.path.join(pasta, "pool_*.tsv"))):
        cid = os.path.basename(caminho)[5:-4]
        with open(caminho, encoding="utf-8", newline="") as f:
            for l in csv.DictReader(f, delimiter="\t"):
                v = (l.get("relevante") or "").strip()
                if v in ("0", "1", "2"):
                    linhas.append((cid, l["url"], v))
                elif v:
                    invalidos += 1
    with open(saida, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t", lineterminator="\n")
        w.writerow(["consulta", "url", "relevancia"])
        w.writerows(linhas)
    return len(linhas), invalidos


def le_qrels(caminho=QRELS):
    qrels = {}
    with open(caminho, encoding="utf-8", newline="") as f:
        for l in csv.DictReader(f, delimiter="\t"):
            qrels.setdefault(l["consulta"], {})[l["url"]] = int(l["relevancia"])
    return qrels


# --------------------------------------------------------------- avaliação
def configuracoes():
    from ranqueamento import MODELOS
    cfg = [("modelos", m, m, {}) for m in MODELOS]
    for k1 in (0.5, 0.9, 1.2, 1.5, 2.0):
        for b in (0.0, 0.25, 0.5, 0.75, 1.0):
            cfg.append(("bm25", f"bm25 K1={k1} b={b}", "bm25", {"k1": k1, "b": b}))
    for k1 in (0.9, 1.2, 2.0):
        for pt in (1, 2, 3, 5):
            for pc in (0, 0.5, 1):
                cfg.append(("bm25f", f"bm25f K1={k1} título={pt} código={pc}", "bm25f",
                            {"k1": k1, "peso_titulo": pt, "peso_codigo": pc}))
    return cfg


def avalia(r, consultas, qrels, cfgs, k=10):
    """{nome: (P@k, MAP, nDCG@k, {consulta: (p, ap, ndcg)})} das consultas julgadas."""
    julgadas = [c for c in consultas if c["id"] in qrels]
    preps = {c["id"]: r.prepara(c["consulta"]) for c in julgadas}
    saida = {}
    for _grupo, nome, modelo, params in cfgs:
        por = {}
        for c in julgadas:
            res = r.ranquear(None, modelo, PROFUNDIDADE, prep=preps[c["id"]], **params)
            urls = [r.documento(d)["url"] for d, _ in res.top]
            rel = qrels[c["id"]]
            por[c["id"]] = (precisao_em(urls, rel, k), precisao_media(urls, rel),
                            ndcg_em(urls, rel, k))

        def med(i):
            v = [x[i] for x in por.values() if x[i] is not None]
            return sum(v) / len(v) if v else float("nan")
        saida[nome] = (med(0), med(1), med(2), por)
    return saida


def main_avaliar(a):
    from ranqueamento import Ranqueador
    if not os.path.exists(a.qrels):
        print(f"Sem julgamentos ({a.qrels} não existe). Rode pool.py, preencha a coluna "
              "'relevante' dos arquivos julgamentos/pool_*.tsv e depois avaliar.py --juntar.")
        return
    qrels = le_qrels(a.qrels)
    consultas = le_consultas(a.consultas)
    r = Ranqueador.abre(a.indice)
    cfgs = configuracoes()
    res = avalia(r, consultas, qrels, cfgs)
    n_q = len([c for c in consultas if c["id"] in qrels])
    os.makedirs(a.saida, exist_ok=True)
    cab = ["configuração", "P@10", "MAP", "nDCG@10"]
    for grupo, titulo in (("modelos", "modelos com os parâmetros padrão"),
                          ("bm25", "busca em grade do BM25 (K₁ × b)"),
                          ("bm25f", "busca em grade do BM25F (K₁ × peso do título × peso do código)")):
        nomes = [n for g, n, _, _ in cfgs if g == grupo]
        linhas = [[n] + [f"{x:.4f}" for x in res[n][:3]] for n in nomes]
        if grupo != "modelos":
            linhas.sort(key=lambda l: -float(l[2]))
        grava(a.saida, f"avaliacao_{grupo}", cab, linhas,
              f"Avaliação: {titulo}; {n_q} consultas julgadas, {sum(len(v) for v in qrels.values())} "
              "julgamentos. Atenção ao sobreajuste: parâmetros escolhidos e medidos nas mesmas "
              "consultas.")
        melhor = max(nomes, key=lambda n: res[n][1])
        print(f"{titulo}: melhor MAP = {res[melhor][1]:.4f} ({melhor})")
    por = [[c, n] + [("" if x is None else f"{x:.4f}") for x in v]
           for n in [n for g, n, _, _ in cfgs if g == "modelos"]
           for c, v in res[n][3].items()]
    grava(a.saida, "avaliacao_por_consulta", ["consulta", "modelo", "P@10", "AP", "nDCG@10"], por)
    print(f"Tabelas em {a.saida}{os.sep}avaliacao_*.csv|md")


# ------------------------------------------------------------------ testes
def testes():
    """Métricas contra contas à mão, com qrels inventado (não são julgamentos reais)."""
    falhas = []

    def eq(nome, a, b):
        if a is None or abs(a - b) > 1e-9:
            falhas.append(f"{nome}: {a} != {b}")

    rel = {"d1": 2, "d3": 1, "d6": 1, "d7": 0}
    ranking = ["d1", "d2", "d3", "d4", "d5"]
    eq("P@5", precisao_em(ranking, rel, 5), 2 / 5)
    eq("P@10 (ranking curto)", precisao_em(ranking, rel, 10), 2 / 10)
    eq("AP", precisao_media(ranking, rel), (1 / 1 + 2 / 3) / 3)
    ideal = 2 + 1 / math.log2(3) + 1 / math.log2(4)
    eq("nDCG@5", ndcg_em(ranking, rel, 5), (2 + 1 / math.log2(4)) / ideal)
    eq("nDCG ordenação ideal", ndcg_em(["d1", "d3", "d6"], rel, 10), 1.0)
    eq("AP ordenação ideal", precisao_media(["d1", "d3", "d6", "d2"], rel), 1.0)
    if precisao_media(ranking, {"d1": 0}) is not None or ndcg_em(ranking, {}, 10) is not None:
        falhas.append("consulta sem relevantes deveria dar None")
    # juntar + le_qrels com arquivos temporários
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "pool_q99.tsv"), "w", encoding="utf-8", newline="") as f:
            f.write("url\ttitulo\tsite\trelevante\tobservacao\n"
                    "u1\tA\ts\t2\t\nu2\tB\ts\t\t\nu3\tC\ts\t0\t\nu4\tD\ts\tx\t\n")
        q = os.path.join(tmp, "qrels.tsv")
        n, inval = juntar(tmp, q)
        if (n, inval) != (2, 1) or le_qrels(q) != {"q99": {"u1": 2, "u3": 0}}:
            falhas.append(f"juntar/le_qrels: {n}, {inval}, {le_qrels(q)}")
    return falhas


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Avaliação com julgamentos de relevância.")
    p.add_argument("--juntar", action="store_true", help="pool_*.tsv -> qrels.tsv")
    p.add_argument("--testar", action="store_true", help="testes das métricas")
    p.add_argument("--indice", default="indice")
    p.add_argument("--consultas", default="consultas.tsv")
    p.add_argument("--qrels", default=QRELS)
    p.add_argument("--saida", default="resultados_etapa3")
    a = p.parse_args()
    if a.testar:
        falhas = testes()
        print("Testes de avaliar.py: " + ("OK" if not falhas else "FALHAS"))
        for f in falhas:
            print("  FALHA:", f)
        sys.exit(1 if falhas else 0)
    if a.juntar:
        n, inval = juntar(PASTA_JULG, a.qrels)
        print(f"{n} julgamentos gravados em {a.qrels}"
              + (f"; {inval} valores inválidos ignorados (use 0, 1 ou 2)" if inval else ""))
        return
    main_avaliar(a)


if __name__ == "__main__":
    main()
