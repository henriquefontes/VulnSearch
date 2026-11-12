# pool.py - pooling para os julgamentos de relevância (paradigma de Cranfield)
# Uso: python pool.py [--modelos tfidf,vetorial,bm25,bm25f] [--profundidade 10]
#                     [--indice indice] [--consultas consultas.tsv] [--saida julgamentos]
#
# Para cada consulta, junta o top-p (p = --profundidade) dos modelos escolhidos
# (com os parâmetros padrão) e grava julgamentos/pool_<id>.tsv com uma linha por
# documento e a coluna 'relevante' vazia, que o grupo preenche com:
#   0 = não relevante, 1 = relevante, 2 = muito relevante
# Os documentos vêm ordenados por quantos modelos os recuperaram e pela melhor
# posição, mas o grupo deve julgar sem olhar essas colunas.
#
# Padrão: 4 modelos (tfidf, vetorial, bm25, bm25f), um de cada família, com
# top-10. Antes de gravar, mostra o total de documentos a julgar em outras
# combinações (8 ou 4 modelos, top-10 ou top-5), para comparar o esforço.
#
# Rodar de novo NÃO apaga julgamentos: os valores de 'relevante' (e
# 'observacao') já preenchidos são mantidos, inclusive de documentos que saíram
# do pool; documentos não julgados que saíram do pool são descartados.
# Depois de preencher: python avaliar.py --juntar
import argparse
import csv
import os
import sys

from avaliar import le_consultas
from ranqueamento import MODELOS, Ranqueador

COLUNAS = ["url", "titulo", "site", "relevante", "observacao", "doc", "modelos", "melhor_pos"]
MODELOS_PADRAO = ("tfidf", "vetorial", "bm25", "bm25f")
COMBINACOES = [(MODELOS, 10, "8 modelos, top-10"), (MODELOS_PADRAO, 10, "4 modelos, top-10"),
               (MODELOS_PADRAO, 5, "4 modelos, top-5"), (MODELOS, 5, "8 modelos, top-5")]


def le_pool(caminho):
    if not os.path.exists(caminho):
        return {}
    with open(caminho, encoding="utf-8", newline="") as f:
        return {l["url"]: l for l in csv.DictReader(f, delimiter="\t")}


def tamanho_pool(tops, modelos, p):
    return len({d for m in modelos for d in tops[m][:p]})


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = argparse.ArgumentParser(description="Pool de documentos para julgamento.")
    a.add_argument("--modelos", default=",".join(MODELOS_PADRAO),
                   help=f"modelos separados por vírgula (padrão: {','.join(MODELOS_PADRAO)}; "
                        f"disponíveis: {','.join(MODELOS)})")
    a.add_argument("--profundidade", type=int, default=10,
                   help="top-p de cada modelo que entra no pool (padrão: 10)")
    a.add_argument("--indice", default="indice")
    a.add_argument("--consultas", default="consultas.tsv")
    a.add_argument("--saida", default="julgamentos")
    args = a.parse_args()
    modelos = [m.strip() for m in args.modelos.split(",") if m.strip()]
    invalidos = [m for m in modelos if m not in MODELOS]
    if invalidos or not modelos:
        sys.exit(f"Modelos inválidos: {invalidos}. Disponíveis: {', '.join(MODELOS)}")
    p = args.profundidade
    r = Ranqueador.abre(args.indice)
    consultas = le_consultas(args.consultas)

    # top de todos os modelos, uma vez por consulta
    k = max(10, p)
    tops = {}
    for c in consultas:
        prep = r.prepara(c["consulta"])
        tops[c["id"]] = {m: [d for d, _ in r.ranquear(None, m, k, prep=prep).top]
                         for m in MODELOS}

    print(f"Documentos a julgar ({len(consultas)} consultas):")
    escolhida = (tuple(modelos), p)
    combinacoes = COMBINACOES + ([] if escolhida in [(tuple(m), q) for m, q, _ in COMBINACOES]
                                 else [(modelos, p, f"{len(modelos)} modelos, top-{p} (escolhida)")])
    for ms, q, nome in combinacoes:
        total = sum(tamanho_pool(t, ms, q) for t in tops.values())
        marca = "  <- gravada" if (tuple(ms), q) == escolhida else ""
        print(f"  {nome:<32} {total:>5} ({total / len(consultas):.1f} por consulta){marca}")

    os.makedirs(args.saida, exist_ok=True)
    total, a_julgar = 0, 0
    for c in consultas:
        achados = {}  # doc -> [(modelo, posição)]
        for m in modelos:
            for i, d in enumerate(tops[c["id"]][m][:p], 1):
                achados.setdefault(d, []).append((m, i))
        caminho = os.path.join(args.saida, f"pool_{c['id']}.tsv")
        antigo = le_pool(caminho)
        linhas = []
        for d, lst in achados.items():
            doc = r.documento(d)
            velho = antigo.pop(doc["url"], {})
            linhas.append({"url": doc["url"], "titulo": doc["titulo"], "site": doc["site"],
                           "relevante": velho.get("relevante", ""),
                           "observacao": velho.get("observacao", ""), "doc": d,
                           "modelos": " ".join(f"{m}:{i}" for m, i in lst),
                           "melhor_pos": min(i for _, i in lst), "_n": len(lst)})
        # documentos que saíram do pool: ficam só se já foram julgados
        for velho in antigo.values():
            if (velho.get("relevante") or "").strip():
                velho["modelos"], velho["melhor_pos"], velho["_n"] = "", "", 0
                linhas.append(velho)
        linhas.sort(key=lambda l: (-l["_n"], int(l["melhor_pos"] or 99), l["url"]))
        with open(caminho, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, COLUNAS, delimiter="\t", extrasaction="ignore",
                               lineterminator="\n")
            w.writeheader()
            w.writerows(linhas)
        n_novos = sum(1 for l in linhas if not (l["relevante"] or "").strip())
        total += len(linhas)
        a_julgar += n_novos
        print(f"  {c['id']} {c['consulta']!r}: {len(linhas)} documentos "
              f"({n_novos} sem julgamento) -> {caminho}")
    print(f"Total: {total} documentos no pool ({', '.join(modelos)}; top-{p}), "
          f"{a_julgar} a julgar.")


if __name__ == "__main__":
    main()
