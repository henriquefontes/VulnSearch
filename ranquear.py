# ranquear.py - busca ranqueada sobre o índice (linha de comando)
# Uso:
#   python ranquear.py "sql injection wordpress"                 BM25F, top 10
#   python ranquear.py "buffer overflow" --modelo vetorial -k 20
#   python ranquear.py "log4j" --modelo bm25 --k1 1.2 --b 0.75
#   python ranquear.py "log4j" --modelo bm25f --peso-titulo 3 --peso-codigo 0.5
#   python ranquear.py "CVE-2021-44228" --explicar               parcelas de cada termo e campo
#   python ranquear.py --comparar "remote code execution"        top 10 dos modelos lado a lado
#   python ranquear.py                                           modo interativo
#
# Sintaxe da consulta: palavras soltas (união das listas), "frase" (filtro por
# posição), -palavra ou NOT palavra (exclui), codigo:termo (só no código).
# No PowerShell, as aspas de uma frase passada como argumento se perdem; use o
# modo interativo ou --frase "denial of service".
#
# Comandos do modo interativo (linha começando com ':'):
#   :modelo bm25   :k 20   :explicar   :comparar   :params   :sair
import argparse
import inspect
import sys
import time

from ranqueamento import MODELOS, MODELO_PADRAO, VARIANTES_IDF, Ranqueador

LARGURA_TITULO = 80


def params_do_modelo(modelo, opcoes):
    """Só os parâmetros que o método do modelo aceita (None = padrão)."""
    aceitos = inspect.signature(getattr(Ranqueador, modelo)).parameters
    return {k: v for k, v in opcoes.items() if k in aceitos and v is not None}


def opcoes_de(a):
    return {"k1": a.k1, "b": a.b, "peso_titulo": a.peso_titulo, "peso_corpo": a.peso_corpo,
            "peso_codigo": a.peso_codigo, "esquema": a.esquema, "tf": a.tf, "idf": a.idf,
            "b_titulo": a.b if a.b is not None else None,
            "b_corpo": a.b if a.b is not None else None,
            "b_codigo": a.b if a.b is not None else None}


def corta(s, n=LARGURA_TITULO):
    return s if len(s) <= n else s[:n - 1] + "…"


def fmt(v):
    if isinstance(v, float):
        return f"{v:.4g}"
    if isinstance(v, dict):
        return "{" + ", ".join(f"{k} {fmt(x)}" for k, x in v.items()) + "}"
    return str(v)


def mostra(r, res, explicar=False):
    p = ", ".join(f"{k}={v}" for k, v in res.params.items())
    print(f"[{res.modelo}{' ' + p if p else ''}] {res.n_candidatos} candidatos, "
          f"{res.n_positivos} com escore > 0, {res.postings} postings lidos, {res.ms:.1f} ms")
    for aviso in res.avisos:
        print(f"  aviso: {aviso}")
    if not res.top:
        print("  nenhum documento")
    for i, (d, s) in enumerate(res.top, 1):
        doc = r.documento(d)
        print(f"{i:3}. {s:9.4f}  {doc['site'].replace('www.', ''):<20} "
              f"{corta(doc['titulo'] or '(sem título)')}\n"
              f"{'':16}{doc['url']}  [doc {d}]")
        if explicar:
            for parcela in res.detalhes.get(d, []):
                print(f"{'':16}· " + "  ".join(f"{k} {fmt(v)}" for k, v in parcela.items()))


def compara(r, consulta, k, opcoes):
    resultados = []
    for m in MODELOS:
        resultados.append(r.ranquear(consulta, m, k, **params_do_modelo(m, opcoes)))
    print(f"Consulta: {consulta}  (documentos por id; títulos abaixo)")
    print("pos " + "".join(f"{m:>9}" for m in MODELOS))
    for i in range(k):
        linha = ""
        for res in resultados:
            linha += f"{res.top[i][0]:>9}" if i < len(res.top) else f"{'-':>9}"
        print(f"{i + 1:>3} " + linha)
    print("ms  " + "".join(f"{res.ms:>9.1f}" for res in resultados))
    vistos = sorted({d for res in resultados for d, _ in res.top})
    print()
    for d in vistos:
        doc = r.documento(d)
        em = sum(1 for res in resultados if d in {x for x, _ in res.top})
        print(f"{d:>7} ({em}/{len(MODELOS)}) {doc['site'].replace('www.', ''):<20} "
              f"{corta(doc['titulo'] or doc['url'], 70)}")


def executa(r, consulta, estado):
    if estado["comparar"]:
        compara(r, consulta, estado["k"], estado["opcoes"])
    else:
        m = estado["modelo"]
        res = r.ranquear(consulta, m, estado["k"], explicar=estado["explicar"],
                         **params_do_modelo(m, estado["opcoes"]))
        mostra(r, res, estado["explicar"])


def interativo(r, estado):
    print("Modo interativo. Comandos: :modelo NOME, :k N, :explicar, :comparar, :params, "
          ":sair (ou linha vazia).")
    while True:
        try:
            linha = input(f"\n{estado['modelo']}> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not linha or linha in (":sair", ":q"):
            break
        if linha.startswith(":"):
            cmd, _, arg = linha[1:].partition(" ")
            if cmd == "modelo" and arg in MODELOS:
                estado["modelo"] = arg
            elif cmd == "k" and arg.isdigit():
                estado["k"] = int(arg)
            elif cmd in ("explicar", "comparar"):
                estado[cmd] = not estado[cmd]
                print(f"{cmd}: {'ligado' if estado[cmd] else 'desligado'}")
            elif cmd == "params":
                print({k: v for k, v in estado["opcoes"].items() if v is not None} or "padrão")
            else:
                print(f"comando inválido; modelos: {', '.join(MODELOS)}")
            continue
        executa(r, linha, estado)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Busca ranqueada no índice do VulnSearch.")
    p.add_argument("consulta", nargs="*")
    p.add_argument("--indice", default="indice")
    p.add_argument("--modelo", choices=MODELOS, default=MODELO_PADRAO)
    p.add_argument("-k", type=int, default=10, help="tamanho do top-k (padrão: 10)")
    p.add_argument("--k1", type=float, help="K₁ da família BM (padrão: 1,2)")
    p.add_argument("--b", type=float, help="b do BM25 e de todos os campos do BM25F (0,75)")
    p.add_argument("--peso-titulo", type=float, help="BM25F (padrão: 2)")
    p.add_argument("--peso-corpo", type=float, help="BM25F (padrão: 1)")
    p.add_argument("--peso-codigo", type=float,
                   help="α do código nos modelos sem campos, ou peso do campo código no "
                        "BM25F (padrão: 1)")
    p.add_argument("--esquema", type=int, choices=[1, 2, 3], help="vetorial (padrão: 3)")
    p.add_argument("--tf", choices=["log", "bruto"], help="TF-IDF (padrão: log)")
    p.add_argument("--idf", choices=list(VARIANTES_IDF),
                   help="IDF da família BM (padrão: limitado+recurso = limitado a 0, mas "
                        "log(1 + ·) se todas as palavras da consulta tiverem n > N/2)")
    p.add_argument("--frase", action="append", default=[],
                   help="acrescenta uma frase entre aspas à consulta (útil no PowerShell)")
    p.add_argument("--explicar", action="store_true", help="parcelas de cada termo e campo")
    p.add_argument("--comparar", action="store_true", help="top-k de todos os modelos")
    a = p.parse_args()
    t = time.perf_counter()
    r = Ranqueador.abre(a.indice)
    print(f"Índice e estatísticas carregados: {len(r.ind.vocabulario)} termos, {r.N} documentos "
          f"({time.perf_counter() - t:.1f} s)")
    estado = {"modelo": a.modelo, "k": a.k, "explicar": a.explicar, "comparar": a.comparar,
              "opcoes": opcoes_de(a)}
    consulta = " ".join(a.consulta + [f'"{f}"' for f in a.frase])
    if consulta:
        executa(r, consulta, estado)
    else:
        interativo(r, estado)


if __name__ == "__main__":
    main()
