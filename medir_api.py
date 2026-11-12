# medir_api.py - latência e vazão do backend Web, ponta a ponta (HTTP + JSON)
# Uso: python medir_api.py [--indice indice] [--saida resultados_web] [--reps 3]
#
# Sobe o servidor numa thread (como o testar_api.py) e usa as 20 consultas de
# consultas.tsv. Grava em --saida (CSV + Markdown) e resumo.json:
#   latencia          por consulta: cliente (ponta a ponta), servidor (ranqueamento,
#                     trechos, total) e o resto (serialização + HTTP), sem cache
#   latencia_resumo   média, mediana, p95 e máximo de cada parte
#   paginacao         página 1 (sem cache) × página 2 (cache)
#   filtro            sem filtro × site=www.exploit-db.com × cve (sem cache)
#   vazao             1, 4 e 8 clientes simultâneos (sem cache): req/s e latências
import argparse
import json
import os
import statistics
import sys
import threading
import time

from avaliar import le_consultas
from cliente_api import ServidorTeste
from etapas import grava
from indice import pico_memoria_mb

META_P95_MS = 300


def pct(v, p):
    v = sorted(v)
    if not v:
        return 0.0
    k = (len(v) - 1) * p / 100
    a = int(k)
    b = min(a + 1, len(v) - 1)
    return v[a] + (v[b] - v[a]) * (k - a)


def resumo(v):
    return {"media": statistics.mean(v), "mediana": statistics.median(v), "p95": pct(v, 95),
            "max": max(v)}


def f1(x):
    return f"{x:.1f}"


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser()
    p.add_argument("--indice", default="indice")
    p.add_argument("--saida", default="resultados_web")
    p.add_argument("--reps", type=int, default=3)
    a = p.parse_args()
    os.makedirs(a.saida, exist_ok=True)
    consultas = le_consultas()
    t_inicio = time.perf_counter()

    with ServidorTeste(a.indice, pasta_logs=None) as srv:
        motor = srv.app.state.motor
        mem_carga = motor.memoria_mb
        get = srv.get
        motor.usar_cache = False
        for c in consultas:  # aquecimento (cache do disco)
            get("/api/busca", q=c["consulta"])

        # 1. latência por consulta, sem cache
        linhas, partes = [], {"cliente": [], "ranqueamento": [], "trechos": [],
                              "servidor": [], "resto": []}
        for c in consultas:
            med = {k: [] for k in partes}
            for _ in range(a.reps):
                st, js, ms = get("/api/busca", q=c["consulta"])
                assert st == 200, js
                t = js["tempo_ms"]
                valores = {"cliente": ms, "ranqueamento": t["ranqueamento"],
                           "trechos": t["trechos"], "servidor": t["total"],
                           "resto": ms - t["total"]}
                for k, v in valores.items():
                    med[k].append(v)
                    partes[k].append(v)
            linhas.append([c["id"], c["consulta"], js["total"], len(js["resultados"])]
                          + [f1(statistics.median(med[k])) for k in partes])
        grava(a.saida, "latencia", ["id", "consulta", "total", "resultados", "cliente ms",
                                    "ranqueamento ms", "trechos ms", "servidor ms",
                                    "serialização + HTTP ms"], linhas,
              f"Latência por consulta (mediana de {a.reps} repetições, sem cache, 10 "
              "resultados por página, BM25F). Cliente = ponta a ponta (urllib); servidor = "
              "tempo dentro do /api/busca; o resto é serialização JSON + HTTP.")
        res_lat = {k: resumo(v) for k, v in partes.items()}
        grava(a.saida, "latencia_resumo", ["parte", "média ms", "mediana ms", "p95 ms",
                                           "máx. ms"],
              [[k] + [f1(res_lat[k][x]) for x in ("media", "mediana", "p95", "max")]
               for k in partes],
              f"Resumo da latência ({len(consultas)} consultas × {a.reps} repetições, sem "
              f"cache). Meta: p95 ponta a ponta < {META_P95_MS} ms.")

        # 2. página 1 (sem cache) x página 2 (cache)
        motor.usar_cache = True
        p1, p2 = [], []
        for c in consultas:
            motor.cache.clear()
            _, j1, m1 = get("/api/busca", q=c["consulta"])
            _, j2, m2 = get("/api/busca", q=c["consulta"], pagina=2)
            p1.append(m1)
            p2.append(m2)
            assert not j1["cache"] and (j2["cache"] or not j2["total"]), (j1["cache"], j2["cache"])
        grava(a.saida, "paginacao", ["página", "média ms", "mediana ms", "p95 ms", "máx. ms"],
              [[n] + [f1(resumo(v)[x]) for x in ("media", "mediana", "p95", "max")]
               for n, v in (("1 (ranqueia)", p1), ("2 (cache)", p2))],
              "Efeito do cache de consultas na paginação (ponta a ponta).")

        # 3. com e sem filtro (sem cache)
        motor.usar_cache = False
        cve = max(motor.por_cve, key=lambda x: len(motor.por_cve[x]))
        filtros = [("sem filtro", {}), ("site=www.exploit-db.com", {"site": "www.exploit-db.com"}),
                   ("site=github.com", {"site": "github.com"}), (f"cve={cve}", {"cve": cve})]
        linhas_f, res_f = [], {}
        for nome, extra in filtros:
            v, tot = [], []
            for c in consultas:
                _, js, ms = get("/api/busca", q=c["consulta"], **extra)
                v.append(ms)
                tot.append(js["total"])
            res_f[nome] = resumo(v)
            linhas_f.append([nome, round(statistics.mean(tot))]
                            + [f1(res_f[nome][x]) for x in ("media", "mediana", "p95", "max")])
        grava(a.saida, "filtro", ["filtro", "total médio", "média ms", "mediana ms", "p95 ms",
                                  "máx. ms"], linhas_f,
              "Latência com e sem filtro (ponta a ponta, sem cache). O filtro restringe os "
              "candidatos antes do top-k; o ranqueamento é o mesmo.")

        # 4. vazão com 1, 4 e 8 clientes (sem cache)
        linhas_v, res_v = [], {}
        for n in (1, 4, 8):
            lat, erros = [], []
            lock = threading.Lock()

            def cliente(i):
                for j in range(len(consultas)):
                    c = consultas[(i * 5 + j) % len(consultas)]
                    st, _, ms = get("/api/busca", q=c["consulta"])
                    with lock:
                        lat.append(ms)
                        if st != 200:
                            erros.append(st)

            t = time.perf_counter()
            ts = [threading.Thread(target=cliente, args=(i,)) for i in range(n)]
            for x in ts:
                x.start()
            for x in ts:
                x.join()
            dur = time.perf_counter() - t
            r = resumo(lat)
            res_v[n] = {"requisicoes": len(lat), "segundos": dur, "req_s": len(lat) / dur,
                        **r, "erros": len(erros)}
            linhas_v.append([n, len(lat), f"{dur:.1f}", f"{len(lat) / dur:.1f}", f1(r["mediana"]),
                             f1(r["p95"]), f1(r["max"]), len(erros)])
        grava(a.saida, "vazao", ["clientes", "requisições", "segundos", "req/s", "mediana ms",
                                 "p95 ms", "máx. ms", "erros"], linhas_v,
              "Vazão com clientes simultâneos (cada cliente faz as 20 consultas, sem cache). "
              "O lock serializa o ranqueamento: mais clientes aumentam a latência, não a vazão.")

        resumo_json = {
            "indice": a.indice, "consultas": len(consultas), "repeticoes": a.reps,
            "carga_s": round(srv.carga_s, 2), "memoria_apos_carga_mb": mem_carga,
            "memoria_pico_mb": pico_memoria_mb(),
            "latencia_ms": res_lat, "paginacao_ms": {"pagina1": resumo(p1), "pagina2": resumo(p2)},
            "filtro_ms": res_f, "vazao": res_v,
            "meta_p95_ms": META_P95_MS,
            "meta_atingida": res_lat["cliente"]["p95"] < META_P95_MS,
            "tempo_total_s": round(time.perf_counter() - t_inicio, 1),
        }
    with open(os.path.join(a.saida, "resumo.json"), "w", encoding="utf-8") as f:
        json.dump(resumo_json, f, ensure_ascii=False, indent=2)
    r = res_lat["cliente"]
    print(f"Ponta a ponta: média {r['media']:.1f} ms, mediana {r['mediana']:.1f}, p95 "
          f"{r['p95']:.1f}, máx. {r['max']:.1f} (meta p95 < {META_P95_MS}: "
          f"{'OK' if resumo_json['meta_atingida'] else 'NÃO'})")
    for k in ("ranqueamento", "trechos", "resto"):
        print(f"  {k}: média {res_lat[k]['media']:.1f} ms, p95 {res_lat[k]['p95']:.1f}")
    print(f"Página 2 (cache): mediana {resumo(p2)['mediana']:.1f} ms × página 1 "
          f"{resumo(p1)['mediana']:.1f} ms")
    print("Vazão: " + "; ".join(f"{n} cliente(s) {v['req_s']:.1f} req/s (p95 {v['p95']:.0f} ms)"
                                for n, v in res_v.items()))
    print(f"Memória: {mem_carga or 0:.0f} MB após a carga, pico {resumo_json['memoria_pico_mb'] or 0:.0f} MB")
    print(f"Gravado em {a.saida}{os.sep} ({resumo_json['tempo_total_s']} s)")


if __name__ == "__main__":
    main()
