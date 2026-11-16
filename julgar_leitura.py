# julgar_leitura.py - leitura cega dos documentos de um pool, para julgar a relevância
# Uso: python julgar_leitura.py q05 [--avaliador NOME] [--indice indice]
#
# Mostra cada documento do pool com um rótulo neutro (d1, d2...), na ordem aleatória fixa
# do avaliador (a mesma da página /julgar), SEM modelo, posição nem score. Para cada um:
#   - site, título, URL e identificadores (CVE/CWE);
#   - exploit-db: Type, Platform, Date (a ficha);
#   - texto: inteiro se tiver até TEXTO_INTEIRO caracteres; senão o início e as janelas
#     em volta dos termos da consulta (trechos.py);
#   - código: tamanho, as primeiras linhas e as linhas em volta do casamento (trechos.py);
#     nas consultas de código, quantas linhas casam e sinais de shellcode/execução.
# Usado para os julgamentos feitos pelo Claude Code (ver RESULTADOS_AVALIACAO.md).
import argparse
import re
import sys

import trechos
from julgamento import Julgamentos, le_tsv
from ranqueamento import ProcessadorConsulta
from textos import Textos

TEXTO_INTEIRO = 900
INICIO_TEXTO = 350
LINHAS_INICIO_CODIGO = 6
AVALIADOR = "Claude Code (modelo de linguagem), texto completo"
RE_SHELLCODE = re.compile(r"(\\x[0-9a-fA-F]{2}){8,}|(0x[0-9a-fA-F]{2},\s*){8,}")
RE_EXEC = re.compile(r"\b(system|popen|exec[lv]?p?e?|passthru|shell_exec|proc_open|Runtime\.getRuntime\(\)\.exec|subprocess\.\w+|os\.system|WinExec|CreateProcess\w*)\s*\(")


def plano(segs):
    return "".join(f"[{s['texto']}]" if s["destaque"] else s["texto"] for s in segs or [])


def curto(t, n):
    t = re.sub(r"\s+", " ", t or "").strip()
    return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + " …"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = argparse.ArgumentParser()
    a.add_argument("consulta")
    a.add_argument("--avaliador", default=AVALIADOR)
    a.add_argument("--indice", default="indice")
    args = a.parse_args()
    j = Julgamentos()
    cid = args.consulta
    _, linhas = le_tsv(j.caminho(cid))
    por_url = {l["url"]: l for l in linhas}
    ordem = j.ordem(cid, args.avaliador, por_url)
    urls_idx = {}
    with open(f"{args.indice}/documentos.tsv", encoding="utf-8") as f:
        next(f)
        for l in f:
            p = l.split("\t")
            urls_idx[p[1]] = int(p[0])
    tx = Textos(args.indice, cache=0)
    q = j.consultas[cid]["consulta"]
    proc = ProcessadorConsulta()
    dest = trechos.Destaque.de_consulta(proc.analisa(q))
    codigo_q = q.startswith("codigo:") or cid in ("q18", "q19", "q20")
    print(f"=== {cid}: {q!r} ({len(ordem)} documentos; ordem cega)\n")
    for n, url in enumerate(ordem, 1):
        d = urls_idx.get(url)
        c = tx.campos(d) if d is not None else {}
        texto = c.get("texto") or ""
        titulo = c.get("titulo") or por_url[url]["titulo"]
        ids = (c.get("cves") or [])[:6] + (c.get("cwes") or [])[:4]
        print(f"--- d{n} | {por_url[url]['site']} | {titulo}")
        print(f"    {url}" + (f" | ids: {', '.join(ids)}" if ids else ""))
        ficha = trechos.ficha_exploitdb(texto, titulo)
        if ficha:
            v = dict(ficha[0])
            print("    ficha: " + " · ".join(f"{k}: {', '.join(v[k])}" for k in ("Type", "Platform", "Date", "CVE", "Tags") if k in v))
            resto = texto[ficha[1]:]
        else:
            resto = texto
        desc = c.get("descricao") or ""
        if desc:
            print("    descrição: " + curto(desc, 250))
        if resto.strip():
            if len(resto) <= TEXTO_INTEIRO:
                print("    texto: " + curto(resto, TEXTO_INTEIRO))
            else:
                g = trechos.gera({"titulo": "", "texto": resto}, dest)
                print(f"    texto ({len(resto)} car.), início: " + curto(resto, INICIO_TEXTO))
                if any(s["destaque"] for s in g["trecho"]):
                    print("    texto, em volta dos termos: " + plano(g["trecho"]))
        codigo = c.get("codigo") or ""
        if codigo:
            ls = [x for x in codigo.split("\n") if x.strip()]
            print(f"    código ({len(codigo)} car., {len(ls)} linhas), início: "
                  + " ⏎ ".join(curto(x, 110) for x in ls[:LINHAS_INICIO_CODIGO]))
            tc = trechos.trecho_codigo(codigo, dest, sem_separadores=True)
            if tc:
                print("    código, em volta do casamento: " + plano(tc).replace("\n", " ⏎ "))
            if codigo_q:
                termos = list(dest.codigo)
                n_lin = sum(1 for x in codigo.lower().split("\n") if any(t in x for t in termos))
                print(f"    código: {n_lin} linhas com {termos}; bytes de shellcode: "
                      f"{'sim' if RE_SHELLCODE.search(codigo) else 'não'}; chamadas de execução: "
                      f"{sorted(set(m.group(1) for m in RE_EXEC.finditer(codigo)))[:6]}")
        print()


if __name__ == "__main__":
    main()
