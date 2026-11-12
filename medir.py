# medir.py - experimentos de indexação: tempo, espaço e hiperparâmetros
# Uso: python medir.py [corpus.jsonl.gz] [--limite N --passo K] [--so nome1,nome2]
#                      [--manter] [--pular-principal]
#
# 1. Constrói o índice principal a partir do corpus (em indice/), medindo
#    todas as etapas, inclusive a extração do HTML, e grava os campos
#    extraídos em resultados/campos.jsonl.gz.
# 2. Constrói cada variação a partir de resultados/campos.jsonl.gz (sem
#    repetir a extração), cada uma num processo separado, para que o pico de
#    memória de uma não contamine a outra. Os índices das variações são
#    apagados no final (use --manter para guardá-los em resultados/indices/).
# 3. Roda etapas.py (tabela Reuters-RCV1 e limite de tamanho do código).
# 4. Grava em resultados/ as tabelas (CSV e Markdown):
#      variacoes   tamanho, tempo e memória de cada variação
#      tempos      tempo por etapa do índice principal
#      tamanhos    arquivos do índice principal e % do texto e do HTML
#      heaps       K e b da lei de Heaps (regressão em log-log)
#      sites       termos por página em cada site
#    e heaps_curva.csv / heaps_curva_aleatoria.csv (crescimento do vocabulário
#    na ordem do corpus e em ordem aleatória). Os gráficos são
#    gerados à parte por graficos.py.
import argparse
import csv
import json
import math
import os
import shutil
import subprocess
import sys
import time

import lexico
from etapas import grava
from indice import PREFIXO_CODIGO

PY = sys.executable
RES = "resultados"
CAMPOS = os.path.join(RES, "campos.jsonl.gz")

# nome, descrição, opções do indexar.py (além das padrão do índice principal)
VARIACOES = [
    ("base", "documento + posições, comprimido (principal, a partir dos campos)", []),
    ("sem_compressao", "sem compressão (inteiros de 4 bytes)", ["--sem-compressao"]),
    ("sem_posicoes", "documento sem posições", ["--sem-posicoes"]),
    ("trecho_500", "trechos de 500 tokens, sem posições",
     ["--granularidade", "trecho", "--tam-trecho", "500", "--sem-posicoes"]),
    ("trecho_200", "trechos de 200 tokens, sem posições",
     ["--granularidade", "trecho", "--tam-trecho", "200", "--sem-posicoes"]),
    ("trecho_200_pos", "trechos de 200 tokens, com posições",
     ["--granularidade", "trecho", "--tam-trecho", "200"]),
    ("sem_codigo", "sem o campo código", ["--sem-codigo"]),
    ("sem_stopwords", "sem remover stopwords", ["--sem-stopwords"]),
    ("sem_stemming", "sem stemming", ["--sem-stemming"]),
    ("codigo_16", "limite de token do código = 16", ["--tam-max-codigo", "16"]),
    ("codigo_64", "limite de token do código = 64", ["--tam-max-codigo", "64"]),
    ("codigo_sem_limite", "código sem limite de tamanho de token", ["--tam-max-codigo", "0"]),
    ("bloco_16", "bloco (MAX_TAMANHO) de 16 MB", ["--bloco", "16"]),
    ("bloco_256", "bloco (MAX_TAMANHO) de 256 MB", ["--bloco", "256"]),
]


def roda(args, log):
    print("  $ indexar.py " + " ".join(args), flush=True)
    t = time.perf_counter()
    with open(log, "w", encoding="utf-8") as f:
        r = subprocess.run([PY, "indexar.py", "--sem-ranking", "--sem-textos"] + args, stdout=f,
                           stderr=subprocess.STDOUT)
    if r.returncode:
        sys.exit(f"Falhou (veja {log})")
    print(f"    {time.perf_counter() - t:.0f} s", flush=True)


def le_estat(pasta):
    with open(os.path.join(pasta, "estatisticas.json"), encoding="utf-8") as f:
        return json.load(f)


def linha_variacao(nome, descricao, e):
    c, m, b = e["contagens"], e["tamanhos_mb"], e["blocos"]
    return [nome, descricao, c["unidades"], c["vocabulario"], c["postings"], c["ocorrencias"],
            f"{m['vocabulario']:.1f}", f"{m['ocorrencias']:.1f}", f"{m['documentos']:.1f}",
            f"{m['total']:.1f}", f"{e['ocorrencias_pct_texto']:.1f}", f"{e['indice_pct_texto']:.1f}",
            f"{e['tempos_s']['total']:.0f}", f"{e['memoria_pico_mb'] or 0:.0f}",
            b["quantidade"], f"{b['temporarios_mb']:.1f}"]


def curva_aleatoria(campos, caminho, semente=42):
    """Curva de Heaps lendo as páginas em ordem aleatória. O corpus está
    agrupado por site, e cada site novo traz um vocabulário próprio: na ordem
    do corpus o vocabulário cresce aos saltos e o ajuste não representa a lei
    de Heaps. Mesma análise léxica do índice principal."""
    import gzip
    import random
    from indexar import CAMPOS_TEXTO, HEAPS_A_CADA
    with gzip.open(campos, "rt", encoding="utf-8") as f:
        linhas = f.readlines()
    random.Random(semente).shuffle(linhas)
    voc_t, voc = set(), set()
    nt = ntot = 0
    pontos = [("paginas", "termos_texto", "vocabulario_texto", "termos_total",
               "vocabulario_total")]
    for i, linha in enumerate(linhas, 1):
        reg = json.loads(linha)
        termos, _ = lexico.termos_campos([reg[k] for k in CAMPOS_TEXTO])
        cod = lexico.termos_codigo(reg["codigo"]) if reg["codigo"] else []
        voc_t.update(t for t, _ in termos)
        voc.update(t for t, _ in termos)
        voc.update(PREFIXO_CODIGO + t for t, _ in cod)
        nt += len(termos)
        ntot += len(termos) + len(cod)
        if i % HEAPS_A_CADA == 0 or i == len(linhas):
            pontos.append((i, nt, len(voc_t), ntot, len(voc)))
    with open(caminho, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(",".join(map(str, p)) for p in pontos) + "\n")


def heaps(caminho, ordem):
    """Ajusta V = K·n^b por mínimos quadrados em log-log."""
    with open(caminho, encoding="utf-8") as f:
        pontos = list(csv.DictReader(f))
    saida = []
    for rotulo, cn, cv in (("texto", "termos_texto", "vocabulario_texto"),
                           ("texto + código", "termos_total", "vocabulario_total")):
        xs = [math.log(float(p[cn])) for p in pontos if float(p[cn]) > 0]
        ys = [math.log(float(p[cv])) for p in pontos if float(p[cn]) > 0]
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        sxx = sum((x - mx) ** 2 for x in xs)
        sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        b = sxy / sxx
        k = math.exp(my - b * mx)
        ss_res = sum((y - (math.log(k) + b * x)) ** 2 for x, y in zip(xs, ys))
        ss_tot = sum((y - my) ** 2 for y in ys)
        saida.append([ordem, rotulo, f"{k:.2f}", f"{b:.3f}", f"{1 - ss_res / ss_tot:.4f}", n,
                      pontos[-1][cn], pontos[-1][cv]])
    return saida


def sites(pasta):
    por = {}
    with open(os.path.join(pasta, "documentos.tsv"), encoding="utf-8") as f:
        next(f)
        for linha in f:
            _id, _url, site, nt, nc, _t = linha.rstrip("\n").split("\t")
            s = por.setdefault(site, [0, 0, 0, 0])
            s[0] += 1
            s[1] += int(nt)
            s[2] += int(nc)
            s[3] += int(nc) > 0
    linhas = []
    for site, (n, nt, nc, com) in sorted(por.items(), key=lambda x: -x[1][0]):
        linhas.append([site, n, nt, f"{nt / n:.0f}", nc, f"{nc / n:.0f}", f"{100 * com / n:.1f}"])
    return linhas


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser()
    p.add_argument("entrada", nargs="?", default="corpus.jsonl.gz")
    p.add_argument("--limite", type=int, default=0)
    p.add_argument("--passo", type=int, default=1)
    p.add_argument("--so", help="só estas variações (nomes separados por vírgula)")
    p.add_argument("--manter", action="store_true", help="não apaga os índices das variações")
    p.add_argument("--pasta-variacoes", default=os.path.join(RES, "indices"),
                   help="onde construir os índices das variações (padrão: resultados/indices)")
    p.add_argument("--pular-principal", action="store_true",
                   help="reaproveita indice/ e resultados/campos.jsonl.gz já construídos")
    a = p.parse_args()
    os.makedirs(os.path.join(RES, "logs"), exist_ok=True)
    amostra = (["--limite", str(a.limite)] if a.limite else []) + \
              (["--passo", str(a.passo)] if a.passo > 1 else [])

    # 1. índice principal, a partir do corpus
    if not a.pular_principal:
        print("Índice principal (a partir do corpus)")
        roda([a.entrada, "--saida", "indice", "--salvar-campos", CAMPOS] + amostra,
             os.path.join(RES, "logs", "principal.log"))
    principal = le_estat("indice")

    # 2. variações, a partir dos campos já extraídos
    escolhidas = VARIACOES
    if a.so:
        nomes = a.so.split(",")
        escolhidas = [v for v in VARIACOES if v[0] in nomes]
    estat = {}
    for nome, desc, opcoes in escolhidas:
        print(f"Variação {nome}: {desc}")
        pasta = os.path.join(a.pasta_variacoes, nome)
        # o campos.jsonl.gz já é a amostra; --limite/--passo não se repetem
        roda([CAMPOS, "--saida", pasta] + opcoes, os.path.join(RES, "logs", nome + ".log"))
        estat[nome] = le_estat(pasta)
        with open(os.path.join(RES, "logs", nome + ".json"), "w", encoding="utf-8") as f:
            json.dump(estat[nome], f, ensure_ascii=False, indent=2)
        if not a.manter:
            shutil.rmtree(pasta, ignore_errors=True)
    if not a.manter and os.path.isdir(a.pasta_variacoes) and not os.listdir(a.pasta_variacoes):
        os.rmdir(a.pasta_variacoes)

    # 3. etapas do pré-processamento
    print("Etapas do pré-processamento (etapas.py)")
    r = subprocess.run([PY, "etapas.py", CAMPOS, "--saida", RES],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if r.returncode:
        print("  etapas.py falhou; rode-o à parte para ver o erro")

    # 4. tabelas
    cab = ["variação", "descrição", "unidades", "vocabulário", "postings", "ocorrências",
           "vocabulário (MB)", "ocorrências (MB)", "documentos (MB)", "total (MB)",
           "ocorrências/texto (%)", "índice/texto (%)", "tempo (s)", "pico de memória (MB)",
           "blocos", "temporários (MB)"]
    linhas = [linha_variacao("principal", "índice principal, a partir do corpus "
                             "(inclui a extração do HTML)", principal)]
    # variações não rodadas agora (--so) entram com o resultado da última execução
    for n, _, _ in VARIACOES:
        anterior = os.path.join(RES, "logs", n + ".json")
        if n not in estat and os.path.exists(anterior):
            with open(anterior, encoding="utf-8") as f:
                estat[n] = json.load(f)
    linhas += [linha_variacao(n, d, estat[n]) for n, d, _ in VARIACOES if n in estat]
    grava(RES, "variacoes", cab, linhas,
          "Variações da representação. Texto = campos de texto + código extraídos "
          f"({principal['texto_mb']:.0f} MB). As variações leem os campos já extraídos, "
          "então o tempo delas não inclui a extração do HTML.")

    t = principal["tempos_s"]
    etapas = [("leitura (descompactação + JSON)", "leitura"), ("extração do HTML", "extracao"),
              ("análise léxica", "lexico"), ("inversão em memória", "inversao"),
              ("gravação dos blocos", "gravacao_blocos"), ("intercalação (merge)", "merge")]
    soma = sum(t[k] for _, k in etapas)
    linhas = [[nome, f"{t[k]:.1f}", f"{100 * t[k] / t['total']:.1f}"] for nome, k in etapas]
    linhas.append(["outros (laço, contagens, documentos.tsv)", f"{t['total'] - soma:.1f}",
                   f"{100 * (t['total'] - soma) / t['total']:.1f}"])
    linhas.append(["total", f"{t['total']:.1f}", "100.0"])
    grava(RES, "tempos", ["etapa", "tempo (s)", "%"], linhas,
          f"Tempo por etapa do índice principal ({principal['contagens']['paginas']} páginas; "
          f"pico de memória {principal['memoria_pico_mb'] or 0:.0f} MB; "
          f"{principal['blocos']['quantidade']} blocos de {principal['parametros']['bloco_mb']:g} MB).")

    m = principal["tamanhos_mb"]
    tx, html = principal["texto_mb"], principal["html_mb"]
    linhas = [[nome, f"{m[k]:.1f}", f"{100 * m[k] / tx:.1f}", f"{100 * m[k] / html:.2f}"]
              for nome, k in (("vocabulario.tsv", "vocabulario"), ("ocorrencias.bin", "ocorrencias"),
                              ("documentos.tsv", "documentos"), ("total", "total"))]
    linhas.append(["texto extraído (texto + código)", f"{tx:.1f}", "100.0", f"{100 * tx / html:.2f}"])
    linhas.append(["HTML do corpus", f"{html:.1f}", f"{100 * html / tx:.0f}", "100.00"])
    grava(RES, "tamanhos", ["arquivo", "MB", "% do texto", "% do HTML"], linhas,
          "Tamanho do índice principal.")

    curva = os.path.join(RES, "heaps_curva.csv")
    curva_alea = os.path.join(RES, "heaps_curva_aleatoria.csv")
    shutil.copy(os.path.join("indice", "heaps.csv"), curva)
    print("Curva de Heaps em ordem aleatória")
    curva_aleatoria(CAMPOS, curva_alea)
    grava(RES, "heaps", ["ordem das páginas", "vocabulário de", "K", "b", "R²", "pontos",
                         "n final", "V final"],
          heaps(curva_alea, "aleatória") + heaps(curva, "do corpus (agrupada por site)"),
          "Lei de Heaps (V = K·n^b), ajustada em log-log; n = termos indexados "
          "(após stopwords e stemming). Na ordem do corpus as páginas vêm agrupadas por "
          "site e o vocabulário cresce aos saltos; a ordem aleatória (semente 42) é a "
          "estimativa representativa.")
    grava(RES, "sites", ["site", "páginas", "termos (texto)", "termos/página", "termos (código)",
                         "termos de código/página", "% com código"], sites("indice"),
          "Termos indexados por site (índice principal).")
    print(f"Tabelas gravadas em {RES}{os.sep}. Gráficos: python graficos.py")


if __name__ == "__main__":
    main()
