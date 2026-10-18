# indexar.py - construção do índice invertido por ordenação externa
# Uso: python indexar.py [corpus.jsonl.gz] [opções]
#   python indexar.py                          índice principal em indice/
#   python indexar.py --limite 2000 --passo 30 teste rápido (1 página a cada 30)
#   python indexar.py --salvar-campos campos.jsonl.gz
#                       grava também os campos extraídos; depois, outras
#                       variações podem ler campos.jsonl.gz no lugar do corpus
#                       e pular a extração do HTML
#   python indexar.py --help                   todas as opções
#
# Etapas (os tempos de cada uma vão para estatisticas.json):
#   1. leitura do corpus em streaming (gzip + JSON, linha a linha)
#   2. extração dos campos do HTML (extrair.py)
#   3. análise léxica (lexico.py)
#   4. inversão em blocos: as ocorrências de cada termo são acumuladas em
#      memória, já codificadas, até o bloco atingir --bloco MB (MAX_TAMANHO);
#      então os termos são ordenados e o bloco é gravado em disco
#   5. intercalação (k-way merge, heapq.merge) dos blocos no arquivo final;
#      os blocos temporários são apagados
# O formato dos arquivos está descrito em indice.py.
import argparse
import gzip
import heapq
import json
import operator
import os
import shutil
import struct
import sys
import time

import lexico
from extrair import extrair, site_da_url
from indice import (PREFIXO_CODIGO, fixo_codifica, pico_memoria_mb, tamanho_mb,
                    vb_codifica, vb_tamanho_primeiro)

# cabeçalho de cada termo num bloco: tamanho do termo, df, cf, primeiro doc,
# último doc, tamanho da lista
CABECALHO = struct.Struct("<IIIIII")
# memória estimada de cada termo novo num bloco, além dos bytes da lista
# (entrada do dicionário, string, lista e bytearray do Python)
CUSTO_TERMO = 200
CAMPOS_TEXTO = ("titulo", "descricao", "palavras_chave", "texto")
ARQUIVOS_INDICE = ("vocabulario.tsv", "ocorrencias.bin", "documentos.tsv", "trechos.tsv",
                   "estatisticas.json", "heaps.csv")
HEAPS_A_CADA = 250  # páginas entre dois pontos da curva de Heaps


def le_registros(caminho, limite, passo, tempos):
    """Lê o corpus (ou o arquivo de campos) linha a linha."""
    lidos, i = 0, 0
    with gzip.open(caminho, "rt", encoding="utf-8") as f:
        while not limite or lidos < limite:
            t = time.perf_counter()  # conta a descompactação e o JSON
            linha = f.readline()
            if not linha:
                break
            i += 1
            if (i - 1) % passo:
                tempos["leitura"] += time.perf_counter() - t
                continue
            reg = json.loads(linha)
            tempos["leitura"] += time.perf_counter() - t
            lidos += 1
            yield reg


def limpa_tsv(s):
    return " ".join(s.split())[:300]


class Construtor:
    """Acumula as ocorrências em blocos e faz a intercalação no final."""

    def __init__(self, args, tempos):
        self.args = args
        self.tempos = tempos
        self.comprimido = not args.sem_compressao
        self.posicoes = not args.sem_posicoes
        self.codifica = vb_codifica if self.comprimido else fixo_codifica
        self.limite_bloco = int(args.bloco * 2**20)
        self.pasta_tmp = os.path.join(args.saida, "tmp_blocos")
        os.makedirs(self.pasta_tmp, exist_ok=True)
        self.bloco, self.bytes_bloco = {}, 0
        self.blocos = []  # caminhos dos blocos gravados
        self.bytes_temp = 0

    def adiciona(self, unidade, termos):
        """termos: {termo: [posições]} de uma unidade (página ou trecho)."""
        bloco, comprimido, posicoes = self.bloco, self.comprimido, self.posicoes
        acrescimo = 0
        for termo, ps in termos.items():
            entrada = bloco.get(termo)
            if entrada is None:
                # [lista codificada, último doc, df, cf, primeiro doc]
                entrada = bloco[termo] = [bytearray(), 0, 0, 0, unidade]
                acrescimo += CUSTO_TERMO + len(termo)
            buf = entrada[0]
            antes = len(buf)
            tf = len(ps)
            if comprimido:
                nums = [unidade - entrada[1], tf]
                if posicoes:
                    nums.append(ps[0])
                    if tf > 1:
                        nums += map(operator.sub, ps[1:], ps[:-1])
            else:
                nums = [unidade, tf] + ps if posicoes else [unidade, tf]
            self.codifica(nums, buf)
            acrescimo += len(buf) - antes
            entrada[1] = unidade
            entrada[2] += 1
            entrada[3] += tf
        self.bytes_bloco += acrescimo
        if self.bytes_bloco >= self.limite_bloco:
            self.grava_bloco()

    def grava_bloco(self):
        if not self.bloco:
            return
        t = time.perf_counter()
        caminho = os.path.join(self.pasta_tmp, f"bloco_{len(self.blocos) + 1:04d}.bin")
        with open(caminho, "wb", buffering=2**20) as f:
            for termo in sorted(self.bloco):
                buf, ultimo, df, cf, primeiro = self.bloco[termo]
                bt = termo.encode("utf-8")
                f.write(CABECALHO.pack(len(bt), df, cf, primeiro, ultimo, len(buf)))
                f.write(bt)
                f.write(buf)
        self.blocos.append(caminho)
        self.bytes_temp += os.path.getsize(caminho)
        self.bloco, self.bytes_bloco = {}, 0
        self.tempos["gravacao_blocos"] += time.perf_counter() - t

    @staticmethod
    def _le_bloco(caminho, ordem):
        with open(caminho, "rb", buffering=2**20) as f:
            while True:
                cab = f.read(CABECALHO.size)
                if not cab:
                    return
                tam_termo, df, cf, primeiro, ultimo, tam = CABECALHO.unpack(cab)
                termo = f.read(tam_termo).decode("utf-8")
                # 'ordem' desempata termos iguais: blocos anteriores têm docs menores
                yield termo, ordem, df, cf, primeiro, ultimo, f.read(tam)

    def intercala(self):
        """k-way merge dos blocos ordenados -> vocabulario.tsv + ocorrencias.bin.
        Como os documentos são lidos em ordem, a lista de um termo é a
        concatenação das suas listas em cada bloco, na ordem dos blocos; com
        compressão, só o primeiro gap de cada parte precisa ser recalculado."""
        self.grava_bloco()
        t = time.perf_counter()
        leitores = [self._le_bloco(c, i) for i, c in enumerate(self.blocos)]
        stats = {"vocabulario": 0, "vocabulario_codigo": 0, "postings": 0, "ocorrencias": 0}
        caminho_voc = os.path.join(self.args.saida, "vocabulario.tsv")
        caminho_oc = os.path.join(self.args.saida, "ocorrencias.bin")
        with open(caminho_voc, "w", encoding="utf-8", newline="\n") as voc, \
                open(caminho_oc, "wb", buffering=2**20) as oc:
            voc.write("termo\tdf\tcf\toffset\tbytes\n")
            offset = 0
            atual, partes, df_t, cf_t, ultimo_t = None, [], 0, 0, 0

            def fecha_termo():
                nonlocal offset
                tam = sum(len(p) for p in partes)
                for p in partes:
                    oc.write(p)
                voc.write(f"{atual}\t{df_t}\t{cf_t}\t{offset}\t{tam}\n")
                offset += tam
                stats["vocabulario"] += 1
                stats["postings"] += df_t
                stats["ocorrencias"] += cf_t
                if atual.startswith(PREFIXO_CODIGO):
                    stats["vocabulario_codigo"] += 1

            for termo, _o, df, cf, primeiro, ultimo, dados in heapq.merge(*leitores):
                if termo != atual:
                    if atual is not None:
                        fecha_termo()
                    atual, partes, df_t, cf_t = termo, [dados], df, cf
                else:
                    if self.comprimido:
                        gap = bytearray()
                        vb_codifica([primeiro - ultimo_t], gap)
                        partes += [gap, memoryview(dados)[vb_tamanho_primeiro(dados):]]
                    else:
                        partes.append(dados)
                    df_t += df
                    cf_t += cf
                ultimo_t = ultimo
            if atual is not None:
                fecha_termo()
        self.tempos["merge"] += time.perf_counter() - t
        shutil.rmtree(self.pasta_tmp, ignore_errors=True)
        return stats


def agrupa(termos, prefixo=""):
    d = {}
    for t, p in termos:
        lst = d.get(prefixo + t)
        if lst is None:
            d[prefixo + t] = [p]
        else:
            lst.append(p)
    return d


def indexar(args):
    inicio = time.perf_counter()
    tempos = dict.fromkeys(["leitura", "extracao", "gravacao_campos", "lexico",
                            "inversao", "gravacao_blocos", "merge"], 0.0)
    os.makedirs(args.saida, exist_ok=True)
    for nome in ARQUIVOS_INDICE:  # restos de um índice anterior na mesma pasta
        caminho = os.path.join(args.saida, nome)
        if os.path.exists(caminho):
            os.remove(caminho)
    stopwords = frozenset() if args.sem_stopwords else lexico.STOPWORDS
    stemming = not args.sem_stemming
    construtor = Construtor(args, tempos)
    por_trecho = args.granularidade == "trecho"

    c = dict.fromkeys(["paginas", "unidades", "tokens_texto", "termos_texto",
                       "termos_codigo", "bytes_html", "bytes_texto",
                       "bytes_codigo"], 0)
    voc_texto, voc_total = set(), set()
    heaps = [("paginas", "tokens_texto", "termos_texto", "vocabulario_texto",
              "termos_total", "vocabulario_total")]

    docs = open(os.path.join(args.saida, "documentos.tsv"), "w", encoding="utf-8", newline="\n")
    docs.write("id\turl\tsite\tn_termos_texto\tn_termos_codigo\ttitulo\n")
    trechos = None
    if por_trecho:
        trechos = open(os.path.join(args.saida, "trechos.tsv"), "w", encoding="utf-8", newline="\n")
        trechos.write("id\tpagina\tn_termos\n")
    cache = None
    if args.salvar_campos:
        cache = gzip.open(args.salvar_campos, "wt", encoding="utf-8", compresslevel=3)

    for reg in le_registros(args.entrada, args.limite, args.passo, tempos):
        pagina = c["paginas"]
        url = reg["url"]
        # 2. extração (ou campos prontos, se a entrada é um arquivo de campos)
        t = time.perf_counter()
        if "html" in reg:
            bytes_html = len(reg["html"].encode("utf-8"))
            campos = extrair(url, reg["html"])
        else:
            campos, bytes_html = reg, reg.get("bytes_html", 0)
        t2 = time.perf_counter()
        tempos["extracao"] += t2 - t
        if cache:
            cache.write(json.dumps({"url": url, "bytes_html": bytes_html,
                                    **{k: campos[k] for k in CAMPOS_TEXTO + ("codigo",)}},
                                   ensure_ascii=False) + "\n")
            t2b = time.perf_counter()
            tempos["gravacao_campos"] += t2b - t2
            t2 = t2b

        # 3. análise léxica
        textos = [campos[k] for k in CAMPOS_TEXTO]
        termos, n_tokens = lexico.termos_campos(textos, stopwords, stemming)
        termos_cod = []
        if not args.sem_codigo and campos["codigo"]:
            termos_cod = lexico.termos_codigo(campos["codigo"], tam_max=args.tam_max_codigo)
        t3 = time.perf_counter()
        tempos["lexico"] += t3 - t2

        # 4. inversão
        c["paginas"] += 1
        c["tokens_texto"] += n_tokens
        c["termos_texto"] += len(termos)
        c["termos_codigo"] += len(termos_cod)
        c["bytes_html"] += bytes_html
        c["bytes_texto"] += sum(len(s.encode("utf-8")) for s in textos)
        if not args.sem_codigo:
            c["bytes_codigo"] += len(campos["codigo"].encode("utf-8"))
        if not por_trecho:
            d = agrupa(termos)
            voc_texto.update(d)
            voc_total.update(d)
            dc = agrupa(termos_cod, PREFIXO_CODIGO)
            voc_total.update(dc)
            d.update(dc)
            if d:
                construtor.adiciona(pagina, d)
            c["unidades"] += 1
        else:
            # trechos de ~N tokens do texto original; o código forma trechos à parte
            partes = {}
            for t_, p in termos:
                partes.setdefault(("t", p // args.tam_trecho), []).append((t_, p))
            for t_, p in termos_cod:
                partes.setdefault(("c", p // args.tam_trecho), []).append((t_, p))
            for chave in sorted(partes):
                d = agrupa(partes[chave], PREFIXO_CODIGO if chave[0] == "c" else "")
                if chave[0] == "t":
                    voc_texto.update(d)
                voc_total.update(d)
                construtor.adiciona(c["unidades"], d)
                trechos.write(f"{c['unidades']}\t{pagina}\t{len(partes[chave])}\n")
                c["unidades"] += 1
        docs.write(f"{pagina}\t{url}\t{site_da_url(url)}\t{len(termos)}\t{len(termos_cod)}"
                   f"\t{limpa_tsv(campos['titulo'])}\n")
        tempos["inversao"] += time.perf_counter() - t3

        if c["paginas"] % HEAPS_A_CADA == 0:
            heaps.append((c["paginas"], c["tokens_texto"], c["termos_texto"], len(voc_texto),
                          c["termos_texto"] + c["termos_codigo"], len(voc_total)))
        if c["paginas"] % 5000 == 0:
            print(f"  {c['paginas']} páginas, {len(construtor.blocos)} blocos, "
                  f"{time.perf_counter() - inicio:.0f} s", file=sys.stderr, flush=True)

    heaps.append((c["paginas"], c["tokens_texto"], c["termos_texto"], len(voc_texto),
                  c["termos_texto"] + c["termos_codigo"], len(voc_total)))
    docs.close()
    if trechos:
        trechos.close()
    if cache:
        cache.close()
    del voc_texto, voc_total
    # o tempo de gravação dos blocos foi contado dentro da inversão
    tempos["inversao"] -= tempos["gravacao_blocos"]

    # 5. intercalação
    n_blocos = len(construtor.blocos) + (1 if construtor.bloco else 0)
    stats = construtor.intercala()
    tempos["total"] = time.perf_counter() - inicio - tempos["gravacao_campos"]

    with open(os.path.join(args.saida, "heaps.csv"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(",".join(map(str, linha)) for linha in heaps) + "\n")

    s = args.saida
    tam = {"vocabulario": tamanho_mb(os.path.join(s, "vocabulario.tsv")),
           "ocorrencias": tamanho_mb(os.path.join(s, "ocorrencias.bin")),
           "documentos": tamanho_mb(os.path.join(s, "documentos.tsv"))
           + tamanho_mb(os.path.join(s, "trechos.tsv"))}
    tam["total"] = sum(tam.values())
    texto_mb = (c["bytes_texto"] + c["bytes_codigo"]) / 2**20
    estat = {
        "parametros": {
            "entrada": os.path.basename(args.entrada), "granularidade": args.granularidade,
            "tam_trecho": args.tam_trecho if por_trecho else None,
            "posicoes": not args.sem_posicoes, "compressao": not args.sem_compressao,
            "codigo": not args.sem_codigo, "stopwords": not args.sem_stopwords,
            "stemming": stemming, "tam_max_codigo": args.tam_max_codigo,
            "bloco_mb": args.bloco, "limite": args.limite, "passo": args.passo,
        },
        "contagens": {**c, **stats, "vocabulario_texto": stats["vocabulario"]
                      - stats["vocabulario_codigo"]},
        "tempos_s": {k: round(v, 2) for k, v in tempos.items()},
        "memoria_pico_mb": pico_memoria_mb(),
        "blocos": {"quantidade": n_blocos, "temporarios_mb": construtor.bytes_temp / 2**20},
        "tamanhos_mb": tam,
        "texto_mb": texto_mb,
        "html_mb": c["bytes_html"] / 2**20,
        "indice_pct_texto": 100 * tam["total"] / texto_mb if texto_mb else None,
        "ocorrencias_pct_texto": 100 * tam["ocorrencias"] / texto_mb if texto_mb else None,
    }
    with open(os.path.join(s, "estatisticas.json"), "w", encoding="utf-8") as f:
        json.dump(estat, f, ensure_ascii=False, indent=2)
    return estat


def argumentos(lista=None):
    p = argparse.ArgumentParser(description="Constrói o índice invertido do VulnSearch.")
    p.add_argument("entrada", nargs="?", default="corpus.jsonl.gz",
                   help="corpus.jsonl.gz ou um arquivo gerado por --salvar-campos")
    p.add_argument("--saida", default="indice", help="pasta do índice (padrão: indice)")
    p.add_argument("--limite", type=int, default=0, help="indexa só N páginas")
    p.add_argument("--passo", type=int, default=1,
                   help="usa 1 página a cada K (o corpus está agrupado por site)")
    p.add_argument("--bloco", type=float, default=64,
                   help="MAX_TAMANHO do bloco em memória, em MB (padrão: 64)")
    p.add_argument("--granularidade", choices=["documento", "trecho"], default="documento")
    p.add_argument("--tam-trecho", type=int, default=200,
                   help="tokens por trecho na granularidade 'trecho' (padrão: 200)")
    p.add_argument("--sem-posicoes", action="store_true", help="guarda só doc e tf")
    p.add_argument("--sem-compressao", action="store_true",
                   help="inteiros de 4 bytes, sem gaps nem variable byte (para depurar)")
    p.add_argument("--sem-codigo", action="store_true", help="não indexa o campo código")
    p.add_argument("--sem-stopwords", action="store_true")
    p.add_argument("--sem-stemming", action="store_true")
    p.add_argument("--tam-max-codigo", type=int, default=lexico.TAM_MAX_CODIGO,
                   help=f"maior token aceito no código (padrão: {lexico.TAM_MAX_CODIGO}; 0 = sem limite)")
    p.add_argument("--salvar-campos", metavar="ARQ",
                   help="grava os campos extraídos em ARQ (.jsonl.gz) para reuso")
    return p.parse_args(lista)


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    args = argumentos()
    if not os.path.exists(args.entrada):
        sys.exit(f"Arquivo não encontrado: {args.entrada}")
    e = indexar(args)
    c, t, m = e["contagens"], e["tempos_s"], e["tamanhos_mb"]
    print(f"Páginas: {c['paginas']}  unidades: {c['unidades']}  "
          f"vocabulário: {c['vocabulario']} ({c['vocabulario_codigo']} do código)")
    print(f"Postings: {c['postings']}  ocorrências: {c['ocorrencias']}")
    print("Tempos (s): " + ", ".join(f"{k} {v}" for k, v in t.items()))
    print(f"Blocos: {e['blocos']['quantidade']} ({e['blocos']['temporarios_mb']:.1f} MB em disco)"
          f"  pico de memória: {e['memoria_pico_mb'] or 0:.0f} MB")
    print(f"Índice: {m['total']:.1f} MB (vocabulário {m['vocabulario']:.1f}, ocorrências "
          f"{m['ocorrencias']:.1f}, documentos {m['documentos']:.1f}) = "
          f"{e['indice_pct_texto'] or 0:.1f}% do texto extraído ({e['texto_mb']:.1f} MB)")
    print(f"Gravado em {args.saida}{os.sep}")


if __name__ == "__main__":
    main()
