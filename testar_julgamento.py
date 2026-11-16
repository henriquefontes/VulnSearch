# testar_julgamento.py - testes da ferramenta de julgamento (/julgar, julgamento.py)
# Uso: python testar_julgamento.py [--indice indice] [--com-pool]
#
# Trabalha numa CÓPIA temporária de julgamentos/ (os arquivos reais não são tocados; o
# teste confere isso no fim, pelo hash). Sobe o servidor numa thread, como o testar_api.py.
#   --com-pool  também roda o pool.py sobre a cópia julgada e confere que ele mantém os
#               julgamentos e a coluna avaliador (~20 s no índice completo)
import argparse
import csv
import glob
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import threading

import avaliar
import julgamento
from cliente_api import ServidorTeste

FALHAS = []
N_OK = 0


def verdadeiro(nome, cond, detalhe=""):
    global N_OK
    if cond:
        N_OK += 1
    else:
        FALHAS.append(nome + (f" ({detalhe})" if detalhe else ""))


def hashes(pasta):
    return {os.path.relpath(f, pasta): hashlib.sha256(open(f, "rb").read()).hexdigest()
            for f in glob.glob(os.path.join(pasta, "**", "*"), recursive=True) if os.path.isfile(f)}


def le(caminho):
    with open(caminho, encoding="utf-8", newline="") as f:
        r = csv.DictReader(f, delimiter="\t")
        return list(r.fieldnames), list(r)


def testes(indice, pasta, com_pool):
    original = os.path.join(pasta, "pool_q01.tsv")
    col0, linhas0 = le(original)
    total = sum(len(le(f)[1]) for f in glob.glob(os.path.join(pasta, "pool_q*.tsv")))

    with ServidorTeste(indice, pasta_julgamentos=pasta) as srv:
        st, r, _ = srv.get("/api/julgamento")
        verdadeiro("resumo: 200, 20 consultas e total = linhas dos pools",
                   st == 200 and len(r["consultas"]) == 20 and r["total"] == total,
                   f"{st} {len(r.get('consultas', []))} {r.get('total')} x {total}")
        verdadeiro("resumo: critério com 0, 1 e 2", [c["valor"] for c in r["criterio"]] == ["2", "1", "0"])
        ja = r["julgados"]

        st, r, _ = srv.get("/api/julgamento/q01", avaliador="Ana")
        docs = r["documentos"]
        verdadeiro("documentos: todos os do pool", st == 200 and len(docs) == len(linhas0))
        proibidas = {"modelos", "melhor_pos", "escore", "posicao", "doc", "score"}
        verdadeiro("documentos: sem modelo, posição nem score",
                   not any(proibidas & set(d) for d in docs), str(set().union(*map(set, docs)) & proibidas))
        verdadeiro("documentos: título, site, URL, trecho e id para a cópia em cache",
                   all({"titulo", "site", "url", "trecho", "id"} <= set(d) for d in docs)
                   and all(d["id"] is not None for d in docs))
        verdadeiro("documentos: título em segmentos com destaque (consulta q01 = CVE-2021-44228)",
                   any(s["destaque"] for d in docs for s in d["trecho"] + d["titulo"]))
        ordem_ana = [d["url"] for d in docs]
        _, r2, _ = srv.get("/api/julgamento/q01", avaliador="ana ")
        verdadeiro("ordem: fixa para o mesmo avaliador (maiúsculas e espaços não importam)",
                   [d["url"] for d in r2["documentos"]] == ordem_ana)
        difere = 0
        for cid in ("q05", "q06", "q07"):
            a = [d["url"] for d in srv.get(f"/api/julgamento/{cid}", avaliador="Ana")[1]["documentos"]]
            b = [d["url"] for d in srv.get(f"/api/julgamento/{cid}", avaliador="Bruno")[1]["documentos"]]
            p = [l["url"] for l in le(os.path.join(pasta, f"pool_{cid}.tsv"))[1]]
            difere += (a != b) + (a != p)
        verdadeiro("ordem: aleatória (difere entre avaliadores e da ordem do pool, que segue o ranking)",
                   difere == 6, f"{difere}/6")

        # gravação
        alvo = ordem_ana[:3]
        for url, v in zip(alvo, ("2", "1", "0")):
            st, r, _ = srv.post("/api/julgamento/q01", {"url": url, "relevante": v, "avaliador": "Ana",
                                                        "observacao": "linha\tcom\ntab e quebra" if v == "2" else ""})
            verdadeiro(f"gravação: julgamento {v} aceito no principal", st == 200 and r["arquivo"] == "principal", str(r))
        verdadeiro("gravação: progresso devolvido (julgados + 3)", r["julgados"] == ja + 3, str(r.get("julgados")))
        col, linhas = le(original)
        por = {l["url"]: l for l in linhas}
        verdadeiro("arquivo: coluna avaliador acrescentada no fim, demais colunas na mesma ordem",
                   col == col0 + ["avaliador"], str(col))
        verdadeiro("arquivo: os 3 julgamentos com avaliador",
                   [(por[u]["relevante"], por[u]["avaliador"]) for u in alvo] == [("2", "Ana"), ("1", "Ana"), ("0", "Ana")])
        verdadeiro("arquivo: observação sem tabulação nem quebra de linha",
                   por[alvo[0]]["observacao"] == "linha com tab e quebra", repr(por[alvo[0]]["observacao"]))
        intactas = all({k: l[k] for k in col0} == {k: por[l["url"]][k] for k in col0}
                       for l in linhas0 if l["url"] not in alvo)
        mesmas_cols = all(por[l["url"]][k] == l[k] for l in linhas0 for k in ("doc", "modelos", "melhor_pos", "titulo"))
        verdadeiro("arquivo: demais linhas e colunas (doc, modelos, melhor_pos) intactas", intactas and mesmas_cols)
        verdadeiro("arquivo: mesma ordem de linhas do pool", [l["url"] for l in linhas] == [l["url"] for l in linhas0])

        # segunda avaliação (concordância), sem mostrar o julgamento da outra pessoa
        _, rb, _ = srv.get("/api/julgamento/q01", avaliador="Bruno")
        db = {d["url"]: d for d in rb["documentos"]}
        verdadeiro("segunda avaliação: Bruno não vê o julgamento de Ana, só o aviso",
                   db[alvo[0]]["relevante"] == "" and db[alvo[0]]["julgado_por_outra_pessoa"]
                   and not db[ordem_ana[5]]["julgado_por_outra_pessoa"])
        st, r, _ = srv.post("/api/julgamento/q01", {"url": alvo[0], "relevante": "1", "avaliador": "Bruno"})
        verdadeiro("segunda avaliação: julgamento de Bruno vai para segunda_avaliacao/",
                   st == 200 and r["arquivo"] == "segunda_avaliacao", str(r))
        _, linhas = le(original)
        verdadeiro("segunda avaliação: principal continua com o julgamento de Ana",
                   {l["url"]: l for l in linhas}[alvo[0]]["relevante"] == "2")
        seg = os.path.join(pasta, "segunda_avaliacao", "pool_q01.tsv")
        cs, ls = le(seg)
        verdadeiro("segunda avaliação: arquivo com url, relevante, avaliador",
                   cs == julgamento.COLUNAS_SEGUNDA and [(l["url"], l["relevante"], l["avaliador"]) for l in ls]
                   == [(alvo[0], "1", "Bruno")], str(ls))
        _, rb, _ = srv.get("/api/julgamento/q01", avaliador="Bruno")
        verdadeiro("segunda avaliação: Bruno vê o próprio julgamento",
                   {d["url"]: d for d in rb["documentos"]}[alvo[0]]["relevante"] == "1")
        srv.post("/api/julgamento/q01", {"url": alvo[0], "relevante": "2", "avaliador": "Bruno"})
        verdadeiro("segunda avaliação: Bruno muda o julgamento sem duplicar a linha",
                   [(l["relevante"]) for l in le(seg)[1]] == ["2"])

        # mudar e desfazer
        srv.post("/api/julgamento/q01", {"url": alvo[1], "relevante": "2", "avaliador": "ANA"})
        srv.post("/api/julgamento/q01", {"url": alvo[2], "relevante": "", "avaliador": "Ana"})
        por = {l["url"]: l for l in le(original)[1]}
        verdadeiro("mudar: Ana troca 1 por 2 (nome sem diferenciar maiúsculas)", por[alvo[1]]["relevante"] == "2")
        verdadeiro("desfazer: relevante, observação e avaliador apagados",
                   (por[alvo[2]]["relevante"], por[alvo[2]]["avaliador"]) == ("", ""))

        # erros
        casos = [({"url": alvo[0], "relevante": "3", "avaliador": "Ana"}, "q01", 400),
                 ({"url": alvo[0], "relevante": "1", "avaliador": "  "}, "q01", 400),
                 ({"url": "https://x.invalido/1", "relevante": "1", "avaliador": "Ana"}, "q01", 404),
                 ({"url": alvo[0], "relevante": "1", "avaliador": "Ana"}, "q99", 404),
                 ({"url": alvo[0], "relevante": "1", "avaliador": "Ana"}, "..%2Fx", 404),
                 ({"relevante": "1", "avaliador": "Ana"}, "q01", 400)]
        for corpo, cid, esperado in casos:
            st, r, _ = srv.post(f"/api/julgamento/{cid}", corpo)
            verdadeiro(f"erro {esperado}: {cid} {corpo.get('relevante')!r} {corpo.get('avaliador')!r}",
                       st == esperado and "erro" in r, f"{st} {r}")
        st, r, _ = srv.get("/api/julgamento/q01")
        verdadeiro("erro 400: listar documentos sem avaliador", st == 400 and "erro" in r)

        # concorrência: 15 julgamentos ao mesmo tempo em documentos diferentes
        urls = [d["url"] for d in srv.get("/api/julgamento/q05", avaliador="Carla")[1]["documentos"]][:15]
        res = []
        ts = [threading.Thread(target=lambda u=u: res.append(srv.post(
            "/api/julgamento/q05", {"url": u, "relevante": "1", "avaliador": "Carla"})[0])) for u in urls]
        [t.start() for t in ts]
        [t.join() for t in ts]
        por = {l["url"]: l for l in le(os.path.join(pasta, "pool_q05.tsv"))[1]}
        verdadeiro("concorrência: 15 gravações simultâneas, nenhuma perdida",
                   res.count(200) == 15 and all(por[u]["relevante"] == "1" for u in urls))
        st, _, _ = srv.get("/api/busca", q="log4j")
        verdadeiro("busca continua respondendo", st == 200)
        julgados_antes = srv.get("/api/julgamento", avaliador="Ana")[1]

    # retomada: novo servidor sobre os mesmos arquivos
    with ServidorTeste(indice, pasta_julgamentos=pasta) as srv:
        _, r, _ = srv.get("/api/julgamento", avaliador="Ana")
        verdadeiro("retomada: mesmo progresso depois de reiniciar o servidor",
                   r["julgados"] == julgados_antes["julgados"]
                   and r["consultas"] == julgados_antes["consultas"])
        _, r, _ = srv.get("/api/julgamento/q01", avaliador="Ana")
        meus = {d["url"]: d["relevante"] for d in r["documentos"]}
        verdadeiro("retomada: Ana vê os próprios julgamentos, na mesma ordem",
                   [d["url"] for d in r["documentos"]] == ordem_ana
                   and (meus[alvo[0]], meus[alvo[1]], meus[alvo[2]]) == ("2", "2", ""))
        verdadeiro("página /julgar servida", _pagina_ok(srv))

    # avaliar.py lê os julgamentos gravados (e não lê a segunda avaliação)
    qrels = os.path.join(pasta, "qrels.tsv")
    n, invalidos = avaliar.juntar(pasta, qrels)
    esperado = sum(1 for f in glob.glob(os.path.join(pasta, "pool_q*.tsv"))
                   for l in le(f)[1] if l["relevante"] in ("0", "1", "2"))
    verdadeiro("avaliar.py --juntar: lê os julgamentos da ferramenta (só o principal)",
               n == esperado == 2 + 15 and invalidos == 0, f"{n} x {esperado}")

    if com_pool:
        p = subprocess.run([sys.executable, "pool.py", "--indice", indice, "--saida", pasta],
                           capture_output=True, text=True, encoding="utf-8")
        _, linhas = le(original)
        por = {l["url"]: l for l in linhas}
        verdadeiro("pool.py regerado: mantém relevante e avaliador",
                   p.returncode == 0 and (por[alvo[0]]["relevante"], por[alvo[0]]["avaliador"]) == ("2", "Ana"),
                   p.stderr[-300:])


def _pagina_ok(srv):
    import urllib.request
    with urllib.request.urlopen(srv.base + "/julgar", timeout=30) as r:
        html = r.read().decode("utf-8")
    return r.status == 200 and "Julgamento de relevância" in html and "julgar.js" in html


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = argparse.ArgumentParser()
    a.add_argument("--indice", default="indice",
                   help="índice dos pools (padrão: indice; o indice_teste não tem a maioria dos documentos)")
    a.add_argument("--com-pool", action="store_true")
    args = a.parse_args()
    reais = hashes("julgamentos")
    tmp = tempfile.mkdtemp(prefix="julgamentos_teste_")
    pasta = os.path.join(tmp, "julgamentos")
    shutil.copytree("julgamentos", pasta)
    # a cópia começa sem julgamentos (os pools reais podem já estar julgados)
    shutil.rmtree(os.path.join(pasta, julgamento.PASTA_SEGUNDA), ignore_errors=True)
    for f in glob.glob(os.path.join(pasta, "pool_q*.tsv")):
        col, linhas = le(f)
        for l in linhas:
            l["relevante"] = l["observacao"] = ""
            l.pop("avaliador", None)
        julgamento.grava_tsv(f, [c for c in col if c != "avaliador"], linhas)
    try:
        testes(args.indice, pasta, args.com_pool)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    verdadeiro("arquivos reais de julgamentos/ intactos (hash)", hashes("julgamentos") == reais)
    for f in FALHAS:
        print("  FALHA:", f)
    print(f"\n{N_OK} verificações OK, {len(FALHAS)} falhas ({args.indice})")
    sys.exit(1 if FALHAS else 0)


if __name__ == "__main__":
    main()
