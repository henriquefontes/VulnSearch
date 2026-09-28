# processar.py - seleção de documentos sobre a saída JSONL do Katana
# Uso: python3 processar.py coleta_*.jsonl   (aceita também .jsonl.gz)
#   Lê os arquivos de todas as execuções da coleta, mantém apenas respostas
#   HTTP 200, do tipo text/html, que não sejam soft-404 nem repetidas
#   (mesma URL ou mesmo conteúdo) e grava corpus.jsonl.gz, com um registro
#   {"url", "status", "headers", "html"} por página. Imprime as estatísticas.
#   O Katana também grava linhas sem resposta para links que ultrapassaram a
#   profundidade máxima (descobertos, mas não visitados); elas são ignoradas.
import glob
import gzip
import hashlib
import json
import re
import sys
from collections import Counter
from urllib.parse import urlparse

TAM_MIN = 1500  # caracteres; páginas menores tendem a ser erro ou vazias
# Título típico de página de erro: começa com 404/"not found" ou é só a mensagem
# de erro. Não procura "error"/"404" em qualquer parte do título, o que
# descartaria páginas legítimas (ex.: "CWE-209: Generation of Error Message",
# "CVE-2024-40404").
ERRO = re.compile(r"<title>\s*(404\b|error 404|erro 404|page not found|not found"
                  r"|página não encontrada|p[aá]gina n[aã]o encontrada)", re.I)


def abre(caminho):
    if caminho.endswith(".gz"):
        return gzip.open(caminho, "rt", encoding="utf-8")
    return open(caminho, encoding="utf-8")


def tipo_conteudo(cabecalhos):
    """Content-Type da resposta; aceita content-type e content_type."""
    for chave, valor in cabecalhos.items():
        if chave.lower().replace("_", "-") == "content-type":
            return str(valor).lower()
    return ""


def main(arquivos):
    visitadas, mantidas, tamanho, descartes = Counter(), Counter(), Counter(), Counter()
    nao_visitadas = 0
    urls_vistas, hashes_vistos = set(), set()
    with gzip.open("corpus.jsonl.gz", "wt", encoding="utf-8") as corpus:
        for arquivo in arquivos:
            for linha in abre(arquivo):
                try:
                    reg = json.loads(linha)
                except ValueError:  # linha cortada (coleta interrompida)
                    descartes["linha incompleta"] += 1
                    continue
                url = reg.get("request", {}).get("endpoint", "")
                resp = reg.get("response") or {}
                if not resp.get("status_code"):  # link descoberto, não visitado
                    nao_visitadas += 1
                    continue
                if url in urls_vistas:  # mesma URL coletada em outra execução
                    descartes["URL repetida"] += 1
                    continue
                urls_vistas.add(url)
                host = urlparse(url).netloc
                visitadas[host] += 1
                html = resp.get("body") or ""
                cabecalhos = resp.get("headers") or {}
                if resp.get("status_code") != 200:
                    descartes["status != 200"] += 1
                    continue
                if "html" not in tipo_conteudo(cabecalhos):
                    descartes["não HTML"] += 1
                    continue
                if len(html) < TAM_MIN or ERRO.search(html):
                    descartes["soft-404"] += 1
                    continue
                h = hashlib.sha1(html.encode()).hexdigest()
                if h in hashes_vistos:
                    descartes["conteúdo duplicado"] += 1
                    continue
                hashes_vistos.add(h)
                corpus.write(json.dumps({"url": url, "status": 200,
                                         "headers": cabecalhos, "html": html},
                                        ensure_ascii=False) + "\n")
                mantidas[host] += 1
                tamanho[host] += len(html.encode())

    print(f"{'site':35} {'visitadas':>10} {'corpus':>10} {'MB':>8}")
    for host in sorted(visitadas, key=visitadas.get, reverse=True):
        print(f"{host:35} {visitadas[host]:>10} {mantidas[host]:>10} "
              f"{tamanho[host] / 2**20:>8.1f}")
    print(f"{'TOTAL':35} {sum(visitadas.values()):>10} "
          f"{sum(mantidas.values()):>10} {sum(tamanho.values()) / 2**20:>8.1f}")
    print("Descartes:", dict(descartes))
    print(f"Links descobertos e não visitados (ignorados): {nao_visitadas}")


if __name__ == "__main__":
    # expande coleta_*.jsonl também no Windows, onde o terminal não o faz
    arquivos = sorted({f for padrao in sys.argv[1:] for f in glob.glob(padrao)})
    if not arquivos:
        sys.exit("Uso: python processar.py coleta_*.jsonl")
    main(arquivos)
