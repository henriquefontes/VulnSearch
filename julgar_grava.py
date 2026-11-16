# julgar_grava.py - grava os julgamentos de uma consulta a partir dos rótulos cegos
# Uso: python julgar_grava.py q05 arquivo.tsv [--avaliador NOME]
# arquivo.tsv: uma linha por documento: rótulo (d1, d2... da julgar_leitura.py) <TAB> 0|1|2
#              <TAB> justificativa curta. Todos os documentos do pool precisam aparecer.
# Grava pela mesma rotina da página /julgar (julgamento.Julgamentos.julga).
import argparse
import sys

from julgamento import Julgamentos, le_tsv
from julgar_leitura import AVALIADOR


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = argparse.ArgumentParser()
    a.add_argument("consulta")
    a.add_argument("arquivo")
    a.add_argument("--avaliador", default=AVALIADOR)
    args = a.parse_args()
    j = Julgamentos()
    _, linhas = le_tsv(j.caminho(args.consulta))
    ordem = j.ordem(args.consulta, args.avaliador, {l["url"] for l in linhas})
    rotulo = {f"d{i}": u for i, u in enumerate(ordem, 1)}
    notas = {}
    with open(args.arquivo, encoding="utf-8") as f:
        for n, l in enumerate(f, 1):
            if not l.strip():
                continue
            p = l.rstrip("\n").split("\t")
            if len(p) != 3 or p[0] not in rotulo or p[1] not in ("0", "1", "2") or not p[2].strip():
                sys.exit(f"linha {n} inválida: {l!r}")
            if p[0] in notas:
                sys.exit(f"linha {n}: {p[0]} repetido")
            notas[p[0]] = (p[1], p[2].strip())
    faltam = sorted(set(rotulo) - set(notas), key=lambda x: int(x[1:]))
    if faltam:
        sys.exit(f"faltam julgamentos: {', '.join(faltam)}")
    onde = {}
    for r, (v, obs) in notas.items():
        x = j.julga(args.consulta, rotulo[r], v, obs, args.avaliador)
        onde[x] = onde.get(x, 0) + 1
    cont = {v: sum(1 for x, _ in notas.values() if x == v) for v in ("2", "1", "0")}
    print(f"{args.consulta}: {len(notas)} julgamentos gravados {onde}; notas 2/1/0 = "
          f"{cont['2']}/{cont['1']}/{cont['0']}")


if __name__ == "__main__":
    main()
