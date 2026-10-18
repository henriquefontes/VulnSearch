# verificar_indice.py - confere o índice gravado contra um índice em memória
# Uso: python verificar_indice.py ENTRADA [--indice indice] [--termos 2000]
#   ENTRADA é o mesmo arquivo usado na indexação (corpus ou campos.jsonl.gz).
#   Refaz a análise léxica com os mesmos parâmetros do índice (lidos de
#   estatisticas.json), monta as listas de ocorrências de uma amostra de
#   termos diretamente em memória e compara com as listas lidas do disco
#   (decodificação, gaps, intercalação dos blocos). Use em índices pequenos
#   (--limite/--passo), porque guarda a amostra inteira em memória.
import argparse
import random
import sys
from types import SimpleNamespace

import lexico
from extrair import extrair
from indexar import CAMPOS_TEXTO, PREFIXO_CODIGO, agrupa, le_registros
from indice import Indice


def main():
    p = argparse.ArgumentParser()
    p.add_argument("entrada")
    p.add_argument("--indice", default="indice")
    p.add_argument("--termos", type=int, default=2000, help="termos sorteados")
    a = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    ind = Indice(a.indice)
    par = SimpleNamespace(**ind.estatisticas["parametros"])
    random.seed(1)
    amostra = set(random.sample(sorted(ind.vocabulario), min(a.termos, len(ind.vocabulario))))
    stop = frozenset() if not par.stopwords else lexico.STOPWORDS
    esperado = {t: [] for t in amostra}
    unidade = 0
    tempos = {"leitura": 0.0}
    for pagina, reg in enumerate(le_registros(a.entrada, par.limite, par.passo, tempos)):
        campos = extrair(reg["url"], reg["html"]) if "html" in reg else reg
        termos, _ = lexico.termos_campos([campos[k] for k in CAMPOS_TEXTO], stop, par.stemming)
        cod = []
        if par.codigo and campos["codigo"]:
            cod = lexico.termos_codigo(campos["codigo"], tam_max=par.tam_max_codigo)
        if par.granularidade == "documento":
            grupos = [{**agrupa(termos), **agrupa(cod, PREFIXO_CODIGO)}]
        else:
            partes = {}
            for t, pos in termos:
                partes.setdefault(("t", pos // par.tam_trecho), []).append((t, pos))
            for t, pos in cod:
                partes.setdefault(("c", pos // par.tam_trecho), []).append((t, pos))
            grupos = [agrupa(partes[k], PREFIXO_CODIGO if k[0] == "c" else "")
                      for k in sorted(partes)]
        for d in grupos:
            if not d and par.granularidade == "trecho":
                continue  # trechos vazios não existem; páginas vazias sim
            if ind.pagina(unidade) != pagina:
                sys.exit(f"ERRO: unidade {unidade} deveria pertencer à página {pagina}")
            for t in amostra.intersection(d):
                esperado[t].append((unidade, len(d[t]), d[t] if par.posicoes else None))
            unidade += 1

    erros = 0
    for t in sorted(amostra):
        lido = ind.lista(t)
        df, cf = ind.vocabulario[t][:2]
        if lido != esperado[t] or df != len(lido) or cf != sum(x[1] for x in lido):
            erros += 1
            if erros <= 5:
                print(f"DIFERENTE: {t!r}: índice {lido[:3]}... esperado {esperado[t][:3]}...")
    print(f"{len(amostra)} termos conferidos, {erros} com erro "
          f"({ind.estatisticas['blocos']['quantidade']} blocos, "
          f"compressão={par.compressao}, posições={par.posicoes}, {par.granularidade})")
    sys.exit(1 if erros else 0)


if __name__ == "__main__":
    main()
