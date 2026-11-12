# cliente_api.py - utilidades comuns de testar_api.py e medir_api.py:
# sobe o servidor numa thread (porta livre) e faz requisições com urllib.
import json
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request


def porta_livre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class ServidorTeste:
    """with ServidorTeste("indice") as srv: srv.get("/api/busca", q="...")"""

    def __init__(self, indice="indice", pasta_logs=None, pasta_web="web"):
        import uvicorn
        from servidor import cria_app
        t = time.perf_counter()
        self.app = cria_app(indice, pasta_web=pasta_web, pasta_logs=pasta_logs)
        self.carga_s = time.perf_counter() - t
        self.porta = porta_livre()
        self.base = f"http://127.0.0.1:{self.porta}"
        cfg = uvicorn.Config(self.app, host="127.0.0.1", port=self.porta, log_level="error")
        self.servidor = uvicorn.Server(cfg)
        self.thread = threading.Thread(target=self.servidor.run, daemon=True)

    def __enter__(self):
        self.thread.start()
        for _ in range(200):
            if self.servidor.started:
                break
            time.sleep(0.05)
        return self

    def __exit__(self, *exc):
        self.servidor.should_exit = True
        self.thread.join(timeout=10)

    def get(self, caminho, **params):
        return requisita(self.base, caminho, **params)


def requisita(base, caminho, **params):
    """(status, json, ms). Listas viram parâmetros repetidos (site=a&site=b)."""
    pares = []
    for k, v in params.items():
        for x in (v if isinstance(v, (list, tuple)) else [v]):
            pares.append((k, str(x).lower() if isinstance(x, bool) else x))
    url = base + caminho + ("?" + urllib.parse.urlencode(pares) if pares else "")
    t = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            corpo, status = r.read(), r.status
    except urllib.error.HTTPError as e:
        corpo, status = e.read(), e.code
    ms = (time.perf_counter() - t) * 1000
    return status, json.loads(corpo.decode("utf-8")), ms
