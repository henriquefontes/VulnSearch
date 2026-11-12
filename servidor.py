# servidor.py - backend da interface Web (API JSON sobre o Ranqueador)
# Uso: python servidor.py [--host 127.0.0.1] [--porta 8000] [--indice indice]
#                         [--cors URL ...] [--web web] [--logs logs]
#   Documentação automática da API: http://127.0.0.1:8000/docs ; contrato em API.md.
#   Na VPS: --host 0.0.0.0 (sem autenticação: limite o acesso pelo firewall).
#
# Rotas: /api/busca, /api/documento/{id}, /api/modelos, /api/sites,
#        /api/estatisticas, /api/saude; / e /static/... servem a pasta web/.
#
# Decisões (PLANO_BACKEND.md, seção 1):
#   - um processo; o índice, as estatísticas e os textos são carregados uma vez;
#   - um lock em volta do Ranqueador e da leitura dos textos (os dois usam seek
#     em arquivos compartilhados);
#   - só JSON; títulos e trechos vão como segmentos {texto, destaque}, sem HTML;
#   - filtros (site, cve, cwe) antes do top-k; facetas por site sem o filtro de
#     site; paginação até 500 resultados;
#   - cache LRU por (consulta, modelo, parâmetros) com os escores positivos:
#     páginas seguintes e mudanças de filtro não refazem o ranqueamento;
#   - registro das consultas em logs/consultas.tsv (sem IP).
import argparse
import collections
import datetime
import inspect
import json
import logging
import math
import os
import re
import sys
import threading
import time
from typing import List, Optional

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

import trechos
from indice import pico_memoria_mb, tamanho_mb
from ranqueamento import B, K1, MODELOS, PESOS_BM25F, Ranqueador, top_k
from textos import Textos, le_metadados

MAX_Q = 200
MAX_PALAVRAS = 32
MAX_RESULTADOS = 500
MAX_POR_PAGINA = 50
MAX_CODIGO = 20_000
TAM_CACHE = 64
CORS_PADRAO = ["http://localhost:5173", "http://127.0.0.1:5500"]

SITES = {
    "www.exploit-db.com": "Exploit Database",
    "github.com": "GitHub Advisory Database",
    "www.rapid7.com": "Rapid7 Vulnerability Database",
    "cwe.mitre.org": "MITRE CWE",
    "www.drupal.org": "Drupal Security Advisories",
    "developer.joomla.org": "Joomla Security Centre",
}
MODELOS_INFO = [
    {"id": "jaccard", "nome": "Jaccard", "aula": "07",
     "descricao": "Similaridade de conjuntos de termos: |q ∩ d| / |q ∪ d|."},
    {"id": "tfidf", "nome": "TF-IDF", "aula": "07",
     "descricao": "Soma de w_q·w_d com w = (1 + log tf)·log(N/n), sem normalização."},
    {"id": "vetorial", "nome": "Modelo vetorial (cosseno)", "aula": "08",
     "descricao": "Cosseno entre os vetores TF-IDF da consulta e do documento."},
    {"id": "bm1", "nome": "BM1", "aula": "09", "descricao": "Só o IDF dos termos em comum."},
    {"id": "bm15", "nome": "BM15", "aula": "09",
     "descricao": "TF saturado por K1, sem normalização pelo tamanho."},
    {"id": "bm11", "nome": "BM11", "aula": "09",
     "descricao": "TF saturado e normalizado pelo tamanho do documento."},
    {"id": "bm25", "nome": "BM25", "aula": "09",
     "descricao": "Normalização parcial do tamanho, controlada por b."},
    {"id": "bm25f", "nome": "BM25F", "aula": "09",
     "descricao": "BM25 com campos: título, corpo e código, com pesos por campo. Padrão."},
]
PARAMETROS = ("k1", "b", "peso_titulo", "peso_codigo")
PADROES = {"k1": K1, "b": B, "peso_titulo": PESOS_BM25F["titulo"],
           "peso_codigo": PESOS_BM25F["codigo"]}
RE_CVE = re.compile(r"^CVE-\d{4}-\d{4,7}$")
RE_CWE = re.compile(r"^CWE-\d{1,4}$")

log = logging.getLogger("vulnsearch")

ARQUIVOS = [
    ("estatisticas.json", "python indexar.py"), ("vocabulario.tsv", "python indexar.py"),
    ("ocorrencias.bin", "python indexar.py"), ("documentos.tsv", "python indexar.py"),
    ("colecao.json", "python preparar_ranking.py"),
    ("textos.bin", "python preparar_textos.py"), ("textos_idx.bin", "python preparar_textos.py"),
    ("metadados.tsv", "python preparar_textos.py"),
]


class ErroConsulta(Exception):
    """Erro de parâmetro: vira status 400 com a mensagem em português."""


def parametros_do_modelo(modelo):
    """Quais dos parâmetros da API o modelo usa."""
    aceitos = inspect.signature(getattr(Ranqueador, modelo)).parameters
    usados = [p for p in PARAMETROS if p in aceitos]
    if modelo == "bm25f":
        usados.insert(1, "b")  # b vale para os três campos
    return usados


def para_ranqueador(modelo, params):
    """Parâmetros da API -> argumentos do método do modelo."""
    saida = dict(params)
    if modelo == "bm25f" and "b" in saida:
        b = saida.pop("b")
        saida.update(b_titulo=b, b_corpo=b, b_codigo=b)
    return saida


class Motor:
    """Estado do servidor: índice, textos, metadados, cache e registro."""

    def __init__(self, pasta="indice", pasta_logs="logs"):
        t0 = time.perf_counter()
        faltam = [(a, cmd) for a, cmd in ARQUIVOS if not os.path.exists(os.path.join(pasta, a))]
        if faltam or not os.path.exists(os.path.join(pasta, "documentos_ranking.bin")) and \
                not os.path.exists(os.path.join(pasta, "documentos_ranking.tsv")):
            linhas = [f"  {pasta}{os.sep}{a}: gere com '{cmd}'" for a, cmd in faltam]
            if not linhas:
                linhas = [f"  {pasta}{os.sep}documentos_ranking.bin: gere com "
                          "'python preparar_ranking.py'"]
            raise RuntimeError("Arquivos do índice ausentes:\n" + "\n".join(linhas))
        self.pasta = pasta
        self.r = Ranqueador.abre(pasta)
        self.textos = Textos(pasta)
        self.cves, self.cwes, self.por_cve, self.por_cwe = le_metadados(pasta)
        self.N = self.r.N
        self.sites = [d["site"] for d in self.r.ind.documentos]
        self.por_site = {}
        for d, s in enumerate(self.sites):
            self.por_site.setdefault(s, set()).add(d)
        with open(os.path.join(pasta, "textos.json"), encoding="utf-8") as f:
            self.info_textos = json.load(f) if f else {}
        self.lock = threading.Lock()
        self.cache = collections.OrderedDict()
        self.usar_cache = True  # medir_api.py desliga para medir o ranqueamento sem cache
        self.pasta_logs = pasta_logs
        self.lock_log = threading.Lock()
        self.carregado_em_s = round(time.perf_counter() - t0, 3)
        self.memoria_mb = pico_memoria_mb()

    # ------------------------------------------------------------- busca
    def _ranqueia(self, q, modelo, params, permitidos, k, explicar):
        """Resultado do ranqueamento, do cache quando possível. Devolve
        (entrada do cache, top [(doc, escore)], detalhes, ms, veio_do_cache)."""
        chave = (q, modelo, tuple(sorted(params.items())))
        t = time.perf_counter()
        with self.lock:
            entrada = self.cache.get(chave) if self.usar_cache else None
            if entrada is not None and not explicar:
                self.cache.move_to_end(chave)
                pos = entrada["positivos"]
                filtrados = pos if permitidos is None else \
                    {d: s for d, s in pos.items() if d in permitidos}
                top = top_k(filtrados, k)
                return entrada, top, {}, (time.perf_counter() - t) * 1000, True
            consulta, prep = self.r.prepara(q)
            res = self.r.ranquear(None, modelo, k, explicar=explicar, prep=(consulta, prep),
                                  permitidos=permitidos, **para_ranqueador(modelo, params))
            entrada = {"consulta": consulta, "positivos": res.positivos, "avisos": res.avisos,
                       "n_candidatos": res.n_candidatos, "recurso": res.recurso,
                       "sem_termos": not consulta.palavras}
            if self.usar_cache:
                self.cache[chave] = entrada
                self.cache.move_to_end(chave)
                while len(self.cache) > TAM_CACHE:
                    self.cache.popitem(last=False)
        return entrada, res.top, res.detalhes, (time.perf_counter() - t) * 1000, False

    def busca(self, q, modelo="bm25f", pagina=1, por_pagina=10, site=None, cve=None, cwe=None,
              params=None, explicar=False):
        t0 = time.perf_counter()
        avisos = []
        q = (q or "").strip()
        if not q:
            raise ErroConsulta("A consulta 'q' está vazia.")
        if len(q) > MAX_Q:
            raise ErroConsulta(f"A consulta 'q' tem {len(q)} caracteres; o máximo é {MAX_Q}.")
        partes = q.split()
        if len(partes) > MAX_PALAVRAS:
            q = " ".join(partes[:MAX_PALAVRAS])
            avisos.append(f"A consulta tem {len(partes)} palavras; só as {MAX_PALAVRAS} "
                          "primeiras foram usadas.")
        if modelo not in MODELOS:
            raise ErroConsulta(f"Modelo desconhecido: '{modelo}'. Válidos: {', '.join(MODELOS)}.")
        usados = parametros_do_modelo(modelo)
        params = {k: v for k, v in (params or {}).items() if v is not None and k in usados}
        efetivos = {k: params.get(k, PADROES[k]) for k in usados}

        # filtros: interseção entre tipos, união dentro de um tipo
        site, cve, cwe = site or [], cve or [], cwe or []
        for s in site:
            if s not in SITES:
                raise ErroConsulta(f"Site desconhecido: '{s}'. Válidos: {', '.join(SITES)}.")
        cve = [c.strip().upper() for c in cve]
        cwe = [c.strip().upper() for c in cwe]
        for c in cve:
            if not RE_CVE.match(c):
                raise ErroConsulta(f"CVE inválido: '{c}'. Formato: CVE-2021-44228.")
        for c in cwe:
            if not RE_CWE.match(c):
                raise ErroConsulta(f"CWE inválido: '{c}'. Formato: CWE-79.")
        sem_site = None  # permitidos por cve/cwe (para as facetas)
        if cve:
            sem_site = set().union(*(self.por_cve.get(c, set()) for c in cve))
        if cwe:
            x = set().union(*(self.por_cwe.get(c, set()) for c in cwe))
            sem_site = x if sem_site is None else sem_site & x
        permitidos = sem_site
        if site:
            x = set().union(*(self.por_site[s] for s in site))
            permitidos = x if permitidos is None else permitidos & x

        inicio = (pagina - 1) * por_pagina
        k = min(pagina * por_pagina, MAX_RESULTADOS)
        if inicio >= MAX_RESULTADOS:
            avisos.append(f"Página além do limite de {MAX_RESULTADOS} resultados.")
        entrada, top, detalhes, ms_rank, do_cache = self._ranqueia(
            q, modelo, params, permitidos, max(k, 1), explicar)
        avisos = entrada["avisos"] + avisos
        if entrada["sem_termos"]:
            avisos.append("A consulta não tem termos indexáveis (só stopwords ou sinais).")

        # total e facetas
        pos = entrada["positivos"]
        if permitidos is None:
            total = len(pos)
        else:
            total = sum(1 for d in pos if d in permitidos)
        facetas = collections.Counter(self.sites[d] for d in pos
                                      if sem_site is None or d in sem_site)
        paginas = math.ceil(min(total, MAX_RESULTADOS) / por_pagina) if total else 0
        if total and inicio < MAX_RESULTADOS and pagina > paginas:
            avisos.append(f"Página {pagina} além da última ({paginas}).")
        fatia = top[inicio:k] if inicio < MAX_RESULTADOS else []

        # trechos
        t1 = time.perf_counter()
        resultados = []
        if fatia:
            dest = trechos.Destaque.de_consulta(entrada["consulta"], self.r.proc.stopwords,
                                                self.r.proc.stemming)
            with self.lock:
                campos = [self.textos.campos(d) for d, _ in fatia]
            for n, ((d, s), c) in enumerate(zip(fatia, campos), inicio + 1):
                doc = self.r.ind.documentos[d]
                g = trechos.gera(c, dest)
                resultados.append({
                    "posicao": n, "id": d, "url": doc["url"], "site": doc["site"],
                    "titulo": g["titulo"] or [{"texto": doc["titulo"] or doc["url"],
                                               "destaque": False}],
                    "escore": round(s, 6), "trecho": g["trecho"],
                    "trecho_codigo": g["trecho_codigo"],
                    "cves": self.cves[d], "cwes": self.cwes[d],
                    "explicacao": detalhes.get(d) if explicar else None,
                })
        ms_trechos = (time.perf_counter() - t1) * 1000
        ms_total = (time.perf_counter() - t0) * 1000
        resposta = {
            "consulta": q, "modelo": modelo, "parametros": efetivos,
            "total": total, "pagina": pagina, "por_pagina": por_pagina, "paginas": paginas,
            "tempo_ms": {"ranqueamento": round(ms_rank, 2), "trechos": round(ms_trechos, 2),
                         "total": round(ms_total, 2)},
            "cache": do_cache,
            "avisos": avisos,
            "filtros": {"site": site, "cve": cve, "cwe": cwe},
            "facetas": {"sites": dict(facetas.most_common())},
            "resultados": resultados,
        }
        self.registra(q, modelo, site, cve, cwe, total, ms_total, pagina)
        return resposta

    # ---------------------------------------------------------- registro
    def registra(self, q, modelo, site, cve, cwe, total, ms, pagina):
        if not self.pasta_logs:
            return
        try:
            os.makedirs(self.pasta_logs, exist_ok=True)
            caminho = os.path.join(self.pasta_logs, "consultas.tsv")
            filtros = ";".join([f"site={s}" for s in site] + [f"cve={c}" for c in cve]
                               + [f"cwe={c}" for c in cwe])
            linha = "\t".join([datetime.datetime.now().isoformat(timespec="seconds"),
                               " ".join(q.split()), modelo, filtros, str(total), f"{ms:.1f}",
                               str(pagina)]) + "\n"
            with self.lock_log:
                novo = not os.path.exists(caminho)
                with open(caminho, "a", encoding="utf-8", newline="\n") as f:
                    if novo:
                        f.write("data\tconsulta\tmodelo\tfiltros\ttotal\tms\tpagina\n")
                    f.write(linha)
        except OSError:
            log.exception("falha ao registrar a consulta")

    # -------------------------------------------------------- documentos
    def documento(self, d):
        if not 0 <= d < self.N:
            return None
        with self.lock:
            c = self.textos.campos(d)
        doc = self.r.ind.documentos[d]
        codigo = c.get("codigo") or ""
        return {"id": d, "url": doc["url"], "site": doc["site"],
                "nome_site": SITES.get(doc["site"], doc["site"]),
                "titulo": c.get("titulo") or doc["titulo"], "descricao": c.get("descricao", ""),
                "palavras_chave": c.get("palavras_chave", ""), "texto": c.get("texto", ""),
                "codigo": codigo[:MAX_CODIGO], "codigo_truncado": len(codigo) > MAX_CODIGO,
                "tamanho_codigo": len(codigo), "cves": self.cves[d], "cwes": self.cwes[d],
                "n_termos_texto": doc["n_texto"], "n_termos_codigo": doc["n_codigo"]}

    def estatisticas(self):
        e = self.r.ind.estatisticas
        c = e["contagens"]
        col = self.r.col.meta
        caminho_oc = os.path.join(self.pasta, "ocorrencias.bin")
        extras = {nome: tamanho_mb(os.path.join(self.pasta, nome))
                  for nome in ("documentos_ranking.bin", "colecao.json", "textos.bin",
                               "textos_idx.bin", "metadados.tsv")}
        return {
            "documentos": self.N,
            "vocabulario": {"total": c["vocabulario"], "texto": c["vocabulario_texto"],
                            "codigo": c["vocabulario_codigo"]},
            "postings": c["postings"], "ocorrencias": c["ocorrencias"],
            "indice_mb": {**{k: round(v, 2) for k, v in e["tamanhos_mb"].items()},
                          **{k: round(v, 2) for k, v in extras.items()}},
            "data_indexacao": datetime.datetime.fromtimestamp(
                os.path.getmtime(caminho_oc)).isoformat(timespec="seconds"),
            "tempo_indexacao_s": e["tempos_s"].get("total"),
            "medias_tamanho": {k: round(v, 2) for k, v in col["medias"].items()},
            "docs_com_campo": col["docs_com_campo"],
            "textos": {"razao_compressao": round(self.info_textos.get("razao_compressao", 0), 2),
                       "docs_com_cve": self.info_textos.get("identificadores", {})
                       .get("docs_com_cve")},
        }


# ------------------------------------------------------------------ app
def mensagem_validacao(erros):
    partes = []
    for e in erros:
        nome = str(e.get("loc", ["?"])[-1])
        tipo = e.get("type", "")
        ctx = e.get("ctx") or {}
        if tipo == "missing":
            partes.append(f"O parâmetro '{nome}' é obrigatório.")
        elif tipo in ("int_parsing", "int_from_float"):
            partes.append(f"O parâmetro '{nome}' deve ser um número inteiro.")
        elif tipo == "float_parsing":
            partes.append(f"O parâmetro '{nome}' deve ser um número.")
        elif tipo == "bool_parsing":
            partes.append(f"O parâmetro '{nome}' deve ser true ou false.")
        elif tipo == "greater_than_equal":
            partes.append(f"O parâmetro '{nome}' deve ser ≥ {ctx.get('ge')}.")
        elif tipo == "greater_than":
            partes.append(f"O parâmetro '{nome}' deve ser > {ctx.get('gt')}.")
        elif tipo == "less_than_equal":
            partes.append(f"O parâmetro '{nome}' deve ser ≤ {ctx.get('le')}.")
        else:
            partes.append(f"Parâmetro '{nome}' inválido.")
    return " ".join(partes) or "Parâmetros inválidos."


def cria_app(pasta="indice", cors=None, pasta_web="web", pasta_logs="logs"):
    motor = Motor(pasta, pasta_logs)
    app = FastAPI(title="VulnSearch API",
                  description="Busca vertical sobre vulnerabilidades de software e hardware "
                              "(PUC Minas). Contrato completo em API.md.",
                  version="1.0")
    app.state.motor = motor
    app.add_middleware(CORSMiddleware, allow_origins=CORS_PADRAO if cors is None else cors,
                       allow_methods=["GET"], allow_headers=["*"])

    @app.exception_handler(RequestValidationError)
    def _validacao(request: Request, exc: RequestValidationError):
        return JSONResponse({"erro": mensagem_validacao(exc.errors())}, status_code=400)

    @app.exception_handler(StarletteHTTPException)
    def _http(request: Request, exc: StarletteHTTPException):
        msg = "Rota não encontrada." if exc.status_code == 404 else str(exc.detail)
        return JSONResponse({"erro": msg}, status_code=exc.status_code)

    @app.exception_handler(ErroConsulta)
    def _consulta(request: Request, exc: ErroConsulta):
        return JSONResponse({"erro": str(exc)}, status_code=400)

    @app.exception_handler(Exception)
    def _interno(request: Request, exc: Exception):
        log.exception("erro inesperado em %s", request.url.path)
        return JSONResponse({"erro": "Erro interno do servidor."}, status_code=500)

    @app.get("/api/busca", summary="Busca ranqueada")
    def busca(q: str = Query(..., description="Consulta (1 a 200 caracteres). Aceita "
                                               "\"frase\", -termo e codigo:termo."),
              modelo: str = Query("bm25f", description="Modelo: " + ", ".join(MODELOS)),
              pagina: int = Query(1, ge=1), por_pagina: int = Query(10, ge=1, le=MAX_POR_PAGINA),
              site: Optional[List[str]] = Query(None, description="Pode repetir"),
              cve: Optional[List[str]] = Query(None, description="Ex.: CVE-2021-44228"),
              cwe: Optional[List[str]] = Query(None, description="Ex.: CWE-79"),
              k1: Optional[float] = Query(None, gt=0, le=10),
              b: Optional[float] = Query(None, ge=0, le=1),
              peso_titulo: Optional[float] = Query(None, ge=0, le=100),
              peso_codigo: Optional[float] = Query(None, ge=0, le=100),
              explicar: bool = Query(False, description="Inclui as parcelas por termo")):
        return motor.busca(q, modelo, pagina, por_pagina, site, cve, cwe,
                           {"k1": k1, "b": b, "peso_titulo": peso_titulo,
                            "peso_codigo": peso_codigo}, explicar)

    @app.get("/api/documento/{doc_id}", summary="Documento completo")
    def documento(doc_id: int):
        d = motor.documento(doc_id)
        if d is None:
            return JSONResponse({"erro": f"O documento {doc_id} não existe."}, status_code=404)
        return d

    @app.get("/api/modelos", summary="Modelos de ranqueamento")
    def modelos():
        return {"padrao": "bm25f", "modelos": [
            {**m, "parametros": {p: PADROES[p] for p in parametros_do_modelo(m["id"])}}
            for m in MODELOS_INFO]}

    @app.get("/api/sites", summary="Sites do corpus")
    def sites():
        return {"sites": [{"id": s, "nome": nome, "documentos": len(motor.por_site.get(s, ()))}
                          for s, nome in SITES.items()]}

    @app.get("/api/estatisticas", summary="Estatísticas do índice")
    def estatisticas():
        return motor.estatisticas()

    @app.get("/api/saude", summary="Situação do servidor")
    def saude():
        return {"ok": True, "documentos": motor.N, "carregado_em_s": motor.carregado_em_s,
                "memoria_mb": round(motor.memoria_mb or 0, 1)}

    if pasta_web and os.path.isdir(pasta_web):
        app.mount("/static", StaticFiles(directory=pasta_web), name="static")

        @app.get("/", include_in_schema=False)
        def raiz():
            for nome in ("index.html", "teste.html"):
                caminho = os.path.join(pasta_web, nome)
                if os.path.exists(caminho):
                    return FileResponse(caminho)
            return JSONResponse({"erro": "A pasta web/ não tem index.html nem teste.html."},
                                status_code=404)
    return app


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Servidor da interface Web do VulnSearch.")
    p.add_argument("--host", default="127.0.0.1",
                   help="endereço (padrão 127.0.0.1; use 0.0.0.0 só na VPS, com firewall)")
    p.add_argument("--porta", type=int, default=8000)
    p.add_argument("--indice", default="indice")
    p.add_argument("--cors", nargs="*", default=None,
                   help=f"origens permitidas (padrão: {' '.join(CORS_PADRAO)})")
    p.add_argument("--web", default="web", help="pasta do frontend (padrão: web)")
    p.add_argument("--logs", default="logs", help="pasta do registro das consultas")
    a = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        app = cria_app(a.indice, a.cors, a.web, a.logs)
    except RuntimeError as e:
        sys.exit(str(e))
    m = app.state.motor
    print(f"Índice carregado: {m.N} documentos em {m.carregado_em_s} s; "
          f"pico de memória {m.memoria_mb or 0:.0f} MB")
    print(f"Interface: http://{a.host}:{a.porta}/   API: http://{a.host}:{a.porta}/docs")
    import uvicorn
    try:
        uvicorn.run(app, host=a.host, port=a.porta, log_level="warning")
    except KeyboardInterrupt:
        pass
    print("Servidor encerrado.")


if __name__ == "__main__":
    main()
