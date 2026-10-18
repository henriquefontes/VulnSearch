# buscar.py - busca booleana sobre o índice (verificação e demonstração)
# Uso: python buscar.py "consulta" [--indice indice] [-n 10]
#      python buscar.py                  (modo interativo; linha vazia sai)
#
# Sintaxe da consulta:
#   sql injection          AND implícito entre os termos
#   wordpress OR joomla    OR entre dois termos vizinhos (liga mais forte que o AND)
#   xss -wordpress         NOT (também: NOT wordpress)
#   "denial of service"    frase (usa as posições; stopwords contam como lacuna)
#   codigo:strcpy          só no campo código (sem stemming)
#   cve-2021-44228         identificadores, versões e pacotes são termos inteiros
# Uma palavra comum é buscada no texto (com stemming) OU no código.
# Os resultados saem na ordem dos documentos: o ranqueamento é a próxima etapa.
import argparse
import re
import sys
import time

import lexico
from indice import PREFIXO_CODIGO, Indice

PARTES = re.compile(r'-?"[^"]*"|\S+')


# ------------------------------------------- operações sobre listas ordenadas
def intersecao(a, b):
    i = j = 0
    saida = []
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            saida.append(a[i])
            i += 1
            j += 1
        elif a[i] < b[j]:
            i += 1
        else:
            j += 1
    return saida


def uniao(a, b):
    i = j = 0
    saida = []
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            saida.append(a[i])
            i += 1
            j += 1
        elif a[i] < b[j]:
            saida.append(a[i])
            i += 1
        else:
            saida.append(b[j])
            j += 1
    return saida + a[i:] + b[j:]


def diferenca(a, b):
    excluir = set(b)
    return [x for x in a if x not in excluir]


class Buscador:
    def __init__(self, pasta="indice"):
        self.ind = Indice(pasta)

    def _paginas(self, unidades):
        """Unidades (páginas ou trechos) -> páginas, ordenadas e sem repetição."""
        if self.ind.trechos is None:
            return unidades
        return sorted({self.ind.pagina(u) for u in unidades})

    def _frase(self, termos):
        """termos: [(termo, posição na consulta)]. Páginas com os termos nas
        mesmas distâncias relativas da consulta."""
        listas = [self.ind.lista(t) for t, _ in termos]
        if not all(listas):
            return []
        if len(termos) == 1:
            return self._paginas([d for d, _, _ in listas[0]])
        comuns = [d for d, _, _ in listas[0]]
        for lst in listas[1:]:
            comuns = intersecao(comuns, [d for d, _, _ in lst])
        if not self.ind.posicoes:  # índice sem posições: vira AND
            return self._paginas(comuns)
        posicoes = [{d: set(p) for d, _, p in lst} for lst in listas]
        base = termos[0][1]
        saida = []
        for d in comuns:
            if any(all(p + (q - base) in posicoes[k][d] for k, (_, q) in enumerate(termos))
                   for p in posicoes[0][d]):
                saida.append(d)
        return self._paginas(saida)

    def _item(self, parte):
        """Páginas de uma parte da consulta, ou None se ela não restringe nada
        (só stopwords)."""
        if parte.lower().startswith("codigo:"):
            termos = [(PREFIXO_CODIGO + t, p)
                      for t, p in lexico.termos_codigo(parte[7:], tam_max=0)]
            return self._frase(termos) if termos else None
        if parte.startswith('"'):
            termos = lexico.termos_texto(parte.strip('"'))
            return self._frase(termos) if termos else None
        termos = lexico.termos_texto(parte)
        if not termos:
            return None
        resultado = self._frase(termos)
        # a mesma palavra no código (sem stemming)
        cod = [(PREFIXO_CODIGO + t, p) for t, p in lexico.termos_codigo(parte, tam_max=0)]
        if cod:
            resultado = uniao(resultado, self._frase(cod))
        return resultado

    def busca(self, consulta):
        partes = PARTES.findall(consulta)
        conjuncao, negados = [], []
        i = 0
        while i < len(partes):
            parte, negar = partes[i], False
            if parte == "NOT" and i + 1 < len(partes):
                i += 1
                parte, negar = partes[i], True
            elif parte.startswith("-") and len(parte) > 1:
                parte, negar = parte[1:], True
            atual = self._item(parte)
            while i + 2 < len(partes) and partes[i + 1] == "OR":
                outro = self._item(partes[i + 2])
                atual = outro if atual is None else (atual if outro is None else uniao(atual, outro))
                i += 2
            if atual is not None:
                (negados if negar else conjuncao).append(atual)
            i += 1
        if not conjuncao:
            return []
        conjuncao.sort(key=len)  # interseção começando pela lista mais curta
        resultado = conjuncao[0]
        for lst in conjuncao[1:]:
            resultado = intersecao(resultado, lst)
        for lst in negados:
            resultado = diferenca(resultado, lst)
        return resultado


def mostra(buscador, consulta, n):
    t = time.perf_counter()
    docs = buscador.busca(consulta)
    ms = (time.perf_counter() - t) * 1000
    print(f"{len(docs)} documentos ({ms:.1f} ms)")
    for d in docs[:n]:
        doc = buscador.ind.documentos[d]
        print(f"  [{d}] {doc['site']}  {doc['titulo'][:90]}\n        {doc['url']}")
    if len(docs) > n:
        print(f"  ... e mais {len(docs) - n}")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="Busca booleana no índice do VulnSearch.")
    p.add_argument("consulta", nargs="*")
    p.add_argument("--indice", default="indice")
    p.add_argument("-n", type=int, default=10, help="resultados mostrados (padrão: 10)")
    a = p.parse_args()
    t = time.perf_counter()
    buscador = Buscador(a.indice)
    print(f"Índice carregado: {len(buscador.ind.vocabulario)} termos, "
          f"{len(buscador.ind.documentos)} documentos ({time.perf_counter() - t:.1f} s)")
    if a.consulta:
        mostra(buscador, " ".join(a.consulta), a.n)
        return
    while True:
        try:
            consulta = input("\nconsulta> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not consulta:
            break
        mostra(buscador, consulta, a.n)


if __name__ == "__main__":
    main()
