# textos.py - leitura do armazenamento de textos (gerado por preparar_textos.py)
#
# Arquivos em indice/:
#   textos.bin       um registro por documento, na ordem dos ids: JSON compacto
#                    (titulo, descricao, palavras_chave, texto, codigo, cves,
#                    cwes) comprimido com zlib
#   textos_idx.bin   N registros struct '<QI' (deslocamento, tamanho) -> acesso
#                    direto pelo id
#   metadados.tsv    id, CVEs e CWEs (separados por vírgula); carregado inteiro
#                    para os filtros
#   textos.json      parâmetros, tamanhos e tempos da preparação
#
# Textos.campos(id) devolve o dicionário de um documento, com cache LRU. A
# leitura usa seek num arquivo compartilhado: não é segura entre threads (o
# servidor protege com um lock).
import functools
import json
import os
import struct
import zlib

INDICE_FMT = struct.Struct("<QI")
CAMPOS = ("titulo", "descricao", "palavras_chave", "texto", "codigo", "cves", "cwes")


class Textos:
    def __init__(self, pasta="indice", cache=256):
        self.pasta = pasta
        with open(os.path.join(pasta, "textos_idx.bin"), "rb") as f:
            self.posicoes = list(INDICE_FMT.iter_unpack(f.read()))
        self._arq = open(os.path.join(pasta, "textos.bin"), "rb")
        self.campos = functools.lru_cache(maxsize=cache)(self._le)

    def __len__(self):
        return len(self.posicoes)

    def _le(self, doc):
        if not 0 <= doc < len(self.posicoes):
            raise KeyError(doc)
        offset, tam = self.posicoes[doc]
        self._arq.seek(offset)
        return json.loads(zlib.decompress(self._arq.read(tam)).decode("utf-8"))

    def fecha(self):
        self._arq.close()


def le_metadados(pasta="indice"):
    """(cves, cwes) por documento (listas de listas) e os mapas
    identificador -> {docs}, para os filtros."""
    cves, cwes = [], []
    por_cve, por_cwe = {}, {}
    with open(os.path.join(pasta, "metadados.tsv"), encoding="utf-8") as f:
        next(f)
        for linha in f:
            d, c, w = linha.rstrip("\n").split("\t")
            d = int(d)
            lc = c.split(",") if c else []
            lw = w.split(",") if w else []
            cves.append(lc)
            cwes.append(lw)
            for x in lc:
                por_cve.setdefault(x, set()).add(d)
            for x in lw:
                por_cwe.setdefault(x, set()).add(d)
    return cves, cwes, por_cve, por_cwe
