# medir_ranking.py - experimentos do ranqueamento (etapa 3)
# Uso: python medir_ranking.py [--indice indice] [--saida resultados_etapa3] [--reps 5]
#   Depois: python graficos.py --etapa3   (gráficos PNG, requer matplotlib)
#
# Lê as consultas de consultas.tsv e grava em --saida (CSV + Markdown):
#   preparacao        custo do pré-processamento (preparar_ranking.py)
#   custo_modelos     latência por modelo (média/mediana/máx.), candidatos, postings
#   latencia          o mesmo por consulta e modelo
#   heap_sorted       top-k com min-heap × sorted × heapq.nlargest
#   sobreposicao      sobreposição do top-10 entre pares de modelos
#   perfil_top10      sites e tamanho médio dos documentos no top-10 de cada modelo
#   sensibilidade_bm25  K₁ × b: sobreposição com o padrão e tamanho dos documentos
#   bm25f_pesos       peso do título × peso do código no BM25F
#   alfa_codigo       peso α do código nos modelos sem campos
#   idf_variantes     IDF limitado a 0 × log(1 + ·) × fórmula sem correção
#   stopwords_dominio IDF dos rótulos da ficha, letras do CVSS e termos raros
#   qualitativo       top-5 de cada modelo para 4 consultas (.md e .csv)
#   explicar          exemplos de --explicar (IDF e efeito do título)
#   resumo.json       números principais
import argparse
import csv
import heapq
import json
import os
import statistics
import sys
import time

import lexico
from etapas import grava
from indice import pico_memoria_mb
from ranqueamento import MODELOS, Ranqueador, idf_bm, idf_peso, top_k

K = 10
SITES = ["www.exploit-db.com", "github.com", "www.rapid7.com", "cwe.mitre.org",
         "www.drupal.org", "developer.joomla.org"]
CURTO = {"www.exploit-db.com": "exploit-db", "github.com": "github", "www.rapid7.com": "rapid7",
         "cwe.mitre.org": "cwe", "www.drupal.org": "drupal", "developer.joomla.org": "joomla"}
# consultas extras para o experimento do IDF (termos com df > N/2)
EXTRAS_IDF = ["wordpress vulnerability", "exploit linux kernel", "cve sql injection",
              "vulnerability", "source code disclosure", "exploit", "cve"]
QUALITATIVAS = ["q01", "q05", "q12", "q18"]  # uma de cada tipo


def le_consultas(caminho="consultas.tsv"):
    with open(caminho, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def f2(x):
    return f"{x:.2f}"


def media(v):
    return sum(v) / len(v) if v else 0.0


class Medidor:
    def __init__(self, r, consultas):
        self.r = r
        self.consultas = consultas
        self.preps = {c["id"]: r.prepara(c["consulta"]) for c in consultas}
        self._no_titulo, self._docs = {}, {}

    def top(self, cid, modelo, **params):
        return [d for d, _ in self.r.ranquear(None, modelo, K, prep=self.preps[cid],
                                              **params).top]

    def no_titulo(self, cid, d):
        """Algum termo de texto da consulta aparece no título do documento?"""
        _, q = self.preps[cid]
        lim = self.r.col.limite_titulo[d]
        for t in q.texto:
            mapa = self._no_titulo.get(t)
            if mapa is None:
                mapa = self._no_titulo[t] = {dd: p[0] for dd, _, p in q.lista(t)}
            if d in mapa and mapa[d] < lim:
                return True
        return False

    def so_codigo(self, cid, d):
        """O documento só casa com a consulta pelo código?"""
        _, q = self.preps[cid]
        for t in q.texto:
            docs = self._docs.get(t)
            if docs is None:
                docs = self._docs[t] = {dd for dd, _, _ in q.lista(t)}
            if d in docs:
                return False
        return True

    def perfil(self, docs):
        col = self.r.col
        return (media([col.n_texto[d] for d in docs]), media([col.n_codigo[d] for d in docs]))


def sobrep(a, b):
    if not a and not b:
        return 1.0
    return len(set(a) & set(b)) / max(len(a), len(b))


def sobrep_txt(a, b):
    return "-" if not a and not b else f2(sobrep(a, b))


# ------------------------------------------------------------- experimentos
def custo(m, reps, saida):
    r = m.r
    linhas, por_modelo = [], {mod: [] for mod in MODELOS}
    for c in m.consultas:
        for mod in MODELOS:
            r.ranquear(c["consulta"], mod, K)  # aquece o cache do disco
            tempos = []
            for _ in range(reps):
                res = r.ranquear(c["consulta"], mod, K)
                tempos.append(res.ms)
            por_modelo[mod].append((tempos, res))
            linhas.append([c["id"], c["consulta"], mod, res.n_candidatos, res.n_positivos,
                           res.postings, f2(media(tempos)), f2(statistics.median(tempos)),
                           f2(max(tempos))])
    grava(saida, "latencia", ["id", "consulta", "modelo", "candidatos", "escore > 0",
                              "postings lidos", "ms média", "ms mediana", "ms máx."], linhas,
          f"Latência por consulta e modelo ({reps} repetições após 1 de aquecimento, k = {K}).")
    resumo = []
    for mod in MODELOS:
        todos = [t for ts, _ in por_modelo[mod] for t in ts]
        meds = [statistics.median(ts) for ts, _ in por_modelo[mod]]
        resumo.append([mod, f2(media(todos)), f2(statistics.median(meds)), f2(max(todos)),
                       round(media([x.n_candidatos for _, x in por_modelo[mod]])),
                       round(media([x.postings for _, x in por_modelo[mod]]))])
    grava(saida, "custo_modelos", ["modelo", "ms média", "ms mediana (das medianas)", "ms máx.",
                                   "candidatos (média)", "postings lidos (média)"], resumo,
          f"Custo por modelo nas {len(m.consultas)} consultas de consultas.tsv ({reps} "
          "repetições cada, cache do disco aquecido; inclui análise da consulta, leitura das "
          "listas, acumulação e top-k).")
    return resumo


def heap_sorted(r, saida, reps=5):
    linhas = []
    for consulta in ["exploit", "vulnerability", "cve", "remote code execution",
                     "sql injection"]:
        esc = r.escores(consulta, "bm25", idf="log1p")
        t = {"heap": [], "sorted": [], "nlargest": []}
        for _ in range(reps):
            a = time.perf_counter()
            x = top_k(esc, K)
            b = time.perf_counter()
            y = sorted(esc.items(), key=lambda p: (-p[1], p[0]))[:K]
            c = time.perf_counter()
            heapq.nlargest(K, esc.items(), key=lambda p: (p[1], -p[0]))
            d = time.perf_counter()
            assert x == y
            t["heap"].append((b - a) * 1000)
            t["sorted"].append((c - b) * 1000)
            t["nlargest"].append((d - c) * 1000)
        h, s, n = (statistics.median(t[k]) for k in ("heap", "sorted", "nlargest"))
        linhas.append([consulta, len(esc), f2(h), f2(s), f2(n), f2(s / h)])
    grava(saida, "heap_sorted", ["consulta", "candidatos (N)", "min-heap ms", "sorted ms",
                                 "heapq.nlargest ms", "sorted / min-heap"], linhas,
          f"Seleção do top-{K}: min-heap de tamanho k (O(N log k), slides 07-20 a 07-36) × "
          "ordenar todos os candidatos (O(N log N)). BM25 com IDF log(1 + ·), para que todos "
          f"os candidatos tenham escore > 0. Mediana de {reps} execuções; os dois dão o mesmo "
          "top-k.")
    return linhas


def sobreposicao(m, saida):
    tops = {c["id"]: {mod: m.top(c["id"], mod) for mod in MODELOS} for c in m.consultas}
    linhas = []
    for a in MODELOS:
        linhas.append([a] + [f2(media([sobrep(tops[c][a], tops[c][b]) for c in tops]))
                             for b in MODELOS])
    grava(saida, "sobreposicao", ["modelo"] + list(MODELOS), linhas,
          f"Sobreposição média do top-{K} entre modelos (|A ∩ B| / max(|A|, |B|)), "
          f"nas {len(tops)} consultas.")
    return tops


def perfil_top10(m, tops, saida):
    col, ind = m.r.col, m.r.ind
    linhas = []
    for mod in MODELOS:
        docs = [d for c in tops for d in tops[c][mod]]
        sites = [ind.documentos[d]["site"] for d in docs]
        nt, nc = m.perfil(docs)
        linhas.append([mod, len(docs)] + [f"{100 * sites.count(s) / len(docs):.0f}"
                                           for s in SITES] + [f"{nt:.0f}", f"{nc:.0f}",
                                                               f"{nt + nc:.0f}"])
    todos = range(col.N)
    sites = [d["site"] for d in ind.documentos]
    nt, nc = m.perfil(todos)
    linhas.append(["(coleção)", col.N] + [f"{100 * sites.count(s) / col.N:.0f}" for s in SITES]
                  + [f"{nt:.0f}", f"{nc:.0f}", f"{nt + nc:.0f}"])
    grava(saida, "perfil_top10", ["modelo", "documentos"] + [f"% {CURTO[s]}" for s in SITES]
          + ["termos de texto (média)", "termos de código (média)", "total (média)"], linhas,
          f"Site e tamanho dos documentos no top-{K} de cada modelo (todas as consultas somadas). "
          "Hipótese (slide 08-38): sem normalização (TF-IDF, BM15) os documentos longos são "
          "favorecidos.")
    return linhas


def sensibilidade_bm25(m, saida):
    ids = [c["id"] for c in m.consultas]
    padrao = {c: m.top(c, "bm25") for c in ids}
    linhas = []
    for k1 in (0.5, 0.9, 1.2, 1.5, 2.0):
        for b in (0.0, 0.25, 0.5, 0.75, 1.0):
            tops = {c: m.top(c, "bm25", k1=k1, b=b) for c in ids}
            docs = [d for c in ids for d in tops[c]]
            nt, nc = m.perfil(docs)
            linhas.append([k1, b, f2(media([sobrep(tops[c], padrao[c]) for c in ids])),
                           f"{nt:.0f}", f"{nc:.0f}"])
    grava(saida, "sensibilidade_bm25", ["K1", "b", "sobreposição com K1=1,2 b=0,75",
                                        "termos de texto (média top-10)",
                                        "termos de código (média top-10)"], linhas,
          "Sensibilidade do BM25 a K₁ e b (b = 0 é o BM15; b = 1 é o BM11).")
    return linhas


def bm25f_pesos(m, saida):
    ids = [c["id"] for c in m.consultas]
    padrao = {c: m.top(c, "bm25f") for c in ids}
    ind = m.r.ind
    linhas = []
    for pt in (1, 2, 3, 5):
        for pc in (0, 0.5, 1):
            tops = {c: m.top(c, "bm25f", peso_titulo=pt, peso_codigo=pc) for c in ids}
            pares = [(c, d) for c in ids for d in tops[c]]
            nt, nc = m.perfil([d for _, d in pares])
            tit = media([m.no_titulo(c, d) for c, d in pares])
            edb = media([ind.documentos[d]["site"] == SITES[0] for _, d in pares])
            linhas.append([pt, pc, f2(media([sobrep(tops[c], padrao[c]) for c in ids])),
                           f"{100 * tit:.0f}", f"{100 * edb:.0f}", f"{nt:.0f}", f"{nc:.0f}"])
    grava(saida, "bm25f_pesos", ["peso título", "peso código", "sobreposição com o padrão (2; 1)",
                                 "% do top-10 com termo no título", "% exploit-db",
                                 "termos de texto (média)", "termos de código (média)"], linhas,
          "BM25F: peso do título × peso do código (peso do corpo = 1; b = 0,75 nos três "
          "campos; K₁ = 1,2).")
    return linhas


def alfa_codigo(m, saida):
    ids = [c["id"] for c in m.consultas]
    ind = m.r.ind
    linhas = []
    for mod in ("jaccard", "tfidf", "vetorial", "bm25"):
        ref = {c: m.top(c, mod, peso_codigo=1.0) for c in ids}
        for a in (0, 0.25, 0.5, 1):
            tops = {c: m.top(c, mod, peso_codigo=a) for c in ids}
            pares = [(c, d) for c in ids for d in tops[c]]
            nt, nc = m.perfil([d for _, d in pares])
            so_cod = media([m.so_codigo(c, d) for c, d in pares])
            edb = media([ind.documentos[d]["site"] == SITES[0] for _, d in pares])
            linhas.append([mod, a, f2(media([sobrep(tops[c], ref[c]) for c in ids])),
                           len(pares), f"{100 * so_cod:.0f}", f"{100 * edb:.0f}",
                           f"{nt:.0f}", f"{nc:.0f}"])
    grava(saida, "alfa_codigo", ["modelo", "α", "sobreposição com α = 1", "documentos no top-10",
                                 "% só com casamento no código", "% exploit-db",
                                 "termos de texto (média)", "termos de código (média)"], linhas,
          "Peso α do código nos modelos sem campos: escore = texto + α·código (D9). "
          "Com α = 0, as consultas codigo:... não têm resultado.")
    return linhas


def idf_variantes(r, consultas, saida):
    N = r.N
    lista = [(c["id"], c["consulta"]) for c in consultas] + \
        [(f"x{i + 1}", q) for i, q in enumerate(EXTRAS_IDF)]
    linhas = []
    for cid, consulta in lista:
        prep = r.prepara(consulta)
        _, q = prep
        altos = [t for t in list(q.texto) + list(q.codigo) if q.df(t) > N / 2]
        if not altos:
            continue
        for mod in ("bm25", "bm25f"):
            res = {v: r.ranquear(None, mod, K, prep=prep, idf=v) for v in
                   ("limitado+recurso", "limitado", "log1p", "bruto")}
            tops = {v: [d for d, _ in x.top] for v, x in res.items()}
            padrao = res["limitado+recurso"]
            linhas.append([cid, consulta, mod,
                           " ".join(f"{t}({q.df(t)}; {idf_bm(q.df(t), N, variante='bruto'):.2f})"
                                    for t in altos),
                           "sim" if padrao.recurso else "não", padrao.n_positivos,
                           res["limitado"].n_positivos, res["log1p"].n_positivos,
                           res["bruto"].n_positivos,
                           sobrep_txt(tops["limitado+recurso"], tops["limitado"]),
                           sobrep_txt(tops["limitado+recurso"], tops["log1p"]),
                           sobrep_txt(tops["limitado+recurso"], tops["bruto"])])
    grava(saida, "idf_variantes", ["id", "consulta", "modelo",
                                   "termos com df > N/2 (df; idf sem correção)", "recurso usado",
                                   "escore > 0 (limitado+recurso)", "escore > 0 (limitado)",
                                   "escore > 0 (log1p)", "escore > 0 (sem correção)",
                                   "sobreposição padrão × limitado", "sobreposição padrão × log1p",
                                   "sobreposição padrão × sem correção"], linhas,
          "IDF da família BM: log((N − n + 0,5)/(n + 0,5)) é negativo para n > N/2 (D10). "
          "Padrão: 'limitado+recurso' (limitado a 0; se todas as palavras ficarem com idf 0, "
          "a consulta usa log(1 + ·)). 'sem correção' é a fórmula do slide. Consultas x1-x7 "
          "são extras, só para este experimento.")
    return linhas


def stopwords_dominio(r, saida):
    N = r.N
    grupos = [("rótulo da ficha do exploit-db", ["edb", "author", "type", "platform", "date",
                                                  "verifi", "exploit", "tag"]),
              ("comum no corpus", ["cve", "vulner", "advisori", "sourc", "id", "link"]),
              ("letra do vetor CVSS", ["av", "ac", "pr", "ui", "n", "l", "h", "u"]),
              ("termo raro (consulta)", [lexico.stem(w) for w in
                                          ("log4j", "strcpy", "struts", "deserialization",
                                           "openssh", "csrf")])]
    linhas = []
    for grupo, termos in grupos:
        for t in termos:
            e = r.ind.vocabulario.get(t)
            if not e:
                continue
            n = e[0]
            linhas.append([grupo, t, n, f"{100 * n / N:.1f}", f"{idf_peso(n, N):.3f}",
                           f"{idf_bm(n, N):.3f}", f"{idf_bm(n, N, variante='log1p'):.3f}",
                           f"{idf_bm(n, N, variante='bruto'):.3f}"])
    grava(saida, "stopwords_dominio", ["grupo", "termo", "df", "% dos docs", "idf log₂(N/n)",
                                       "idf BM limitado", "idf BM log1p", "idf BM sem correção"],
          linhas, "\"Stopwords do domínio\" (D12): o IDF rebaixa os rótulos da ficha do "
                  "exploit-db e as letras do CVSS sem uma lista nova de stopwords.")
    return linhas


def qualitativo(m, saida):
    r, ind = m.r, m.r.ind
    linhas, md = [], ["# Exemplos qualitativos: top-5 de cada modelo\n"]
    porid = {c["id"]: c for c in m.consultas}
    for cid in QUALITATIVAS:
        c = porid[cid]
        md.append(f"\n## {cid} ({c['tipo']}): `{c['consulta']}`\n")
        md.append("| modelo | pos. | escore | site | título |\n|---|---:|---:|---|---|")
        for mod in MODELOS:
            res = r.ranquear(None, mod, 5, prep=m.preps[cid])
            for i, (d, s) in enumerate(res.top, 1):
                doc = ind.documentos[d]
                tit = (doc["titulo"] or doc["url"])[:90].replace("|", "/")
                linhas.append([cid, c["consulta"], mod, i, f"{s:.4f}", CURTO.get(doc["site"]),
                               tit, doc["url"]])
                md.append(f"| {mod if i == 1 else ''} | {i} | {s:.4f} | "
                          f"{CURTO.get(doc['site'])} | {tit} |")
    with open(os.path.join(saida, "qualitativo.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["id", "consulta", "modelo", "pos", "escore", "site", "titulo", "url"])
        w.writerows(linhas)
    with open(os.path.join(saida, "qualitativo.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")


def explicar(r, saida):
    from ranquear import fmt

    def bloco(titulo, consulta, modelo, k=3, **params):
        res = r.ranquear(consulta, modelo, k, explicar=True, **params)
        p = ", ".join(f"{a}={b}" for a, b in params.items())
        out = [f"\n### {titulo}\n", f"`python ranquear.py \"{consulta}\" --modelo {modelo}"
               f"{' ' + p if p else ''} -k {k} --explicar`\n", "```"]
        for i, (d, s) in enumerate(res.top, 1):
            doc = r.documento(d)
            out.append(f"{i}. {s:.4f}  {CURTO.get(doc['site'])}  {doc['titulo'][:80]}")
            for parcela in res.detalhes.get(d, []):
                out.append("     · " + "  ".join(f"{a} {fmt(b)}" for a, b in parcela.items()))
        out.append("```")
        return out

    md = ["# Exemplos de --explicar\n",
          "## IDF baixo de um termo comum × IDF alto de um termo raro"]
    md += bloco("TF-IDF: 'exploit' (df alto) e 'strcpy' (df baixo)", "exploit strcpy", "tfidf")
    md += bloco("BM25: o IDF de 'exploit' (df > N/2) é limitado a 0", "exploit strcpy", "bm25")
    md += ["\n## Efeito do título no BM25F"]
    for pt in (1, 5):
        md += bloco(f"BM25F com peso do título {pt}", "sql injection wordpress plugin", "bm25f",
                    k=5, peso_titulo=pt)
    with open(os.path.join(saida, "explicar.md"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(md) + "\n")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser()
    p.add_argument("--indice", default="indice")
    p.add_argument("--saida", default="resultados_etapa3")
    p.add_argument("--consultas", default="consultas.tsv")
    p.add_argument("--reps", type=int, default=5)
    a = p.parse_args()
    os.makedirs(a.saida, exist_ok=True)
    inicio = time.perf_counter()

    t = time.perf_counter()
    r = Ranqueador.abre(a.indice)
    carga = time.perf_counter() - t
    mem_carga = pico_memoria_mb()
    consultas = le_consultas(a.consultas)
    meta = r.col.meta

    def etapa(nome, f, *args):
        t0 = time.perf_counter()
        x = f(*args)
        print(f"  {nome}: {time.perf_counter() - t0:.0f} s", flush=True)
        return x

    tp = meta["tempos_s"]
    fm = meta["formatos"]
    grava(a.saida, "preparacao", ["item", "valor"], [
        ["documentos (N)", meta["N"]],
        ["tempo: títulos (s)", tp["titulos"]], ["tempo: passada nas ocorrências (s)", tp["passada"]],
        ["tempo: gravação (s)", tp["gravacao"]], ["tempo total (s)", tp["total"]],
        ["pico de memória (MB)", f"{meta['memoria_pico_mb']:.0f}"],
        ["formato escolhido", meta["formato"]],
        ["documentos_ranking.bin (MB)", f"{fm['bin']['tamanho_mb']:.2f}"],
        ["documentos_ranking.tsv (MB)", f"{fm['tsv']['tamanho_mb']:.2f}"],
        ["leitura .bin (s)", fm["bin"]["leitura_s"]], ["leitura .tsv (s)", fm["tsv"]["leitura_s"]],
        ["arquivos novos no índice (MB)", f"{meta['tamanho_mb']:.2f}"],
        ["carga do Ranqueador (s)", f2(carga)],
        ["pico de memória após a carga (MB)", f"{mem_carga:.0f}"],
    ] + [[f"média de len: {k}", f"{v:.2f}"] for k, v in meta["medias"].items()]
      + [[f"documentos com {k}", v] for k, v in meta["docs_com_campo"].items()],
        "Custo do pré-processamento do ranqueamento (preparar_ranking.py) e da carga.")

    m = Medidor(r, consultas)
    resumo_custo = etapa("custo", custo, m, a.reps, a.saida)
    hs = etapa("heap × sorted", heap_sorted, r, a.saida)
    tops = etapa("sobreposição", sobreposicao, m, a.saida)
    etapa("perfil do top-10", perfil_top10, m, tops, a.saida)
    etapa("sensibilidade BM25", sensibilidade_bm25, m, a.saida)
    etapa("pesos BM25F", bm25f_pesos, m, a.saida)
    etapa("α do código", alfa_codigo, m, a.saida)
    etapa("variantes do IDF", idf_variantes, r, consultas, a.saida)
    etapa("stopwords do domínio", stopwords_dominio, r, a.saida)
    etapa("qualitativo", qualitativo, m, a.saida)
    etapa("explicar", explicar, r, a.saida)

    resumo = {"indice": a.indice, "consultas": len(consultas), "repeticoes": a.reps,
              "carga_s": round(carga, 3), "memoria_pico_mb": pico_memoria_mb(),
              "memoria_apos_carga_mb": mem_carga,
              "latencia_ms_media": {l[0]: float(l[1]) for l in resumo_custo},
              "heap_sorted": [{"consulta": l[0], "candidatos": l[1], "heap_ms": float(l[2]),
                               "sorted_ms": float(l[3])} for l in hs],
              "tempo_total_s": round(time.perf_counter() - inicio, 1)}
    with open(os.path.join(a.saida, "resumo.json"), "w", encoding="utf-8") as f:
        json.dump(resumo, f, ensure_ascii=False, indent=2)
    print(f"Gravado em {a.saida}{os.sep} ({resumo['tempo_total_s']} s)")


if __name__ == "__main__":
    main()
