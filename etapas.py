# etapas.py - efeito de cada etapa do pré-processamento (tabela Reuters-RCV1)
# Uso: python etapas.py [campos.jsonl.gz | corpus.jsonl.gz] [--saida resultados]
#                       [--limite N] [--passo K]
#
# Numa única leitura, aplica as etapas de forma cumulativa, como na tabela do
# Reuters-RCV1 (Manning et al., cap. 5), e conta, após cada uma:
#   vocabulário  nº de termos distintos
#   postings     nº de pares (termo, documento) = índice sem posições
#   tokens       nº de ocorrências = índice com posições
# Etapas: sem filtro -> sem números -> minúsculas e sem acentos -> 30 stopwords
#         -> 150 stopwords -> stemming. Uma última linha mostra o pipeline
#         usado no VulnSearch, que mantém os números (CVEs, versões, IDs).
# Também mede o campo código com vários limites de tamanho de token e lista
# os termos mais frequentes.
# Saídas: etapas.csv/.md, codigo_limite.csv/.md, termos_frequentes.csv
import argparse
import csv
import os
import sys
from collections import Counter

import lexico
from extrair import extrair
from indexar import CAMPOS_TEXTO, le_registros

LIMITES_CODIGO = [8, 16, 24, 32, 48, 64, 0]  # 0 = sem limite


def tabela_md(cabecalho, linhas):
    saida = ["| " + " | ".join(cabecalho) + " |",
             "|" + "|".join("---" if i == 0 else "---:" for i in range(len(cabecalho))) + "|"]
    saida += ["| " + " | ".join(str(x) for x in linha) + " |" for linha in linhas]
    return "\n".join(saida) + "\n"


def grava(pasta, nome, cabecalho, linhas, titulo=""):
    with open(os.path.join(pasta, nome + ".csv"), "w", encoding="utf-8", newline="") as f:
        escritor = csv.writer(f, lineterminator="\n")
        escritor.writerow(cabecalho)
        escritor.writerows(linhas)
    with open(os.path.join(pasta, nome + ".md"), "w", encoding="utf-8", newline="\n") as f:
        if titulo:
            f.write(f"{titulo}\n\n")
        f.write(tabela_md(cabecalho, linhas))


def pct(atual, anterior):
    return f"{100 * (atual - anterior) / anterior:.1f}" if anterior else "-"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser()
    p.add_argument("entrada", nargs="?", default=os.path.join("resultados", "campos.jsonl.gz"))
    p.add_argument("--saida", default="resultados")
    p.add_argument("--limite", type=int, default=0)
    p.add_argument("--passo", type=int, default=1)
    a = p.parse_args()
    os.makedirs(a.saida, exist_ok=True)

    stop30 = lexico.carrega_stopwords(quantas=30)
    stop150 = lexico.STOPWORDS
    nomes = ["sem filtro", "sem números", "minúsculas e sem acentos", "30 stopwords",
             "150 stopwords", "stemming", "VulnSearch (com números, 150 stopwords, stemming)"]
    voc = [set() for _ in nomes]
    postings = [0] * len(nomes)
    tokens = [0] * len(nomes)
    voc_cod = {lim: set() for lim in LIMITES_CODIGO}
    post_cod = dict.fromkeys(LIMITES_CODIGO, 0)
    tok_cod = dict.fromkeys(LIMITES_CODIGO, 0)
    cf_texto, df_texto, cf_cod = Counter(), Counter(), Counter()
    tempos = {"leitura": 0.0}

    n = 0
    for reg in le_registros(a.entrada, a.limite, a.passo, tempos):
        campos = extrair(reg["url"], reg["html"]) if "html" in reg else reg
        s1 = []
        for k in CAMPOS_TEXTO:
            if campos[k]:
                s1 += lexico.tokens(campos[k])
        s2 = [t for t in s1 if not lexico.eh_numero(t)]
        s3 = [lexico.normaliza(t) for t in s2]
        s4 = [t for t in s3 if t not in stop30]
        s5 = [t for t in s4 if t not in stop150]
        s6 = [lexico.stem(t) for t in s5]
        # pipeline do índice: igual a termos_campos (descarta tokens > TAM_MAX_TEXTO)
        s7 = [lexico.stem(t) for t in
              (lexico.normaliza(x) for x in s1 if len(x) <= lexico.TAM_MAX_TEXTO)
              if t not in stop150]
        for i, s in enumerate((s1, s2, s3, s4, s5, s6, s7)):
            distintos = set(s)
            voc[i].update(distintos)
            postings[i] += len(distintos)
            tokens[i] += len(s)
        cf_texto.update(s7)
        df_texto.update(set(s7))

        toks = lexico.tokens_codigo(campos["codigo"]) if campos["codigo"] else []
        for lim in LIMITES_CODIGO:
            maximo = lim or 10**9
            s = [lexico.normaliza(t) for t in toks if lexico.TAM_MIN_CODIGO <= len(t) <= maximo]
            distintos = set(s)
            voc_cod[lim].update(distintos)
            post_cod[lim] += len(distintos)
            tok_cod[lim] += len(s)
            if lim == lexico.TAM_MAX_CODIGO:
                cf_cod.update(s)
        n += 1
        if n % 5000 == 0:
            print(f"  {n} páginas...", file=sys.stderr, flush=True)

    # tabela no formato do Reuters-RCV1: valor, Δ% para a linha anterior, T% para o total
    cab = ["etapa", "vocabulário", "Δ%", "T%", "postings (sem posições)", "Δ%", "T%",
           "tokens (com posições)", "Δ%", "T%"]
    linhas = []
    for i, nome in enumerate(nomes):
        ant = i - 1 if 0 < i < 6 else (0 if i == 6 else None)  # a última compara com a 1ª
        v, pt, tk = len(voc[i]), postings[i], tokens[i]
        linhas.append([nome,
                       v, pct(v, len(voc[ant])) if ant is not None else "-", pct(v, len(voc[0])) if i else "-",
                       pt, pct(pt, postings[ant]) if ant is not None else "-", pct(pt, postings[0]) if i else "-",
                       tk, pct(tk, tokens[ant]) if ant is not None else "-", pct(tk, tokens[0]) if i else "-"])
    grava(a.saida, "etapas", cab, linhas,
          f"Efeito das etapas de pré-processamento (campos de texto, {n} páginas). "
          "Δ% = variação em relação à linha anterior; T% = em relação à primeira linha. "
          "A última linha é o pipeline do VulnSearch, comparado à primeira.")

    cab = ["limite de tamanho", "vocabulário", "postings", "tokens", "% vocabulário sem limite"]
    linhas = []
    for lim in LIMITES_CODIGO:
        linhas.append([lim or "sem limite", len(voc_cod[lim]), post_cod[lim], tok_cod[lim],
                       f"{100 * len(voc_cod[lim]) / max(1, len(voc_cod[0])):.1f}"])
    vt = len(voc[6])
    vc = len(voc_cod[lexico.TAM_MAX_CODIGO])
    linhas.append([f"texto + código (limite {lexico.TAM_MAX_CODIGO})", vt + vc,
                   postings[6] + post_cod[lexico.TAM_MAX_CODIGO],
                   tokens[6] + tok_cod[lexico.TAM_MAX_CODIGO], "-"])
    grava(a.saida, "codigo_limite", cab, linhas,
          f"Campo código: efeito do limite de tamanho de token (tokens de 1 caractere "
          f"sempre descartados). Para comparação, o texto tem vocabulário {vt} e {tokens[6]} tokens.")

    with open(os.path.join(a.saida, "termos_frequentes.csv"), "w", encoding="utf-8",
              newline="\n") as f:
        f.write("posicao,termo_texto,cf,df,termo_codigo,cf_codigo\n")
        topo_t, topo_c = cf_texto.most_common(100), cf_cod.most_common(100)
        for i in range(100):
            t, cf = topo_t[i] if i < len(topo_t) else ("", "")
            c, cfc = topo_c[i] if i < len(topo_c) else ("", "")
            f.write(f"{i + 1},{t},{cf},{df_texto.get(t, '')},{c},{cfc}\n")

    print(open(os.path.join(a.saida, "etapas.md"), encoding="utf-8").read())
    print(open(os.path.join(a.saida, "codigo_limite.md"), encoding="utf-8").read())


if __name__ == "__main__":
    main()
