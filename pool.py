# pool.py - pooling para os julgamentos de relevância (paradigma de Cranfield)
# Uso: python pool.py [--indice indice] [--consultas consultas.tsv] [--saida julgamentos] [-k 10]
#
# Para cada consulta, junta o top-k de todos os modelos (com os parâmetros
# padrão) e grava julgamentos/pool_<id>.tsv com uma linha por documento e a
# coluna 'relevante' vazia, que o grupo preenche com:
#   0 = não relevante, 1 = relevante, 2 = muito relevante
# Os documentos vêm ordenados por quantos modelos os recuperaram e pela melhor
# posição, mas o grupo deve julgar sem olhar essas colunas.
#
# Rodar de novo NÃO apaga julgamentos: se o arquivo já existe, os valores de
# 'relevante' (e 'observacao') preenchidos são mantidos, e só entram os
# documentos novos. Depois de preencher: python avaliar.py --juntar
import argparse
import csv
import os
import sys

from avaliar import le_consultas
from ranqueamento import MODELOS, Ranqueador

COLUNAS = ["url", "titulo", "site", "relevante", "observacao", "doc", "modelos", "melhor_pos"]


def le_pool(caminho):
    if not os.path.exists(caminho):
        return {}
    with open(caminho, encoding="utf-8", newline="") as f:
        return {l["url"]: l for l in csv.DictReader(f, delimiter="\t")}


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Pool de documentos para julgamento.")
    p.add_argument("--indice", default="indice")
    p.add_argument("--consultas", default="consultas.tsv")
    p.add_argument("--saida", default="julgamentos")
    p.add_argument("-k", type=int, default=10)
    a = p.parse_args()
    os.makedirs(a.saida, exist_ok=True)
    r = Ranqueador.abre(a.indice)
    total, novos_total = 0, 0
    for c in le_consultas(a.consultas):
        achados = {}  # doc -> [(modelo, posição)]
        for m in MODELOS:
            for i, (d, _) in enumerate(r.ranquear(c["consulta"], m, a.k).top, 1):
                achados.setdefault(d, []).append((m, i))
        caminho = os.path.join(a.saida, f"pool_{c['id']}.tsv")
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
        novos = sum(1 for l in linhas if not l["relevante"])
        # documentos julgados antes que saíram do pool continuam no arquivo
        for velho in antigo.values():
            velho["modelos"], velho["_n"] = "", 0
            linhas.append(velho)
        linhas.sort(key=lambda l: (-l["_n"], int(l["melhor_pos"] or 99), l["url"]))
        with open(caminho, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, COLUNAS, delimiter="\t", extrasaction="ignore",
                               lineterminator="\n")
            w.writeheader()
            w.writerows(linhas)
        total += len(linhas)
        novos_total += novos
        print(f"  {c['id']} {c['consulta']!r}: {len(linhas)} documentos "
              f"({novos} sem julgamento) -> {caminho}")
    print(f"{total} documentos no pool, {novos_total} a julgar.")


if __name__ == "__main__":
    main()
