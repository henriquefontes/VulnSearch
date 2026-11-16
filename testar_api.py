# testar_api.py - testes do backend Web (servidor.py, trechos.py, textos.py)
# Uso: python testar_api.py [--indice indice_teste]
#      python testar_api.py --indice indice --gravar-exemplos   (grava exemplos_api/*.json)
#
# Sobe o servidor numa thread, numa porta livre, e faz requisições com urllib.
# Compara a API com o Ranqueador direto (o mesmo que o ranquear.py usa).
# Os testes do ranqueamento continuam em testar_ranking.py.
import argparse
import json
import os
import random
import re
import sys
import tempfile
import threading

import lexico
import trechos
from cliente_api import ServidorTeste
from ranqueamento import Consulta, Ranqueador
from textos import Textos

FALHAS = []
N_OK = 0


def verdadeiro(nome, cond, detalhe=""):
    global N_OK
    if cond:
        N_OK += 1
    else:
        FALHAS.append(nome + (f" ({detalhe})" if detalhe else ""))


def texto(segs):
    return "".join(s["texto"] for s in segs or [])


def destacados(segs):
    return [s["texto"] for s in segs or [] if s["destaque"]]


def ids(js):
    return [r["id"] for r in js["resultados"]]


# ================================================================ trechos
def destaque(consulta):
    from ranqueamento import ProcessadorConsulta
    return trechos.Destaque.de_consulta(ProcessadorConsulta().analisa(consulta))


def testes_trechos(pasta):
    d = destaque("sql injection")
    g = trechos.gera({"titulo": "WordPress Plugin X - SQL Injection",
                      "texto": "A blind SQL Injection in the id parameter."}, d)
    verdadeiro("trechos: 'SQL Injection' destacado no título", "SQL Injection" in destacados(g["titulo"]))
    verdadeiro("trechos: título inteiro preservado",
               texto(g["titulo"]) == "WordPress Plugin X - SQL Injection")
    g = trechos.gera({"titulo": "Multiple SQL Injections"}, d)
    verdadeiro("trechos: 'Injections' destacado (stemming)",
               "SQL Injections" in destacados(g["titulo"]), str(g["titulo"]))
    g = trechos.gera({"titulo": "x", "texto": "A heap use-after-free in the parser."},
                     destaque('"use after free"'))
    verdadeiro("trechos: 'use-after-free' destacado inteiro pela frase",
               "use-after-free" in destacados(g["trecho"]), str(g["trecho"]))
    g = trechos.gera({"titulo": "x", "texto": "Remote denial of service via crafted packets."},
                     destaque('"denial of service"'))
    verdadeiro("trechos: frase com stopword interna destacada inteira",
               "denial of service" in destacados(g["trecho"]), str(g["trecho"]))
    g = trechos.gera({"titulo": "Apache Log4j", "texto": "Fixed in 2.15 (CVE-2021-44228)."},
                     destaque("CVE-2021-44228"))
    verdadeiro("trechos: CVE-2021-44228 destacado inteiro",
               "CVE-2021-44228" in destacados(g["trecho"]), str(g["trecho"]))
    g = trechos.gera({"titulo": "x", "texto": "EDB-ID: 1\nCVE:\n2006-0660\nAuthor: y"},
                     destaque("CVE-2006-0660"))
    verdadeiro("trechos: CVE sem prefixo da ficha do exploit-db destacado",
               "2006-0660" in destacados(g["trecho"]), str(g["trecho"]))
    codigo = "int main() {\n  char buf[8];\n  strcpy(buf, argv[1]);\n  return 0;\n}"
    g = trechos.gera({"titulo": "x", "texto": "overflow", "codigo": codigo}, destaque("strcpy"))
    verdadeiro("trechos: 'strcpy' destacado no trecho de código",
               "strcpy" in destacados(g["trecho_codigo"]), str(g["trecho_codigo"]))
    verdadeiro("trechos: quebras de linha preservadas no código",
               "\n" in texto(g["trecho_codigo"]))
    g = trechos.gera({"titulo": "Configuração INSEGURA", "texto": "Uma configuração insegura."},
                     destaque("configuracao"))
    verdadeiro("trechos: acentos e maiúsculas preservados no texto devolvido",
               "Configuração" in destacados(g["titulo"])
               and "configuração" in destacados(g["trecho"]), str(g))
    g = trechos.gera({}, destaque("sql"))
    verdadeiro("trechos: documento vazio", g == {"titulo": [], "trecho": [],
                                                 "trecho_codigo": None}, str(g))
    g = trechos.gera({"titulo": "", "texto": "", "codigo": "x = system(cmd)\nprint(x)"},
                     destaque("system"))
    verdadeiro("trechos: documento só com código (trecho e trecho_codigo)",
               "system" in destacados(g["trecho"]) and "system" in destacados(g["trecho_codigo"]),
               str(g))
    g = trechos.gera({"titulo": "Nada a ver", "texto": "Texto sem os termos. " * 30}, d)
    verdadeiro("trechos: sem casamento -> início do texto sem destaque, ~220 caracteres",
               not destacados(g["trecho"]) and len(texto(g["trecho"])) <= trechos.JANELA + 2)
    longo = "intro " * 200 + "sql here " + "middle " * 200 + "injection there " + "fim " * 50
    g = trechos.gera({"titulo": "x", "texto": longo}, d)
    verdadeiro("trechos: termos distantes -> duas janelas separadas por ' … '",
               " … " in texto(g["trecho"]) and set(destacados(g["trecho"])) == {"sql", "injection"},
               texto(g["trecho"]))
    vizinhos = all(a["destaque"] != b["destaque"] for a, b in zip(g["trecho"], g["trecho"][1:]))
    verdadeiro("trechos: segmentos vizinhos de mesmo tipo unidos", vizinhos)

    testes_trechos_exploitdb(pasta)

    # posições: tokens_com_posicao == tokens() em documentos reais
    tx = Textos(pasta)
    rnd = random.Random(5)
    iguais = True
    for doc in rnd.sample(range(len(tx)), min(300, len(tx))):
        c = tx.campos(doc)
        for k in ("titulo", "descricao", "palavras_chave", "texto"):
            if [t for t, _, _ in lexico.tokens_com_posicao(c[k])] != lexico.tokens(c[k]):
                iguais = False
    verdadeiro("lexico: tokens_com_posicao = tokens em 300 documentos reais", iguais)
    tx.fecha()


FICHA = ("{t}\nEDB-ID:\n12345\nCVE:\n2020-1111\n2020-2222\nEDB Verified:\nAuthor:\nfulano\n"
         "Type:\nwebapps\nExploit:\n/\nPlatform:\nPHP\nDate:\n2020-01-01\nVulnerable App:\n"
         "Tags:\nAdvisory/Source:\nLink")


def testes_trechos_exploitdb(pasta):
    """Exploit-db: título + ficha fora da janela do trecho; separadores fora do
    trecho de código; outros sites sem mudança."""
    tit = "WordPress Plugin X 1.0 - SQL Injection"
    ficha = trechos.ficha_exploitdb(FICHA.format(t=tit), tit)
    verdadeiro("ficha: pares rótulo/valor, vários CVEs, sem rótulos vazios nem '/', 'Link'",
               ficha is not None and ficha[0] == [
                   ("EDB-ID", ["12345"]), ("CVE", ["2020-1111", "2020-2222"]), ("Author", ["fulano"]),
                   ("Type", ["webapps"]), ("Platform", ["PHP"]), ("Date", ["2020-01-01"])],
               str(ficha))
    verdadeiro("ficha: texto de outro site não é reconhecido",
               trechos.ficha_exploitdb("Advisory X\nPackage: npm\nEDB-ID:\n1", "Advisory X") is None)

    codigo = ("# Exploit Title: X\n#####################\n\n# Date: 2020\n"
              "======================\n---- \n   \n"
              "Blind SQL injection in the id parameter\n* * * ~~~ ***\n\n"
              "payload = \"1 OR 1=1\"\nsend(payload)\nprint('ok')\n")
    d = destaque("sql injection")
    g = trechos.gera({"titulo": tit, "texto": FICHA.format(t=tit), "codigo": codigo}, d)
    tr = texto(g["trecho"])
    verdadeiro("exploit-db: trecho sem a ficha e sem repetir o título",
               "EDB-ID" not in tr and "Author" not in tr and not tr.lstrip("… ").startswith(tit), tr)
    verdadeiro("exploit-db: trecho vem do código, com destaque",
               "SQL injection" in destacados(g["trecho"]) and "Blind" in tr, tr)
    linhas = texto(g["trecho_codigo"]).split("\n")
    verdadeiro("exploit-db: trecho_codigo sem linhas vazias ou só de separadores",
               not any(trechos.SEPARADOR.match(x) for x in linhas), repr(linhas))
    verdadeiro("exploit-db: trecho_codigo com 5 linhas úteis em volta do casamento",
               len(linhas) == 5 and any("SQL injection" in x for x in linhas)
               and linhas[0] == "# Exploit Title: X" and linhas[-1] == "send(payload)", repr(linhas))
    verdadeiro("exploit-db: separadores também fora do trecho em linha", "####" not in tr
               and "~~~" not in tr and "====" not in tr, tr)

    g = trechos.gera({"titulo": tit, "texto": FICHA.format(t=tit), "codigo": "print('nada')\n"},
                     destaque("wordpress"))
    verdadeiro("exploit-db sem casamento no código: linha curta Type/Platform/Date",
               texto(g["trecho"]) == "Type: webapps · Platform: PHP · Date: 2020-01-01"
               and g["trecho_codigo"] is None, str(g))
    g = trechos.gera({"titulo": tit, "texto": FICHA.format(t=tit)}, destaque("php"))
    verdadeiro("exploit-db sem código: linha curta com o termo destacado",
               destacados(g["trecho"]) == ["PHP"], str(g["trecho"]))

    # outros sites: o mesmo código mantém o comportamento anterior (linhas vazias e
    # separadores no meio continuam; o trecho vem do texto)
    g = trechos.gera({"titulo": "Advisory", "texto": "A SQL injection in X.", "codigo": codigo}, d)
    linhas = texto(g["trecho_codigo"]).split("\n")
    verdadeiro("outros sites: trecho do texto e trecho_codigo como antes",
               texto(g["trecho"]).startswith("A SQL injection in X")
               and destacados(g["trecho"]) == ["SQL injection"]
               and any(trechos.SEPARADOR.match(x) for x in linhas), repr(linhas))

    # documentos reais do exploit-db: nenhum trecho com a ficha ou começando pelo título
    tx = Textos(pasta)
    vistos = ruins = 0
    for doc in range(len(tx)):
        c = tx.campos(doc)
        if not trechos.ficha_exploitdb(c["texto"], c["titulo"]):
            continue
        palavras = [w for w in lexico.tokens(c["titulo"]) if len(w) > 3]
        if not palavras:
            continue
        g = trechos.gera(c, destaque(max(palavras, key=len)))
        tr = texto(g["trecho"])
        if "EDB-ID:" in tr or (c["titulo"] and tr.lstrip("… ").startswith(c["titulo"])):
            ruins += 1
        vistos += 1
        if vistos == 300:
            break
    tx.fecha()
    verdadeiro(f"exploit-db reais: {vistos} trechos sem ficha nem título no início",
               vistos > 0 and ruins == 0, f"{ruins} de {vistos}")


# ================================================================== API
def testes_api(pasta):
    r = Ranqueador.abre(pasta)  # o mesmo ranqueamento do ranquear.py
    logs = tempfile.mkdtemp()
    with ServidorTeste(pasta, pasta_logs=logs) as srv:
        motor = srv.app.state.motor
        get = srv.get

        st, js, _ = get("/api/busca", q="sql injection wordpress")
        esperado = [d for d, _ in r.ranquear("sql injection wordpress", "bm25f", 10).top]
        verdadeiro("busca simples: 200 e 10 resultados", st == 200 and len(js["resultados"]) == 10,
                   f"{st}, {len(js.get('resultados', []))}")
        verdadeiro("busca simples: ordem = ranquear.py (bm25f)", ids(js) == esperado)
        for m in ("tfidf", "bm25", "vetorial"):
            st, js, _ = get("/api/busca", q="buffer overflow", modelo=m)
            verdadeiro(f"busca com modelo {m}: ordem = ranquear.py",
                       ids(js) == [d for d, _ in r.ranquear("buffer overflow", m, 10).top])
        st, js, _ = get("/api/busca", q="buffer overflow", modelo="bm25", k1=2.0, b=0.3)
        verdadeiro("parâmetros k1 e b repassados ao modelo",
                   ids(js) == [d for d, _ in r.ranquear("buffer overflow", "bm25", 10, k1=2.0,
                                                        b=0.3).top]
                   and js["parametros"] == {"k1": 2.0, "b": 0.3, "peso_codigo": 1.0})
        st, js, _ = get("/api/busca", q="buffer overflow", modelo="bm25f", peso_titulo=5, b=0.5)
        verdadeiro("parâmetros do BM25F repassados (b nos três campos)",
                   ids(js) == [d for d, _ in r.ranquear("buffer overflow", "bm25f", 10,
                                                        peso_titulo=5, b_titulo=0.5, b_corpo=0.5,
                                                        b_codigo=0.5).top])

        # paginação e cache
        _, p1, _ = get("/api/busca", q="sql injection")
        _, p2, _ = get("/api/busca", q="sql injection", pagina=2)
        _, p12, _ = get("/api/busca", q="sql injection", por_pagina=20)
        verdadeiro("paginação: página 2 com 10 resultados diferentes da 1",
                   len(p2["resultados"]) == 10 and not set(ids(p1)) & set(ids(p2)))
        verdadeiro("paginação: páginas 1 + 2 = página 1 com por_pagina=20",
                   ids(p1) + ids(p2) == ids(p12))
        verdadeiro("paginação: posições contínuas",
                   [x["posicao"] for x in p2["resultados"]] == list(range(11, 21)))
        verdadeiro("cache: página 2 não refaz o ranqueamento", p2["cache"] is True)
        verdadeiro("paginas = ⌈min(total, 500)/por_pagina⌉",
                   p1["paginas"] == -(-min(p1["total"], 500) // 10))
        _, fora, _ = get("/api/busca", q="sql injection", pagina=51)
        verdadeiro("página além de 500 resultados: vazia e com aviso",
                   not fora["resultados"] and any("500" in a for a in fora["avisos"]))

        # filtros e facetas
        site = "www.exploit-db.com"
        _, sem, _ = get("/api/busca", q="sql injection")
        _, com, _ = get("/api/busca", q="sql injection", site=site)
        verdadeiro("filtro site: todos os resultados do site",
                   com["resultados"] and all(x["site"] == site for x in com["resultados"]))
        verdadeiro("filtro site: total = faceta do site", com["total"] == sem["facetas"]["sites"]
                   .get(site) and com["facetas"] == sem["facetas"])
        esperado = {d: s for d, s in r.ranquear("sql injection", "bm25f", 1).positivos.items()
                    if motor.sites[d] == site}
        from ranqueamento import top_k
        verdadeiro("filtro site: ordem = top-k dos positivos do site",
                   ids(com) == [d for d, _ in top_k(esperado, 10)])
        _, dois, _ = get("/api/busca", q="sql injection", site=[site, "github.com"])
        verdadeiro("filtro site repetido: união dos sites",
                   dois["total"] == sem["facetas"]["sites"].get(site, 0)
                   + sem["facetas"]["sites"].get("github.com", 0))
        cve = max(motor.por_cve, key=lambda c: len(motor.por_cve[c]))
        _, jc, _ = get("/api/busca", q=cve, cve=cve.lower())
        verdadeiro(f"filtro cve ({cve}, minúsculas): só documentos com o CVE",
                   jc["resultados"] and all(cve in x["cves"] for x in jc["resultados"]))
        cwe = max(motor.por_cwe, key=lambda c: len(motor.por_cwe[c]))
        _, jw, _ = get("/api/busca", q="injection", cwe=cwe)
        verdadeiro(f"filtro cwe ({cwe}): só documentos com o CWE",
                   all(cwe in x["cwes"] for x in jw["resultados"]))
        _, jx, _ = get("/api/busca", q="injection", cwe=cwe, site=site)
        verdadeiro("filtros combinados (cwe + site): interseção",
                   all(cwe in x["cwes"] and x["site"] == site for x in jx["resultados"]))

        # frase, negação, código
        q = '"denial of service" -wordpress'
        _, jf, _ = get("/api/busca", q=q)
        verdadeiro("frase e negação: igual ao ranquear.py",
                   ids(jf) == [d for d, _ in r.ranquear(q, "bm25f", 10).top] and jf["resultados"])
        _, jcod, _ = get("/api/busca", q="codigo:strcpy")
        verdadeiro("codigo:strcpy: trecho_codigo com 'strcpy' destacado",
                   jcod["resultados"] and all(
                       any(t.lower() == "strcpy" for t in destacados(x["trecho_codigo"]))
                       for x in jcod["resultados"]))

        # avisos
        _, js, _ = get("/api/busca", q="the of and")
        verdadeiro("consulta só de stopwords: 200, total 0 e aviso",
                   js["total"] == 0 and any("termos indexáveis" in a for a in js["avisos"]))
        _, js, _ = get("/api/busca", q="xyzzyqwertyuiop")
        verdadeiro("termo inexistente: 200, total 0 e aviso",
                   js["total"] == 0 and any("não encontrado" in a for a in js["avisos"]))
        _, js, _ = get("/api/busca", q="vulnerability")
        verdadeiro("'vulnerability': resultados e aviso do recurso do IDF",
                   js["total"] > 0 and any("recurso do IDF" in a for a in js["avisos"]))
        _, js, _ = get("/api/busca", q=" ".join(f"p{i}" for i in range(40)))
        verdadeiro("mais de 32 palavras: usa as 32 primeiras e avisa",
                   any("32" in a for a in js["avisos"]) and len(js["consulta"].split()) == 32)
        _, js, _ = get("/api/busca", q="sql injection", explicar=True, por_pagina=2)
        verdadeiro("explicar: parcelas por termo nos resultados",
                   js["resultados"] and all(x["explicacao"] for x in js["resultados"]))

        # erros
        for nome, params in [("q vazio", {"q": ""}), ("q ausente", {}),
                             ("q com 201 caracteres", {"q": "a" * 201}),
                             ("modelo inválido", {"q": "x", "modelo": "foo"}),
                             ("pagina=0", {"q": "x", "pagina": 0}),
                             ("por_pagina=51", {"q": "x", "por_pagina": 51}),
                             ("pagina não numérica", {"q": "x", "pagina": "abc"}),
                             ("site desconhecido", {"q": "x", "site": "example.com"}),
                             ("cve mal formado", {"q": "x", "cve": "2021-44228"}),
                             ("b fora do intervalo", {"q": "x", "b": 2})]:
            st, js, _ = get("/api/busca", **params)
            verdadeiro(f"erro 400: {nome}", st == 400 and isinstance(js.get("erro"), str)
                       and js["erro"], f"{st} {js}")

        # documento e demais rotas
        st, js, _ = get("/api/documento/0")
        verdadeiro("/api/documento válido", st == 200 and js["id"] == 0 and "texto" in js
                   and "codigo_truncado" in js)
        st, js, _ = get(f"/api/documento/{motor.N}")
        verdadeiro("/api/documento inexistente: 404 com erro", st == 404 and "erro" in js)
        st, js, _ = get("/api/documento/abc")
        verdadeiro("/api/documento com id não numérico: 400", st == 400)
        st, js, _ = get("/api/modelos")
        verdadeiro("/api/modelos: 8 modelos", st == 200 and len(js["modelos"]) == 8)
        st, js, _ = get("/api/sites")
        verdadeiro("/api/sites: soma = N", st == 200 and sum(s["documentos"] for s in js["sites"])
                   == motor.N)
        st, js, _ = get("/api/estatisticas")
        verdadeiro("/api/estatisticas", st == 200 and js["documentos"] == motor.N)
        st, js, _ = get("/api/saude")
        verdadeiro("/api/saude", st == 200 and js["ok"] is True)
        st, js, _ = get("/api/inexistente")
        verdadeiro("rota inexistente: 404 com erro em JSON", st == 404 and "erro" in js)

        # concorrência (testa o lock): 20 requisições simultâneas
        consultas = ["sql injection", "buffer overflow", "remote code execution", "xss",
                     "log4j", "path traversal", "denial of service", "csrf", "privilege escalation",
                     "use after free"] * 2
        motor.cache.clear()
        sequencial = {q: ids(get("/api/busca", q=q, modelo="bm25")[1]) for q in set(consultas)}
        motor.cache.clear()
        resultados = [None] * len(consultas)

        def tarefa(i, q):
            resultados[i] = get("/api/busca", q=q, modelo="bm25")

        ts = [threading.Thread(target=tarefa, args=(i, q)) for i, q in enumerate(consultas)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        verdadeiro("20 requisições simultâneas: todas 200 e iguais às sequenciais",
                   all(x[0] == 200 and ids(x[1]) == sequencial[q]
                       for x, q in zip(resultados, consultas)))

        # formato: nenhum HTML montado pelo servidor
        _, js, _ = get("/api/busca", q="xss script alert", por_pagina=20)
        bruto = json.dumps(js, ensure_ascii=False)
        ok = "<mark" not in bruto.lower()
        for x in js["resultados"]:
            ok &= all(set(s) == {"texto", "destaque"} and isinstance(s["texto"], str)
                      for s in x["titulo"] + x["trecho"] + (x["trecho_codigo"] or []))
            original = motor.documento(x["id"])["titulo"]
            ok &= texto(x["titulo"]) == re.sub(r"\s+", " ", original)
        verdadeiro("formato: só segmentos {texto, destaque}, sem HTML; título = texto original",
                   ok)

        # registro das consultas
        caminho = os.path.join(logs, "consultas.tsv")
        with open(caminho, encoding="utf-8") as f:
            linhas = f.read().splitlines()
        verdadeiro("registro: logs/consultas.tsv com cabeçalho e uma linha por busca",
                   linhas[0].split("\t") == ["data", "consulta", "modelo", "filtros", "total",
                                             "ms", "pagina"] and len(linhas) > 40)


# ============================================================ exemplos
EXEMPLOS = [
    ("busca", "/api/busca", {"q": "sql injection wordpress"}),
    ("busca_pagina2", "/api/busca", {"q": "sql injection wordpress", "pagina": 2}),
    ("busca_filtro", "/api/busca", {"q": "log4j", "site": "www.exploit-db.com",
                                    "cve": "CVE-2021-44228"}),
    ("busca_codigo", "/api/busca", {"q": "codigo:strcpy", "por_pagina": 3}),
    ("busca_frase", "/api/busca", {"q": '"denial of service" -wordpress', "por_pagina": 3}),
    ("busca_modelo", "/api/busca", {"q": "buffer overflow", "modelo": "bm25", "k1": 1.5,
                                    "b": 0.5, "por_pagina": 3}),
    ("busca_explicar", "/api/busca", {"q": "CVE-2021-44228", "explicar": True,
                                      "por_pagina": 2}),
    ("busca_recurso_idf", "/api/busca", {"q": "vulnerability", "por_pagina": 3}),
    ("busca_vazia", "/api/busca", {"q": "the of and"}),
    ("erro_400", "/api/busca", {"q": "x", "pagina": 0}),
    ("documento", "/api/documento/38165", {}),
    ("erro_404", "/api/documento/999999", {}),
    ("modelos", "/api/modelos", {}),
    ("sites", "/api/sites", {}),
    ("estatisticas", "/api/estatisticas", {}),
    ("saude", "/api/saude", {}),
]


def grava_exemplos(pasta, saida="exemplos_api"):
    os.makedirs(saida, exist_ok=True)
    with ServidorTeste(pasta, pasta_logs=None) as srv:
        for nome, rota, params in EXEMPLOS:
            st, js, _ = srv.get(rota, **params)
            url = rota + ("?" + "&".join(f"{k}={v}" for k, v in params.items()) if params else "")
            with open(os.path.join(saida, nome + ".json"), "w", encoding="utf-8",
                      newline="\n") as f:
                json.dump({"requisicao": "GET " + url, "status": st, "resposta": js}, f,
                          ensure_ascii=False, indent=2)
            print(f"  {st} {nome}.json  ({url})")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser()
    p.add_argument("--indice", default="indice_teste")
    p.add_argument("--gravar-exemplos", action="store_true",
                   help="grava exemplos_api/*.json (use com --indice indice)")
    a = p.parse_args()
    if a.gravar_exemplos:
        grava_exemplos(a.indice)
        return
    testes_trechos(a.indice)
    testes_api(a.indice)
    print(f"\n{N_OK} verificações OK, {len(FALHAS)} falhas ({a.indice})")
    for f in FALHAS:
        print("  FALHA:", f)
    sys.exit(1 if FALHAS else 0)


if __name__ == "__main__":
    main()
