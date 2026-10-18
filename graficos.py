# graficos.py - gráficos (PNG) para o relatório, a partir de resultados/
# Uso: python graficos.py [--resultados resultados] [--indice indice]
#   Requer matplotlib, usado só aqui (pip install matplotlib). Os demais
#   scripts não dependem dele; as tabelas em CSV/Markdown bastam sem os gráficos.
# Gera em resultados/:
#   heaps.png          crescimento do vocabulário (log-log, ordem aleatória) e ajuste
#   heaps_ordem_corpus.png  o mesmo na ordem do corpus, que é agrupado por site
#   etapas.png         % de vocabulário, postings e tokens após cada etapa
#   variacoes.png      tamanho do índice em cada variação, por arquivo
#   codigo_limite.png  vocabulário do código x limite de tamanho de token
import argparse
import csv
import math
import os
import sys

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:
    sys.exit("Este script precisa do matplotlib: pip install matplotlib")

# paleta categórica (3 primeiras posições, validadas para daltonismo) e tinta
AZUL, LARANJA, VERDE = "#2a78d6", "#eb6834", "#1baf7a"
TINTA, TINTA2, GRADE, FUNDO = "#0b0b0b", "#52514e", "#e4e3df", "#ffffff"

plt.rcParams.update({
    "figure.facecolor": FUNDO, "axes.facecolor": FUNDO, "savefig.facecolor": FUNDO,
    "axes.edgecolor": GRADE, "axes.labelcolor": TINTA2, "text.color": TINTA,
    "xtick.color": TINTA2, "ytick.color": TINTA2, "axes.grid": True,
    "grid.color": GRADE, "grid.linewidth": 0.8, "axes.spines.top": False,
    "axes.spines.right": False, "font.size": 10, "axes.titlesize": 11,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "legend.frameon": False,
    "lines.linewidth": 2,
})


def le_csv(caminho):
    with open(caminho, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def salva(fig, pasta, nome):
    caminho = os.path.join(pasta, nome)
    fig.savefig(caminho, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("  " + caminho)


def grafico_heaps(res, indice, curva, ordem, nome, titulo, marcar_sites):
    pontos = le_csv(os.path.join(res, curva))
    ajuste = {}
    if os.path.exists(os.path.join(res, "heaps.csv")):
        ajuste = {l["vocabulário de"]: l for l in le_csv(os.path.join(res, "heaps.csv"))
                  if l["ordem das páginas"].startswith(ordem)}
    # início de cada site (o corpus está agrupado por site): marcador na curva
    inicios = []
    caminho_docs = os.path.join(indice, "documentos.tsv")
    if marcar_sites and os.path.exists(caminho_docs):
        anterior = None
        with open(caminho_docs, encoding="utf-8") as f:
            next(f)
            for linha in f:
                partes = linha.split("\t")
                if partes[2] != anterior:
                    inicios.append((int(partes[0]), partes[2].replace("www.", "")))
                    anterior = partes[2]
    paginas = [int(p["paginas"]) for p in pontos]

    fig, ax = plt.subplots(figsize=(7, 4.4))
    series = [("texto", "termos_texto", "vocabulario_texto", AZUL),
              ("texto + código", "termos_total", "vocabulario_total", LARANJA)]
    for s_i, (rotulo, cn, cv, cor) in enumerate(series):
        n = [float(p[cn]) for p in pontos]
        v = [float(p[cv]) for p in pontos]
        ax.plot(n, v, color=cor, label=rotulo, zorder=2)
        if rotulo in ajuste:
            k, b = float(ajuste[rotulo]["K"]), float(ajuste[rotulo]["b"])
            ax.plot(n, [k * x ** b for x in n], color=cor, linewidth=1, linestyle="--",
                    alpha=0.8, zorder=1)
            ax.annotate(f"V = {k:.2g}·n^{b:.2f}", (n[-1], v[-1]), xytext=(4, -4),
                        textcoords="offset points", ha="left", va="top", color=TINTA, fontsize=9)
        for j, (pag, site) in enumerate(inicios[1:]):
            # ponto da curva mais próximo do início do site
            i = min(range(len(paginas)), key=lambda k_: abs(paginas[k_] - pag))
            ax.plot([n[i]], [v[i]], marker="o", markersize=7, markerfacecolor=FUNDO,
                    markeredgecolor=cor, markeredgewidth=1.5, zorder=3)
            if s_i == 1:  # rótulo do site só na curva de cima, alternando a altura
                ax.annotate(site, (n[i], v[i]), xytext=(-4, 10 + 11 * (j % 2)),
                            textcoords="offset points", ha="right", fontsize=7, color=TINTA2)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("termos indexados lidos (n)")
    ax.set_ylabel("tamanho do vocabulário (V)")
    ax.set_title(titulo)
    ax.legend(loc="upper left")
    salva(fig, res, nome)


def grafico_etapas(res):
    # colunas repetidas (Δ%, T%): lido por posição
    with open(os.path.join(res, "etapas.csv"), encoding="utf-8") as f:
        linhas = list(csv.reader(f))[1:7]
    rotulos = [l[0] for l in linhas]
    fig, ax = plt.subplots(figsize=(7, 4))
    medidas = [("vocabulário", 1, AZUL), ("postings (sem posições)", 4, LARANJA),
               ("tokens (com posições)", 7, VERDE)]
    x = range(len(rotulos))
    for nome, col, cor in medidas:
        base = float(linhas[0][col])
        ys = [100 * float(l[col]) / base for l in linhas]
        ax.plot(x, ys, color=cor, marker="o", markersize=6, label=nome)
        ax.annotate(f"{ys[-1]:.0f}%", (x[-1], ys[-1]), xytext=(8, 0),
                    textcoords="offset points", va="center", fontsize=9, color=TINTA)
    ax.set_xticks(list(x))
    ax.set_xticklabels([r.replace(" e ", "\ne ").replace(" stopwords", "\nstopwords")
                        for r in rotulos], fontsize=8)
    ax.set_ylabel("% do valor sem filtro")
    ax.set_ylim(0, 105)
    ax.set_title("Efeito acumulado de cada etapa do pré-processamento")
    ax.legend(loc="lower left")
    salva(fig, res, "etapas.png")


def grafico_variacoes(res):
    linhas = le_csv(os.path.join(res, "variacoes.csv"))
    linhas = [l for l in linhas if l["variação"] not in ("principal", "bloco_16", "bloco_256")]
    nomes = [l["variação"] for l in linhas]
    partes = [("ocorrências", "ocorrências (MB)", AZUL), ("vocabulário", "vocabulário (MB)", LARANJA),
              ("documentos", "documentos (MB)", VERDE)]
    fig, ax = plt.subplots(figsize=(7, 0.42 * len(nomes) + 1.2))
    esquerda = [0.0] * len(nomes)
    y = list(range(len(nomes)))[::-1]
    for rotulo, col, cor in partes:
        valores = [float(l[col]) for l in linhas]
        ax.barh(y, valores, left=esquerda, color=cor, height=0.62, label=rotulo,
                edgecolor=FUNDO, linewidth=1.5)
        esquerda = [e + v for e, v in zip(esquerda, valores)]
    for yi, total in zip(y, esquerda):
        ax.text(total, yi, f" {total:.0f} MB" if total >= 10 else f" {total:.1f} MB", va="center", fontsize=8, color=TINTA)
    ax.set_yticks(y)
    ax.set_yticklabels(nomes, fontsize=8)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("tamanho do índice (MB)")
    ax.set_xlim(0, max(esquerda) * 1.15)
    ax.set_title("Tamanho do índice por variação da representação")
    ax.legend(loc="lower right", fontsize=8)
    salva(fig, res, "variacoes.png")


def grafico_codigo(res):
    linhas = [l for l in le_csv(os.path.join(res, "codigo_limite.csv"))
              if not l["limite de tamanho"].startswith("texto")]
    rotulos = [l["limite de tamanho"] for l in linhas]
    voc = [int(l["vocabulário"]) / 1000 for l in linhas]
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.plot(range(len(voc)), voc, color=AZUL, marker="o", markersize=6)
    for i, v in enumerate(voc):
        ax.annotate(f"{v:.0f} mil", (i, v), xytext=(0, 8), textcoords="offset points",
                    ha="center", fontsize=8, color=TINTA)
    ax.set_xticks(range(len(rotulos)))
    ax.set_xticklabels(rotulos)
    ax.set_xlabel("maior token aceito no campo código (caracteres)")
    ax.set_ylabel("vocabulário do código (mil termos)")
    ax.set_ylim(0, max(voc) * 1.18)
    ax.set_title("Campo código: vocabulário x limite de tamanho de token")
    salva(fig, res, "codigo_limite.png")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--resultados", default="resultados")
    p.add_argument("--indice", default="indice")
    a = p.parse_args()
    print("Gráficos:")
    for nome, f in (("heaps_curva_aleatoria.csv", lambda: grafico_heaps(
                        a.resultados, a.indice, "heaps_curva_aleatoria.csv", "aleatória",
                        "heaps.png", "Lei de Heaps: crescimento do vocabulário "
                        "(páginas em ordem aleatória)", False)),
                    ("heaps_curva.csv", lambda: grafico_heaps(
                        a.resultados, a.indice, "heaps_curva.csv", "do corpus",
                        "heaps_ordem_corpus.png", "Crescimento do vocabulário na ordem do "
                        "corpus (○ = início de um site)", True)),
                    ("etapas.csv", lambda: grafico_etapas(a.resultados)),
                    ("variacoes.csv", lambda: grafico_variacoes(a.resultados)),
                    ("codigo_limite.csv", lambda: grafico_codigo(a.resultados))):
        if os.path.exists(os.path.join(a.resultados, nome)):
            f()
        else:
            print(f"  (sem {nome}; rode medir.py antes)")


if __name__ == "__main__":
    main()
