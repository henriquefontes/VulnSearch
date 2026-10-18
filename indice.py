# indice.py - formato do índice invertido: codificação, leitura e utilidades
#
# Arquivos de um índice (diretório, padrão "indice/"):
#   vocabulario.tsv   termo, df, cf, offset e tamanho (bytes) da lista de
#                     ocorrências; carregado inteiro na memória na busca
#   ocorrencias.bin   listas de ocorrências, uma após a outra, na ordem do
#                     vocabulário; cada lista é <tᵢ; nᵢ; [tf(i,j); dⱼ; posições]>
#                     (tᵢ e nᵢ = df ficam no vocabulário)
#   documentos.tsv    id, URL, site, nº de termos do texto, nº de termos do
#                     código e título de cada página
#   trechos.tsv       (só na granularidade por trecho) id do trecho -> página
#   estatisticas.json parâmetros da construção, tempos e tamanhos
#   heaps.csv         (nº de tokens, tamanho do vocabulário) durante a leitura
#
# Cada lista de ocorrências é uma sequência de inteiros:
#   com posições: doc, tf, pos₁, pos₂, ..., pos_tf, doc, tf, ...
#   sem posições: doc, tf, doc, tf, ...
# Com compressão, doc e pos são gravados como diferenças (gaps) em relação ao
# anterior da mesma lista, em variable byte; sem compressão, como inteiros
# absolutos de 4 bytes (little-endian).
#
# Termos do campo código são gravados com o prefixo "c:" (c:strcpy), o que
# permite buscar só no código e medir o índice com e sem esse campo.
import json
import os
import struct
import sys

PREFIXO_CODIGO = "c:"


# ---------------------------------------------------------------- codificação
def vb_codifica(numeros, saida):
    """Variable byte (7 bits por byte; o bit mais alto indica que o número
    continua no próximo byte). Acrescenta os bytes em 'saida' (bytearray)."""
    if max(numeros) < 128:  # caso mais comum (gaps pequenos): 1 byte cada
        saida += bytes(numeros)
        return
    for n in numeros:
        while n >= 128:
            saida.append((n & 127) | 128)
            n >>= 7
        saida.append(n)


def vb_decodifica(dados):
    numeros, n, desloc = [], 0, 0
    for b in dados:
        if b & 128:
            n |= (b & 127) << desloc
            desloc += 7
        else:
            numeros.append(n | (b << desloc))
            n, desloc = 0, 0
    return numeros


def vb_tamanho_primeiro(dados):
    """Nº de bytes do primeiro número de uma sequência em variable byte."""
    i = 0
    while dados[i] & 128:
        i += 1
    return i + 1


def fixo_codifica(numeros, saida):
    saida += struct.pack(f"<{len(numeros)}I", *numeros)


def fixo_decodifica(dados):
    return list(struct.unpack(f"<{len(dados) // 4}I", dados))


# ------------------------------------------------------------------- leitura
class Indice:
    """Leitor de um índice gravado por indexar.py."""

    def __init__(self, pasta="indice"):
        self.pasta = pasta
        with open(os.path.join(pasta, "estatisticas.json"), encoding="utf-8") as f:
            self.estatisticas = json.load(f)
        p = self.estatisticas["parametros"]
        self.comprimido = p["compressao"]
        self.posicoes = p["posicoes"]
        self.vocabulario = {}
        with open(os.path.join(pasta, "vocabulario.tsv"), encoding="utf-8") as f:
            next(f)  # cabeçalho
            for linha in f:
                termo, df, cf, offset, tam = linha.rstrip("\n").split("\t")
                self.vocabulario[termo] = (int(df), int(cf), int(offset), int(tam))
        self.documentos = []
        with open(os.path.join(pasta, "documentos.tsv"), encoding="utf-8") as f:
            next(f)
            for linha in f:
                _id, url, site, n_texto, n_codigo, titulo = linha.rstrip("\n").split("\t")
                self.documentos.append({"url": url, "site": site, "titulo": titulo,
                                        "n_texto": int(n_texto), "n_codigo": int(n_codigo)})
        self.trechos = None  # id do trecho -> id da página
        caminho = os.path.join(pasta, "trechos.tsv")
        if os.path.exists(caminho):
            with open(caminho, encoding="utf-8") as f:
                next(f)
                self.trechos = [int(l.split("\t")[1]) for l in f]
        self._arq = open(os.path.join(pasta, "ocorrencias.bin"), "rb")

    def pagina(self, unidade):
        """Página (documento) de uma unidade indexada (ela mesma ou um trecho)."""
        return self.trechos[unidade] if self.trechos is not None else unidade

    def lista(self, termo):
        """Lista de ocorrências: [(doc, tf, [posições] ou None)], doc crescente."""
        entrada = self.vocabulario.get(termo)
        if not entrada:
            return []
        _df, _cf, offset, tam = entrada
        self._arq.seek(offset)
        dados = self._arq.read(tam)
        nums = vb_decodifica(dados) if self.comprimido else fixo_decodifica(dados)
        saida, i, doc = [], 0, 0
        while i < len(nums):
            doc = doc + nums[i] if self.comprimido else nums[i]
            tf = nums[i + 1]
            i += 2
            pos = None
            if self.posicoes:
                pos = nums[i:i + tf]
                i += tf
                if self.comprimido:
                    for k in range(1, tf):
                        pos[k] += pos[k - 1]
            saida.append((doc, tf, pos))
        return saida

    def fecha(self):
        self._arq.close()


# --------------------------------------------------------------- utilidades
def pico_memoria_mb():
    """Pico de memória (working set / RSS máximo) do processo atual, em MB,
    sem depender do psutil. Devolve None se o sistema não informar."""
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes

            class PMC(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t),
                            ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t),
                            ("PeakPagefileUsage", ctypes.c_size_t)]
            pmc = PMC()
            pmc.cb = ctypes.sizeof(PMC)
            kernel32 = ctypes.WinDLL("kernel32")
            kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            psapi = ctypes.WinDLL("psapi")
            psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(PMC),
                                                   wintypes.DWORD]
            psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
            if not psapi.GetProcessMemoryInfo(kernel32.GetCurrentProcess(),
                                              ctypes.byref(pmc), pmc.cb):
                return None
            return pmc.PeakWorkingSetSize / 2**20
        import resource
        maximo = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return maximo / 2**20 if sys.platform == "darwin" else maximo / 1024
    except Exception:
        return None


def tamanho_mb(caminho):
    return os.path.getsize(caminho) / 2**20 if os.path.exists(caminho) else 0.0
