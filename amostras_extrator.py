# amostras_extrator.py - separa páginas de exemplo de cada site do corpus
# Uso: python amostras_extrator.py corpus.jsonl.gz
#   Sorteia páginas de cada site (variando do menor ao maior HTML) e grava:
#     amostras_extrator/<site>_<n>.html  - o HTML de cada página
#     amostras_extrator/indice.tsv       - arquivo, site, URL e tamanho
#     amostras_extrator.zip              - tudo compactado, para enviar
#   Lê o corpus linha a linha, sem descompactar o arquivo inteiro.
import gzip
import json
import os
import random
import sys
import zipfile
from urllib.parse import urlparse

POR_SITE = 8          # páginas escolhidas por site
RESERVATORIO = 60     # páginas sorteadas por site antes da escolha final
SITES = {"www.exploit-db.com": "exploitdb", "github.com": "ghsa",
         "www.rapid7.com": "rapid7", "cwe.mitre.org": "cwe",
         "www.drupal.org": "drupal", "developer.joomla.org": "joomla"}
PREFIXO = '{"url": "'


def main(caminho):
    random.seed(42)  # mesma amostra a cada execução
    sorteadas, vistas = {s: [] for s in SITES.values()}, {s: 0 for s in SITES.values()}
    with gzip.open(caminho, "rt", encoding="utf-8") as f:
        for n, linha in enumerate(f, 1):
            if n % 10000 == 0:
                print(f"{n} páginas lidas...")
            if not linha.startswith(PREFIXO):
                continue
            url = linha[len(PREFIXO):linha.find('"', len(PREFIXO))]
            site = SITES.get(urlparse(url).netloc)
            if not site:
                continue
            vistas[site] += 1  # sorteio uniforme numa única leitura
            if len(sorteadas[site]) < RESERVATORIO:
                sorteadas[site].append(linha)
            elif (j := random.randrange(vistas[site])) < RESERVATORIO:
                sorteadas[site][j] = linha

    os.makedirs("amostras_extrator", exist_ok=True)
    indice = ["arquivo\tsite\turl\tbytes_html"]
    for site, linhas in sorteadas.items():
        regs = sorted((json.loads(l) for l in linhas), key=lambda r: len(r["html"]))
        # escolhe páginas espalhadas do menor ao maior HTML, para ver variações
        passo = max(1, (len(regs) - 1) / max(1, POR_SITE - 1))
        escolhidas = {regs[min(len(regs) - 1, round(i * passo))]["url"]: None
                      for i in range(POR_SITE)}
        regs = [r for r in regs if r["url"] in escolhidas]
        for i, r in enumerate(regs, 1):
            nome = f"{site}_{i}.html"
            with open(os.path.join("amostras_extrator", nome), "w", encoding="utf-8") as out:
                out.write(r["html"])
            indice.append(f"{nome}\t{site}\t{r['url']}\t{len(r['html'].encode())}")
        print(f"{site}: {len(regs)} páginas (de {vistas[site]} no corpus)")

    with open(os.path.join("amostras_extrator", "indice.tsv"), "w", encoding="utf-8") as f:
        f.write("\n".join(indice) + "\n")
    with zipfile.ZipFile("amostras_extrator.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for nome in sorted(os.listdir("amostras_extrator")):
            z.write(os.path.join("amostras_extrator", nome), nome)
    print(f"Pronto: amostras_extrator.zip ({os.path.getsize('amostras_extrator.zip') / 2**20:.1f} MB)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Uso: python amostras_extrator.py corpus.jsonl.gz")
    main(sys.argv[1])
