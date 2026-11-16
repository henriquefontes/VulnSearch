# avaliar_cv.py - calibração do BM25F com validação cruzada e teste pareado
# Uso: python avaliar_cv.py [--saida resultados_avaliacao]
# Grade (K1 x b x peso do título x peso do código), 5 partes das 20 consultas (estratificadas
# pelo tipo), escolha pelo nDCG@10 médio no treino, nDCG@10 medido no teste. Teste pareado
# por consulta contra os padrões: permutação exata (troca de sinais, 2^20) e Wilcoxon
# (aproximação normal). Também: métricas por consulta dos 8 modelos e fração do top-10 julgada.
import argparse
import itertools
import math
import os
import statistics

from avaliar import PROFUNDIDADE, QRELS, le_consultas, le_qrels, ndcg_em, precisao_media, precisao_em
from etapas import grava
from ranqueamento import MODELOS, Ranqueador

GRADE = {"k1": (0.9, 1.2, 2.0), "b": (0.5, 0.75), "peso_titulo": (1, 2, 3), "peso_codigo": (0.5, 1)}
PADRAO = {"k1": 1.2, "b": 0.75, "peso_titulo": 2, "peso_codigo": 1}


def permutacao(d, n_perm=20000):
    """p bilateral por troca aleatória de sinais (20.000 sorteios, semente fixa)."""
    import random
    rnd = random.Random(42)
    obs = abs(sum(d))
    cont = sum(1 for _ in range(n_perm)
               if abs(sum(x if rnd.random() < 0.5 else -x for x in d)) >= obs - 1e-12)
    return (cont + 1) / (n_perm + 1)


def wilcoxon(d):
    d = [x for x in d if abs(x) > 1e-12]
    n = len(d)
    if n == 0:
        return 1.0
    ordem = sorted(range(n), key=lambda i: abs(d[i]))
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j + 1 < n and abs(abs(d[ordem[j + 1]]) - abs(d[ordem[i]])) < 1e-12:
            j += 1
        for k in range(i, j + 1):
            ranks[ordem[k]] = (i + j) / 2 + 1
        i = j + 1
    w = sum(r for r, x in zip(ranks, d) if x > 0)
    mu = n * (n + 1) / 4
    sd = math.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    z = (abs(w - mu) - 0.5) / sd
    return math.erfc(z / math.sqrt(2))


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--saida", default="resultados_avaliacao")
    a.add_argument("--indice", default="indice")
    args = a.parse_args()
    r = Ranqueador.abre(args.indice)
    qrels = le_qrels(QRELS)
    consultas = [c for c in le_consultas() if c["id"] in qrels]
    preps = {c["id"]: r.prepara(c["consulta"]) for c in consultas}

    def avalia(modelo, params):
        params = dict(params)
        if "b" in params:  # mesmo b nos três campos, como na API
            bb = params.pop("b")
            params.update(b_titulo=bb, b_corpo=bb, b_codigo=bb)
        por = {}
        for c in consultas:
            urls = [r.documento(d)["url"] for d, _ in r.ranquear(None, modelo, PROFUNDIDADE, prep=preps[c["id"]], **params).top]
            rel = qrels[c["id"]]
            julg = sum(1 for u in urls[:10] if u in rel) / max(1, min(10, len(urls)))
            por[c["id"]] = (precisao_em(urls, rel, 10), precisao_media(urls, rel) or 0.0, ndcg_em(urls, rel, 10) or 0.0, julg)
        return por

    os.makedirs(args.saida, exist_ok=True)
    # modelos: média, por consulta, fração julgada do top-10, teste pareado contra o BM25F
    mods = {m: avalia(m, {}) for m in MODELOS}
    base = mods["bm25f"]
    linhas = []
    for m in MODELOS:
        v = mods[m]
        d = [v[c][2] - base[c][2] for c in v]
        linhas.append([m, "sim" if m in ("tfidf", "vetorial", "bm25", "bm25f") else "não"]
                      + [f"{statistics.mean(x[i] for x in v.values()):.4f}" for i in range(4)]
                      + ["—" if m == "bm25f" else f"{permutacao(d):.4f}"])
    grava(args.saida, "modelos_resumo", ["modelo", "formou o pool", "P@10", "MAP", "nDCG@10",
                                         "top-10 julgado", "p (permutação, nDCG@10 × BM25F)"], linhas,
          "Média das 20 consultas. 'top-10 julgado' = fração do top-10 que está nos julgamentos; documento não julgado conta como não relevante.")
    grava(args.saida, "modelos_por_consulta", ["consulta", "modelo", "P@10", "AP", "nDCG@10", "top-10 julgado"],
          [[c, m] + [f"{x:.4f}" for x in mods[m][c]] for c in base for m in MODELOS])

    # grade do BM25F
    chaves = list(GRADE)
    cfgs = [dict(zip(chaves, v)) for v in itertools.product(*GRADE.values())]
    res = {i: avalia("bm25f", p) for i, p in enumerate(cfgs)}
    pad = next(i for i, p in enumerate(cfgs) if p == PADRAO)
    grava(args.saida, "bm25f_grade", chaves + ["nDCG@10", "MAP", "P@10"],
          sorted([[p[k] for k in chaves] + [f"{statistics.mean(x[2] for x in res[i].values()):.4f}",
                                             f"{statistics.mean(x[1] for x in res[i].values()):.4f}",
                                             f"{statistics.mean(x[0] for x in res[i].values()):.4f}"]
                  for i, p in enumerate(cfgs)], key=lambda l: -float(l[len(chaves)])),
          "Grade completa do BM25F (média das 20 consultas; escolhida e medida nas mesmas consultas: otimista).")

    # validação cruzada estratificada pelo tipo
    ordem = sorted(consultas, key=lambda c: (c["tipo"], c["id"]))
    partes = [[c["id"] for c in ordem[i::5]] for i in range(5)]
    cv, linhas = {}, []
    for k, teste in enumerate(partes):
        treino = [c for c in base if c not in teste]
        melhor = max(res, key=lambda i: (statistics.mean(res[i][c][2] for c in treino), -abs(i - pad)))
        for c in teste:
            cv[c] = res[melhor][c][2]
        linhas.append([k + 1, " ".join(teste)] + [cfgs[melhor][x] for x in chaves]
                      + [f"{statistics.mean(res[melhor][c][2] for c in teste):.4f}",
                         f"{statistics.mean(res[pad][c][2] for c in teste):.4f}"])
    grava(args.saida, "bm25f_validacao_cruzada", ["parte", "consultas de teste"] + chaves + ["nDCG@10 teste (escolhida)", "nDCG@10 teste (padrão)"],
          linhas, "5 partes; a configuração é escolhida no treino (16 consultas) e medida nas 4 de teste.")
    d = [cv[c] - res[pad][c][2] for c in base]
    resumo = [["nDCG@10 padrão (K1=1,2 b=0,75 título=2 código=1)", f"{statistics.mean(res[pad][c][2] for c in base):.4f}"],
              ["nDCG@10 com calibração (validação cruzada)", f"{statistics.mean(cv.values()):.4f}"],
              ["diferença média", f"{statistics.mean(d):+.4f}"],
              ["consultas melhores / piores / iguais", f"{sum(x > 1e-9 for x in d)} / {sum(x < -1e-9 for x in d)} / {sum(abs(x) <= 1e-9 for x in d)}"],
              ["p (permutação, 20.000 sorteios, bilateral)", f"{permutacao(d):.4f}"],
              ["p (Wilcoxon, aproximação normal)", f"{wilcoxon(d):.4f}"]]
    grava(args.saida, "bm25f_teste_pareado", ["medida", "valor"], resumo,
          "Teste pareado por consulta: calibração por validação cruzada × padrões.")
    for l in resumo:
        print(f"{l[0]}: {l[1]}")
    print(open(os.path.join(args.saida, "modelos_resumo.md"), encoding="utf-8").read())
    print(open(os.path.join(args.saida, "bm25f_validacao_cruzada.md"), encoding="utf-8").read())


if __name__ == "__main__":
    main()
