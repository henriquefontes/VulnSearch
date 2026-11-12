# preparar_textos.py - armazenamento dos textos para os trechos da interface Web
# Uso: python preparar_textos.py [--indice indice] [--fonte resultados/campos.jsonl.gz]
#   Roda depois do indexar.py (que o chama ao final, salvo com --sem-textos).
#   Só acrescenta arquivos ao índice (formato em textos.py):
#     textos.bin, textos_idx.bin, metadados.tsv, textos.json
#
# A fonte são os campos já extraídos (resultados/campos.jsonl.gz), lidos com o
# mesmo limite/passo da indexação; a URL de cada registro é conferida contra
# documentos.tsv, como no preparar_ranking.py. CVEs e CWEs são recalculados
# com as expressões regulares do extrair.py (o cache de campos não os guarda),
# acrescentando os CVEs sem prefixo da ficha do exploit-db ("CVE:\n2006-0660"),
# que o lexico já trata como cve-2006-0660.
import argparse
import datetime
import json
import os
import random
import re
import sys
import time
import zlib

import lexico
from extrair import CVE, CWE, extrair
from indexar import le_registros
from indice import Indice, pico_memoria_mb, tamanho_mb
from preparar_ranking import CAMPOS_PADRAO
from textos import CAMPOS, INDICE_FMT, Textos

ANO_FICHA = re.compile(r"(?:19|20)\d\d-\d{4,7}")
NIVEL_ZLIB = 6


def identificadores(campos):
    """(cves, cwes) ordenados, em maiúsculas."""
    tudo = "\n".join(campos[k] for k in ("titulo", "descricao", "palavras_chave", "texto",
                                         "codigo"))
    cves = {c.upper() for c in CVE.findall(tudo)}
    for m in lexico.CVE_FICHA.finditer(tudo):
        cves.update("CVE-" + a for a in ANO_FICHA.findall(m.group(2)))
    return sorted(cves), sorted({c.upper() for c in CWE.findall(tudo)})


def preparar(pasta="indice", fonte=None, log=print):
    t0 = time.perf_counter()
    ind = Indice(pasta)
    p = ind.estatisticas["parametros"]
    if fonte is None:
        fonte = CAMPOS_PADRAO if os.path.exists(CAMPOS_PADRAO) else p["entrada"]
    N = len(ind.documentos)
    log(f"Textos a partir de {fonte} ...")
    caminho_bin = os.path.join(pasta, "textos.bin")
    caminho_idx = os.path.join(pasta, "textos_idx.bin")
    caminho_meta = os.path.join(pasta, "metadados.tsv")
    bytes_json = bytes_texto = 0
    n_cve = n_cwe = docs_cve = docs_cwe = 0
    with open(caminho_bin, "wb", buffering=2**20) as fb, \
            open(caminho_idx, "wb") as fi, \
            open(caminho_meta, "w", encoding="utf-8", newline="\n") as fm:
        fm.write("id\tcves\tcwes\n")
        offset = 0
        d = -1
        for d, reg in enumerate(le_registros(fonte, p["limite"], p["passo"], {"leitura": 0.0})):
            if d >= N or reg["url"] != ind.documentos[d]["url"]:
                sys.exit(f"{fonte} não corresponde ao índice (documento {d}). "
                         "Use --fonte com o arquivo usado na indexação.")
            if "html" in reg:
                reg = extrair(reg["url"], reg["html"])
            cves, cwes = identificadores(reg)
            registro = {k: reg[k] for k in CAMPOS[:5]}
            registro["cves"], registro["cwes"] = cves, cwes
            dados = json.dumps(registro, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
            comp = zlib.compress(dados, NIVEL_ZLIB)
            fb.write(comp)
            fi.write(INDICE_FMT.pack(offset, len(comp)))
            offset += len(comp)
            bytes_json += len(dados)
            bytes_texto += sum(len(reg[k].encode("utf-8")) for k in CAMPOS[:5])
            fm.write(f"{d}\t{','.join(cves)}\t{','.join(cwes)}\n")
            n_cve += len(cves)
            n_cwe += len(cwes)
            docs_cve += bool(cves)
            docs_cwe += bool(cwes)
    if d + 1 != N:
        sys.exit(f"{fonte} tem {d + 1} documentos; o índice tem {N}")
    t_prep = time.perf_counter() - t0

    # leitura: 10 documentos sorteados, sem cache, 20 rodadas
    textos = Textos(pasta, cache=0)
    rnd = random.Random(42)
    tempos = []
    for _ in range(20):
        docs = rnd.sample(range(N), min(10, N))
        t = time.perf_counter()
        for x in docs:
            textos.campos(x)
        tempos.append((time.perf_counter() - t) * 1000)
    textos.fecha()
    ind.fecha()

    tam = {"textos_bin": tamanho_mb(caminho_bin), "textos_idx": tamanho_mb(caminho_idx),
           "metadados": tamanho_mb(caminho_meta)}
    tam["total"] = sum(tam.values())
    meta = {
        "N": N, "fonte": os.path.basename(fonte), "zlib_nivel": NIVEL_ZLIB,
        "data": datetime.datetime.now().isoformat(timespec="seconds"),
        "texto_mb": bytes_texto / 2**20, "json_mb": bytes_json / 2**20,
        "tamanhos_mb": tam,
        "razao_compressao": bytes_json / os.path.getsize(caminho_bin),
        "pct_do_texto": 100 * os.path.getsize(caminho_bin) / bytes_texto if bytes_texto else None,
        "tempo_preparacao_s": round(t_prep, 2),
        "leitura_10_docs_ms": {"media": sum(tempos) / len(tempos), "min": min(tempos),
                               "max": max(tempos)},
        "memoria_pico_mb": pico_memoria_mb(),
        "identificadores": {"cves": n_cve, "cwes": n_cwe, "docs_com_cve": docs_cve,
                            "docs_com_cwe": docs_cwe},
    }
    with open(os.path.join(pasta, "textos.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return meta


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = argparse.ArgumentParser(description="Armazenamento dos textos para os trechos.")
    a.add_argument("--indice", default="indice")
    a.add_argument("--fonte", help=f"campos.jsonl.gz ou o corpus (padrão: {CAMPOS_PADRAO})")
    args = a.parse_args()
    m = preparar(args.indice, args.fonte)
    t = m["tamanhos_mb"]
    print(f"N = {m['N']}; texto + código {m['texto_mb']:.1f} MB (JSON {m['json_mb']:.1f} MB) -> "
          f"textos.bin {t['textos_bin']:.1f} MB (razão {m['razao_compressao']:.2f}; "
          f"{m['pct_do_texto']:.1f}% do texto); índice {t['textos_idx']:.2f} MB; "
          f"metadados {t['metadados']:.2f} MB")
    i = m["identificadores"]
    print(f"CVEs: {i['cves']} em {i['docs_com_cve']} docs; CWEs: {i['cwes']} em "
          f"{i['docs_com_cwe']} docs")
    print(f"Tempo: {m['tempo_preparacao_s']} s; leitura de 10 docs: "
          f"{m['leitura_10_docs_ms']['media']:.2f} ms em média; pico "
          f"{m['memoria_pico_mb'] or 0:.0f} MB")


if __name__ == "__main__":
    main()
