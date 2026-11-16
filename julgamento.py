# julgamento.py - leitura e gravação dos julgamentos de relevância (ferramenta /julgar)
#
# Arquivos (gerados pelo pool.py; uma linha por documento do pool):
#   julgamentos/pool_qXX.tsv
#       url, titulo, site, relevante, observacao, doc, modelos, melhor_pos [, avaliador]
#       É o julgamento PRINCIPAL, o único que o avaliar.py --juntar lê. A coluna
#       avaliador é acrescentada na primeira gravação; as demais não mudam.
#   julgamentos/segunda_avaliacao/pool_qXX.tsv
#       url, titulo, site, relevante, observacao, avaliador
#       Julgamentos de um documento que OUTRA pessoa já julgou no principal (para medir
#       a concordância entre avaliadores). Uma linha por (url, avaliador).
#
# Regras:
#   - relevante: "0" (não serve), "1" (relacionado), "2" (trata do assunto pedido) ou ""
#     (desfaz o julgamento da própria pessoa);
#   - no principal, a pessoa grava se a linha está sem julgamento ou se foi ela mesma
#     que julgou; se outra pessoa já julgou, o julgamento vai para a segunda avaliação;
#   - a ordem dos documentos é aleatória, fixa por (consulta, avaliador), e a página
#     não recebe modelo, posição nem score;
#   - gravação atômica (arquivo temporário + os.replace) e com lock, para não perder
#     linhas com duas pessoas julgando ao mesmo tempo.
import csv
import hashlib
import os
import random
import re
import tempfile
import threading

RE_ID = re.compile(r"^q\d{2}$")
VALORES = ("0", "1", "2")
PASTA_SEGUNDA = "segunda_avaliacao"
COLUNAS_SEGUNDA = ["url", "titulo", "site", "relevante", "observacao", "avaliador"]
MAX_AVALIADOR = 60
MAX_OBSERVACAO = 500
CRITERIO = [
    ("2", "Trata do assunto pedido",
     "O documento é sobre a vulnerabilidade, o identificador (CVE, CWE, aviso) ou o tema "
     "da consulta: um exploit, aviso ou definição que responde ao que foi pedido."),
    ("1", "Relacionado",
     "Tem relação com a consulta, mas não é o que foi pedido: outra versão ou produto "
     "parecido, menção de passagem, assunto vizinho."),
    ("0", "Não serve",
     "Não ajuda quem fez a consulta: assunto diferente, casamento só de palavras soltas."),
]


class ErroJulgamento(ValueError):
    """Erro de validação (vira 400 na API); 'nao_existe' vira 404."""

    def __init__(self, msg, nao_existe=False):
        super().__init__(msg)
        self.nao_existe = nao_existe


def limpa(texto, maximo):
    """Sem tabulação nem quebra de linha (o arquivo é TSV), cortado em 'maximo'."""
    return re.sub(r"[\t\r\n]+", " ", texto or "").strip()[:maximo]


def mesmo(a, b):
    return (a or "").strip().casefold() == (b or "").strip().casefold()


def le_tsv(caminho):
    if not os.path.exists(caminho):
        return [], []
    with open(caminho, encoding="utf-8", newline="") as f:
        r = csv.DictReader(f, delimiter="\t")
        linhas = list(r)
        return list(r.fieldnames or []), linhas


def grava_tsv(caminho, colunas, linhas):
    pasta = os.path.dirname(caminho) or "."
    os.makedirs(pasta, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".julg_", suffix=".tsv", dir=pasta)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, colunas, delimiter="\t", lineterminator="\n",
                               extrasaction="ignore")
            w.writeheader()
            w.writerows(linhas)
        os.replace(tmp, caminho)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def le_consultas(caminho):
    with open(caminho, encoding="utf-8", newline="") as f:
        return {c["id"]: c for c in csv.DictReader(f, delimiter="\t")}


class Julgamentos:
    def __init__(self, pasta="julgamentos", consultas="consultas.tsv"):
        self.pasta = pasta
        self.lock = threading.Lock()
        todas = le_consultas(consultas) if os.path.exists(consultas) else {}
        self.consultas = {cid: c for cid, c in todas.items()
                          if os.path.exists(self.caminho(cid))}

    # ------------------------------------------------------------ arquivos
    def caminho(self, cid, segunda=False):
        if not RE_ID.match(cid or ""):
            raise ErroJulgamento(f"Consulta inválida: {cid!r}.", nao_existe=True)
        base = os.path.join(self.pasta, PASTA_SEGUNDA) if segunda else self.pasta
        return os.path.join(base, f"pool_{cid}.tsv")

    def _confere(self, cid):
        if cid not in self.consultas:
            raise ErroJulgamento(f"A consulta {cid!r} não tem pool para julgar.", nao_existe=True)

    @staticmethod
    def _avaliador(avaliador):
        a = limpa(avaliador, MAX_AVALIADOR)
        if not a:
            raise ErroJulgamento("Informe o nome do avaliador.")
        return a

    # --------------------------------------------------------------- leitura
    @staticmethod
    def ordem(cid, avaliador, urls):
        """Ordem aleatória, mas fixa para a mesma (consulta, avaliador)."""
        semente = hashlib.sha256(f"{cid}|{(avaliador or '').strip().casefold()}".encode()).hexdigest()
        urls = sorted(urls)
        random.Random(semente).shuffle(urls)
        return urls

    def resumo(self, avaliador=""):
        consultas, total, julgados = [], 0, 0
        for cid in sorted(self.consultas):
            with self.lock:  # no Windows, os.replace falha com o arquivo aberto por um leitor
                _, linhas = le_tsv(self.caminho(cid))
                _, seg = le_tsv(self.caminho(cid, segunda=True))
            n = len(linhas)
            j = sum(1 for l in linhas if (l.get("relevante") or "").strip() in VALORES)
            meus = sum(1 for l in linhas if (l.get("relevante") or "").strip() in VALORES
                       and mesmo(l.get("avaliador"), avaliador)) if avaliador else 0
            meus += sum(1 for l in seg if mesmo(l.get("avaliador"), avaliador)) if avaliador else 0
            consultas.append({"id": cid, "consulta": self.consultas[cid]["consulta"],
                              "tipo": self.consultas[cid].get("tipo", ""), "total": n,
                              "julgados": j, "meus": meus,
                              "segunda_avaliacao": len({l["url"] for l in seg})})
            total += n
            julgados += j
        return {"consultas": consultas, "total": total, "julgados": julgados,
                "criterio": [{"valor": v, "nome": n, "descricao": d} for v, n, d in CRITERIO]}

    def documentos(self, cid, avaliador):
        """Documentos do pool na ordem do avaliador, com o julgamento DELE (o de outras
        pessoas não é mostrado). Sem modelo, posição nem score."""
        self._confere(cid)
        avaliador = self._avaliador(avaliador)
        with self.lock:
            _, linhas = le_tsv(self.caminho(cid))
            _, seg = le_tsv(self.caminho(cid, segunda=True))
        meus_seg = {l["url"]: l for l in seg if mesmo(l.get("avaliador"), avaliador)}
        por_url = {l["url"]: l for l in linhas}
        saida = []
        for url in self.ordem(cid, avaliador, por_url):
            l = por_url[url]
            julgado = (l.get("relevante") or "").strip() in VALORES
            meu = julgado and mesmo(l.get("avaliador"), avaliador)
            outro = julgado and not meu
            fonte = l if meu else meus_seg.get(url, {})
            saida.append({"url": url, "titulo": l.get("titulo", ""), "site": l.get("site", ""),
                          "doc": l.get("doc", ""),
                          "relevante": (fonte.get("relevante") or "").strip(),
                          "observacao": fonte.get("observacao") or "",
                          "julgado_por_outra_pessoa": outro})
        return {"id": cid, "consulta": self.consultas[cid]["consulta"], "documentos": saida}

    # -------------------------------------------------------------- gravação
    def julga(self, cid, url, relevante, observacao, avaliador):
        """Grava um julgamento; devolve 'principal' ou 'segunda_avaliacao'."""
        self._confere(cid)
        avaliador = self._avaliador(avaliador)
        relevante = (relevante or "").strip()
        if relevante not in VALORES + ("",):
            raise ErroJulgamento("O julgamento deve ser 0, 1, 2 (ou vazio para desfazer).")
        observacao = limpa(observacao, MAX_OBSERVACAO)
        with self.lock:
            colunas, linhas = le_tsv(self.caminho(cid))
            linha = next((l for l in linhas if l["url"] == url), None)
            if linha is None:
                raise ErroJulgamento("Documento fora do pool desta consulta.", nao_existe=True)
            julgado = (linha.get("relevante") or "").strip() in VALORES
            if not julgado or mesmo(linha.get("avaliador"), avaliador):
                if "avaliador" not in colunas:
                    colunas = colunas + ["avaliador"]
                linha["relevante"] = relevante
                linha["observacao"] = observacao if relevante else ""
                linha["avaliador"] = avaliador if relevante else ""
                grava_tsv(self.caminho(cid), colunas, linhas)
                return "principal"
            # outra pessoa já julgou: segunda avaliação (concordância)
            caminho = self.caminho(cid, segunda=True)
            _, seg = le_tsv(caminho)
            seg = [l for l in seg if not (l["url"] == url and mesmo(l.get("avaliador"), avaliador))]
            if relevante:
                seg.append({"url": url, "titulo": linha.get("titulo", ""), "site": linha.get("site", ""),
                            "relevante": relevante, "observacao": observacao,
                            "avaliador": avaliador})
            grava_tsv(caminho, COLUNAS_SEGUNDA, seg)
            return "segunda_avaliacao"
