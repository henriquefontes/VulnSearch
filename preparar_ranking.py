# preparar_ranking.py - estatísticas por documento para o ranqueamento
# Uso: python preparar_ranking.py [--indice indice] [--fonte resultados/campos.jsonl.gz]
#   Roda depois do indexar.py (que o chama ao final, salvo com --sem-ranking).
#   Só acrescenta arquivos ao índice; não altera os da etapa 2.
#
# 1. Limite do título: título, descrição, palavras-chave e texto foram
#    analisados em sequência (indexar.py, lexico.termos_campos), com o título
#    primeiro. As ocorrências de um termo de texto com posição < limite_titulo
#    são do título. O limite é calculado com o mesmo código (lexico), a partir
#    do título completo (o de documentos.tsv está cortado em 300 caracteres).
# 2. Uma passada sobre ocorrencias.bin acumula, por documento: termos
#    distintos (Jaccard), soma dos quadrados dos pesos (normas do cosseno,
#    esquemas 1, 2 e 3) e nº de termos do título e do corpo (BM25F).
# 3. Grava indice/documentos_ranking.tsv (ou .bin) e indice/colecao.json.
#
# Verificações: os termos de posição < limite lidos do índice têm de ser
# exatamente os termos do título analisado (amostra de documentos); os
# tamanhos contados na passada têm de bater com documentos.tsv.
import argparse
import bisect
import datetime
import json
import math
import os
import random
import sys
import time

import lexico
from extrair import extrair
from indexar import le_registros
from indice import PREFIXO_CODIGO, Indice, pico_memoria_mb, tamanho_mb
from ranqueamento import ESQUEMAS, Colecao, idf_peso, tf_peso

CAMPOS_PADRAO = os.path.join("resultados", "campos.jsonl.gz")


def limite_do_titulo(titulo, stopwords, stemming):
    """(limite_titulo, termos do título) com o mesmo código do indexar.py:
    termos_campos devolve a próxima posição livre (nº de tokens + 1 lacuna)."""
    termos, prox = lexico.termos_campos([titulo], stopwords, stemming)
    return max(prox - 1, 0), termos


def calcula(ind, limites, base=2, esquemas=None, amostra=None):
    """Passada única sobre as listas de 'ind' (Indice ou índice em memória).
    limites[d] = limite do título. Devolve (Colecao, contagens da passada,
    {doc da amostra: [(posição, termo)] do título lido do índice})."""
    esquemas = esquemas or ESQUEMAS
    N = len(ind.documentos)
    docs = {n: [0] * N for n in ("n_titulo", "n_corpo", "n_codigo", "distintos_texto",
                                 "distintos_codigo")}
    docs["limite_titulo"] = list(limites)
    n2 = {e: ([0.0] * N, [0.0] * N) for e in esquemas}
    n_titulo, n_texto, n_codigo = docs["n_titulo"], [0] * N, docs["n_codigo"]
    dist_t, dist_c = docs["distintos_texto"], docs["distintos_codigo"]
    amostra = amostra or set()
    vistos = {d: [] for d in amostra}
    cache_tf = {}
    lista_esq = list(esquemas.items())
    for termo, (df, _cf, _o, _t) in ind.vocabulario.items():
        codigo = termo.startswith(PREFIXO_CODIGO)
        idfs = [idf_peso(df, N, e["idf_doc"], base) for _, e in lista_esq]
        acums = [n2[nome][1 if codigo else 0] for nome, _ in lista_esq]
        modos = [e["tf_doc"] for _, e in lista_esq]
        for d, f, pos in ind.lista(termo):
            if codigo:
                dist_c[d] += 1
                n_codigo[d] += f
            else:
                dist_t[d] += 1
                n_texto[d] += f
                if pos is not None and limites[d]:
                    nt = bisect.bisect_left(pos, limites[d])
                    n_titulo[d] += nt
                    if nt and d in vistos:
                        vistos[d] += [(p, termo) for p in pos[:nt]]
            for j in range(len(lista_esq)):
                chave = (modos[j], f)
                tw = cache_tf.get(chave)
                if tw is None:
                    tw = cache_tf[chave] = tf_peso(f, modos[j], base)
                w = tw * idfs[j]
                acums[j][d] += w * w
    docs["n_corpo"] = [a - b for a, b in zip(n_texto, n_titulo)]

    def media(v):
        com = [x for x in v if x > 0]
        return (sum(com) / len(com) if com else 0.0), len(com)

    medias, com_campo = {}, {}
    for campo, v in (("titulo", n_titulo), ("corpo", docs["n_corpo"]), ("texto", n_texto),
                     ("codigo", n_codigo)):
        medias[campo], com_campo[campo] = media(v)
    col = Colecao(N, base, esquemas, docs, n2, medias,
                  {"docs_com_campo": com_campo})
    return col, {"n_texto": n_texto, "n_codigo": n_codigo}, vistos


def titulos(fonte, ind, stopwords, stemming):
    """Limite do título de cada documento, lendo a fonte com o mesmo
    limite/passo da indexação. Confere a URL de cada documento."""
    p = ind.estatisticas["parametros"]
    limites, termos_tit = [], []
    tempos = {"leitura": 0.0}
    for i, reg in enumerate(le_registros(fonte, p["limite"], p["passo"], tempos)):
        if i >= len(ind.documentos) or reg["url"] != ind.documentos[i]["url"]:
            sys.exit(f"{fonte} não corresponde ao índice (documento {i}). "
                     "Use --fonte com o arquivo usado na indexação.")
        titulo = reg["titulo"] if "titulo" in reg else extrair(reg["url"], reg["html"])["titulo"]
        lim, termos = limite_do_titulo(titulo, stopwords, stemming)
        limites.append(lim)
        termos_tit.append(termos)
    if len(limites) != len(ind.documentos):
        sys.exit(f"{fonte} tem {len(limites)} documentos; o índice tem {len(ind.documentos)}")
    return limites, termos_tit


def preparar(pasta="indice", fonte=None, formato="bin", n_amostra=500, base=2, log=print):
    t0 = time.perf_counter()
    ind = Indice(pasta)
    p = ind.estatisticas["parametros"]
    if p["granularidade"] != "documento":
        sys.exit("O ranqueamento usa a granularidade 'documento'.")
    if fonte is None:
        fonte = CAMPOS_PADRAO if os.path.exists(CAMPOS_PADRAO) else p["entrada"]
    stopwords = lexico.STOPWORDS if p["stopwords"] else frozenset()
    log(f"Títulos a partir de {fonte} ...")
    limites, termos_tit = titulos(fonte, ind, stopwords, p["stemming"])
    t1 = time.perf_counter()

    random.seed(42)
    N = len(ind.documentos)
    amostra = set(random.sample(range(N), min(n_amostra, N)))
    log("Passada sobre as ocorrências ...")
    col, cont, vistos = calcula(ind, limites, base, amostra=amostra)
    t2 = time.perf_counter()

    # verificações
    titulo_ok = sum(1 for d in amostra if sorted(vistos[d]) == [(q, t) for t, q in termos_tit[d]])
    dif_titulo = sum(1 for d in range(N) if col.n_titulo[d] != len(termos_tit[d]))
    dif_texto = sum(1 for d in range(N) if cont["n_texto"][d] != ind.documentos[d]["n_texto"])
    dif_codigo = sum(1 for d in range(N) if cont["n_codigo"][d] != ind.documentos[d]["n_codigo"])
    verif = {"amostra_titulo": len(amostra), "amostra_titulo_iguais": titulo_ok,
             "docs_n_titulo_diferente": dif_titulo, "docs_n_texto_diferente": dif_texto,
             "docs_n_codigo_diferente": dif_codigo}

    # gravação nos dois formatos, para medir; fica o escolhido
    formatos = {}
    for fmt in ("tsv", "bin"):
        caminho = os.path.join(pasta, f"documentos_ranking.{fmt}")
        t = time.perf_counter()
        col.grava_tsv(caminho) if fmt == "tsv" else col.grava_bin(caminho)
        formatos[fmt] = {"tamanho_mb": tamanho_mb(caminho),
                         "gravacao_s": round(time.perf_counter() - t, 3)}
        t = time.perf_counter()
        if fmt == "tsv":
            Colecao._le_tsv(caminho)
        else:
            Colecao._le_bin(caminho, [n for n, _, _ in col.colunas()])
        formatos[fmt]["leitura_s"] = round(time.perf_counter() - t, 3)
        if fmt != formato:
            os.remove(caminho)
    t3 = time.perf_counter()

    meta = {
        "N": N, "base_log": base, "formato": formato,
        "colunas": [n for n, _, _ in col.colunas()],
        "esquemas": {str(k): v for k, v in col.esquemas.items()},
        "medias": col.medias, "docs_com_campo": col.meta["docs_com_campo"],
        "fonte_titulos": os.path.basename(fonte),
        "data": datetime.datetime.now().isoformat(timespec="seconds"),
        "tempos_s": {"titulos": round(t1 - t0, 2), "passada": round(t2 - t1, 2),
                     "gravacao": round(t3 - t2, 2), "total": round(t3 - t0, 2)},
        "memoria_pico_mb": pico_memoria_mb(),
        "formatos": formatos,
        "verificacao": verif,
    }
    caminho_json = os.path.join(pasta, "colecao.json")
    with open(caminho_json, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    meta["tamanho_mb"] = formatos[formato]["tamanho_mb"] + tamanho_mb(caminho_json)
    with open(caminho_json, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    ind.fecha()
    return meta


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = argparse.ArgumentParser(description="Pré-processamento do ranqueamento.")
    a.add_argument("--indice", default="indice")
    a.add_argument("--fonte", help="campos.jsonl.gz ou o corpus usado na indexação "
                                   f"(padrão: {CAMPOS_PADRAO}, se existir)")
    a.add_argument("--formato", choices=["bin", "tsv"], default="bin")
    a.add_argument("--amostra", type=int, default=500,
                   help="documentos sorteados para conferir o limite do título")
    args = a.parse_args()
    m = preparar(args.indice, args.fonte, args.formato, args.amostra)
    v, t = m["verificacao"], m["tempos_s"]
    print(f"N = {m['N']}; médias: " + ", ".join(f"{k} {x:.1f}" for k, x in m["medias"].items()))
    print(f"Documentos com o campo: {m['docs_com_campo']}")
    print(f"Tempos (s): {t}; pico de memória {m['memoria_pico_mb'] or 0:.0f} MB")
    print("Formatos: " + "; ".join(f"{k} {x['tamanho_mb']:.2f} MB, leitura {x['leitura_s']} s"
                                   for k, x in m["formatos"].items())
          + f" -> {m['formato']}")
    print(f"Limite do título: {v['amostra_titulo_iguais']}/{v['amostra_titulo']} documentos "
          f"da amostra iguais; n_titulo diferente em {v['docs_n_titulo_diferente']}, "
          f"n_texto em {v['docs_n_texto_diferente']}, n_codigo em {v['docs_n_codigo_diferente']}")
    ok = (v["amostra_titulo_iguais"] == v["amostra_titulo"] and not v["docs_n_titulo_diferente"]
          and not v["docs_n_texto_diferente"] and not v["docs_n_codigo_diferente"])
    print("Verificação OK" if ok else "ATENÇÃO: verificação falhou")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
