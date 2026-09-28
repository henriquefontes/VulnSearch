# retomar.py - descobre onde a coleta parou e monta um plano para continuar
# Uso: python retomar.py
#   Lê os coleta_<site>_*.jsonl já gravados (inclusive com a última linha
#   cortada por um desligamento), mostra quanto cada site já coletou e grava
#   retomada.json com as sementes que faltam. Depois:
#       python coletar.py --retomada
#   Serve quando não há arquivo de retomada do Katana (queda de energia,
#   computador desligado). As páginas coletadas duas vezes são removidas
#   depois pelo processar.py.
import glob
import json
import re
from collections import Counter, defaultdict
from urllib.parse import parse_qsl, urlencode, urlparse

from sites import EXPLOITDB_PASSO, EXPLOITDB_ULTIMO_ID, SITES

# Exploit Database: faixa de ids sem páginas maior que isto indica que a coleta
# não passou por ali (os ids têm lacunas naturais, geralmente pequenas).
LACUNA_MAX = 50
PASSO_RETOMADA = 100      # sementes a cada 100 ids nos blocos não cobertos
PROFUNDIDADE_RETOMADA = 150
# Listagens: página com menos que esta fração dos itens da página mais cheia
# é considerada incompleta e entra de novo.
FRACAO_LISTAGEM = 0.8
CWE_MINIMO = 900  # abaixo disso, o CWE é coletado de novo (leva ~10 min)


def normaliza(url):
    """Compara URLs ignorando barra final e ordem dos parâmetros."""
    p = urlparse(url)
    consulta = urlencode(sorted(parse_qsl(p.query)))
    return f"{p.netloc.lower()}{p.path.rstrip('/')}?{consulta}"


CAMPO = {k: re.compile(rb'"%s"\s*:\s*"((?:[^"\\]|\\.)*)"' % k.encode())
         for k in ("endpoint", "source")}


def campo(cabeca, nome):
    m = CAMPO[nome].search(cabeca)
    return json.loads(b'"' + m.group(1) + b'"') if m else ""


def le_site(nome):
    """Devolve (URLs visitadas, contagem por listagem de origem, linhas cortadas).

    Para ser rápido em arquivos de vários GB, não interpreta o HTML: lê só a
    URL e a origem no início de cada linha (o objeto request vem antes da resposta).
    """
    visitadas, origens, cortadas = set(), Counter(), 0
    escopo = [re.compile(r) for r in SITES[nome]["escopo"]]
    for arquivo in sorted(glob.glob(f"coleta_{nome}_*.jsonl")):
        with open(arquivo, "rb") as f:
            for linha in f:
                if not linha.rstrip().endswith(b"}"):
                    cortadas += 1  # linha interrompida pelo desligamento
                    continue
                if b'"status_code"' not in linha:
                    continue  # link descoberto, não visitado
                cabeca = linha[:8192]
                url = campo(cabeca, "endpoint")
                if not url or url in visitadas:
                    continue
                visitadas.add(url)
                origem = campo(cabeca, "source")
                if origem and (not escopo or any(r.search(url) for r in escopo)):
                    origens[normaliza(origem)] += 1
    return visitadas, origens, cortadas


def plano_exploitdb(visitadas):
    ids = sorted({int(m.group(1)) for u in visitadas
                  if (m := re.search(r"/exploits/(\d+)$", u))})
    faltam = []
    for inicio in range(1, EXPLOITDB_ULTIMO_ID + 1, EXPLOITDB_PASSO):
        fim = inicio + EXPLOITDB_PASSO
        dentro = [i for i in ids if inicio <= i < fim]
        marcos = [inicio - 1] + dentro + [fim]
        maior_lacuna = max(b - a for a, b in zip(marcos, marcos[1:]))
        if maior_lacuna > LACUNA_MAX:
            faltam.append(inicio)
    sementes = [f"https://www.exploit-db.com/exploits/{i}"
                for b in faltam for i in range(b, b + EXPLOITDB_PASSO, PASSO_RETOMADA)]
    info = f"{len(ids)} exploits; {len(faltam)} de {len(range(1, EXPLOITDB_ULTIMO_ID + 1, EXPLOITDB_PASSO))} blocos de {EXPLOITDB_PASSO} ids incompletos"
    return sementes, PROFUNDIDADE_RETOMADA, info


def plano_listagem(nome, origens):
    sementes = SITES[nome]["sementes"]()
    cheia = max(origens.values(), default=0)
    pendentes = [s for s in sementes
                 if origens.get(normaliza(s), 0) < FRACAO_LISTAGEM * cheia or cheia == 0]
    info = f"{len(sementes) - len(pendentes)} de {len(sementes)} páginas de listagem concluídas"
    return pendentes, SITES[nome]["profundidade"], info


def main():
    plano = {}
    print(f"{'site':<10} {'páginas':>8}  situação")
    for nome in SITES:
        if not glob.glob(f"coleta_{nome}_*.jsonl"):
            print(f"{nome:<10} {0:>8}  nenhum arquivo: coletar do zero")
            plano[nome] = {"sementes": SITES[nome]["sementes"](),
                           "profundidade": SITES[nome]["profundidade"]}
            continue
        visitadas, origens, cortadas = le_site(nome)
        if nome == "exploitdb":
            sementes, prof, info = plano_exploitdb(visitadas)
        elif nome == "cwe":
            completo = len(visitadas) >= CWE_MINIMO
            sementes = [] if completo else SITES[nome]["sementes"]()
            prof = SITES[nome]["profundidade"]
            info = "completo" if completo else "incompleto: coletar de novo (~10 min)"
        else:
            sementes, prof, info = plano_listagem(nome, origens)
        if cortadas:
            info += f"; {cortadas} linha(s) cortada(s) ignorada(s)"
        situacao = "OK" if not sementes else f"faltam {len(sementes)} sementes"
        print(f"{nome:<10} {len(visitadas):>8}  {situacao} ({info})")
        if sementes:
            plano[nome] = {"sementes": sementes, "profundidade": prof}

    with open("retomada.json", "w", encoding="utf-8") as f:
        json.dump(plano, f, indent=1)
    if plano:
        print(f"\nPlano gravado em retomada.json ({', '.join(plano)}). Para continuar:\n"
              f"  python coletar.py --retomada")
    else:
        print("\nTodos os sites estão completos. Rode: python processar.py coleta_*.jsonl")


if __name__ == "__main__":
    main()
