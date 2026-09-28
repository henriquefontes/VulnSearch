# coletar.py - executa a coleta com o Katana, um processo por site (sites.py)
# Uso:
#   python coletar.py --teste                      coleta curta de todos os sites
#   python coletar.py                              coleta completa de todos os sites
#   python coletar.py --sites exploitdb            só os sites indicados
#   python coletar.py --sites ghsa --retomar ARQ   retoma um site interrompido com Ctrl+C
#                                                  (ARQ = resume-*.cfg indicado ao final)
#   python coletar.py --retomada                   continua a partir do plano gerado pelo
#                                                  retomar.py (após queda ou desligamento)
# Cada execução grava arquivos novos (coleta_<site>_1.jsonl, _2...), pois o
# Katana sobrescreve o arquivo de saída ao iniciar. Ctrl+C interrompe todos os
# sites; o Katana grava um arquivo de retomada para cada um.
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

from robots_escopo import UA_COMPLETO, gerar
from sites import SITES

CONTATO = "<email do grupo>"  # aparece no User-Agent enviado aos sites
EXTENSOES = "css,js,png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,zip,gz,pdf"


def proximo_numero(prefixo, site):
    n = 1
    while os.path.exists(f"{prefixo}_{site}_{n}.jsonl"):
        n += 1
    return n


def grava(caminho, linhas):
    with open(caminho, "w", encoding="utf-8") as f:
        f.write("\n".join(linhas) + "\n")


def linhas(caminho):
    try:
        with open(caminho, encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def prepara(nome, perfil, a):
    """Gera os arquivos do site e devolve o comando do Katana e as saídas."""
    teste = perfil["teste"] if a.teste else {}
    sementes = perfil["sementes"]()
    if a.plano:  # retomada: só as sementes que faltam, com a profundidade do plano
        sementes = a.plano[nome]["sementes"]
        teste = {"profundidade": a.plano[nome]["profundidade"]}
    if a.teste:
        sementes = sementes[:teste["sementes"]]
    arq_sementes = f"sementes_{nome}.txt"
    grava(arq_sementes, sementes)

    exclusoes, crawl_delay = gerar(arq_sementes)  # regras do robots.txt
    exclusoes += perfil["exclusoes"]
    arq_exclusoes = f"exclusoes_{nome}.txt"
    grava(arq_exclusoes, exclusoes or [r"^$"])

    prefixo = "teste" if a.teste else "coleta"
    n = proximo_numero(prefixo, nome)
    saida, log = f"{prefixo}_{nome}_{n}.jsonl", f"katana_{nome}_{n}.log"

    cmd = [a.katana,
           "-strategy", "breadth-first",
           "-depth", str(teste.get("profundidade", perfil["profundidade"])),
           "-field-scope", "rdn", "-crawl-out-scope", arq_exclusoes,
           "-extension-filter", EXTENSOES,
           "-rate-limit", "10",
           "-host-rate-limit", str(perfil["requisicoes_por_segundo"]),
           "-headers", f"User-Agent: {UA_COMPLETO}; contato: {CONTATO}",
           # No Katana, -timeout também é o tempo máximo que a fila de uma sessão
           # pode ficar vazia antes de a sessão ser encerrada. Nas cadeias do
           # exploit-db e nas listagens, a fila fica vazia enquanto a próxima
           # página espera a vez no limite de taxa e é baixada; com 15 s, as
           # sessões terminavam antes da hora. 60 s dá folga para essa espera.
           "-timeout", "60", "-retry", "2",
           "-max-domain-pages", str(teste.get("max_paginas", perfil["max_paginas"])),
           "-crawl-duration", "5m" if a.teste else "24h",
           "-jsonl", "-omit-raw", "-output", saida,
           "-error-log", f"erros_{nome}.log"]
    if crawl_delay:
        # O -delay do Katana vale para cada tarefa paralela, não para o servidor:
        # com várias tarefas, as requisições sairiam em rajadas. Para respeitar o
        # Crawl-delay como intervalo mínimo entre requisições, uma por vez.
        cmd += ["-concurrency", "1", "-parallelism", "1", "-delay", f"{crawl_delay:g}"]
        print(f"[{nome}] Crawl-delay de {crawl_delay:g} s: uma requisição por vez")
    else:
        # sem Crawl-delay, o ritmo é controlado pelo -host-rate-limit
        cmd += ["-concurrency", "5", "-parallelism", "5"]
    if perfil["escopo"]:
        arq_escopo = f"escopo_{nome}.txt"
        grava(arq_escopo, perfil["escopo"])
        cmd += ["-crawl-scope", arq_escopo]
    if perfil["sitemap"]:
        cmd += ["-known-files", "sitemapxml"]
    if perfil["ignorar_parametros"]:
        cmd += ["-ignore-query-params"]
    cmd += ["-resume", a.retomar] if a.retomar else ["-list", arq_sementes]
    return cmd, saida, log


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sites", default=",".join(SITES),
                   help=f"sites separados por vírgula (disponíveis: {', '.join(SITES)})")
    p.add_argument("--teste", action="store_true", help="coleta curta de teste")
    p.add_argument("--retomar", metavar="ARQ", help="arquivo resume-*.cfg do Katana")
    p.add_argument("--retomada", action="store_true",
                   help="continua a coleta a partir do retomada.json gerado pelo retomar.py")
    p.add_argument("--katana", default=shutil.which("katana") or "katana",
                   help="caminho do executável do Katana")
    a = p.parse_args()

    a.plano = None
    if a.retomada:
        if a.teste or a.retomar:
            sys.exit("--retomada não pode ser usado com --teste ou --retomar.")
        try:
            with open("retomada.json", encoding="utf-8") as f:
                a.plano = json.load(f)
        except OSError:
            sys.exit("retomada.json não encontrado. Rode antes: python retomar.py")
        if not a.plano:
            sys.exit("Nada a retomar: todos os sites estão completos.")
        a.sites = ",".join(a.plano)
    nomes = [s.strip() for s in a.sites.split(",") if s.strip()]
    desconhecidos = [s for s in nomes if s not in SITES]
    if desconhecidos:
        sys.exit(f"Site(s) desconhecido(s): {', '.join(desconhecidos)}. "
                 f"Disponíveis: {', '.join(SITES)}")
    if a.retomar and len(nomes) != 1:
        sys.exit("--retomar exige um único site em --sites.")
    if not shutil.which(a.katana) and not os.path.isfile(a.katana):
        sys.exit("Katana não encontrado. Instale-o (veja o README) ou use --katana CAMINHO.")

    processos = {}
    for nome in nomes:
        print(f"[{nome}] lendo o robots.txt e preparando a coleta...")
        cmd, saida, log = prepara(nome, SITES[nome], a)
        with open(log, "w", encoding="utf-8") as f:
            f.write("CMD: " + " ".join(cmd) + "\n")
            f.flush()
            proc = subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT)
        processos[nome] = (proc, saida, log)
        print(f"[{nome}] coletando em {saida} (log: {log})")

    print("\nCtrl+C interrompe todos os sites e gera arquivos de retomada.\n")
    try:
        segundos = 0
        while any(p.poll() is None for p, _, _ in processos.values()):
            time.sleep(1)
            segundos += 1
            if segundos % 30:
                continue
            estado = "  ".join(
                f"{nome}: {linhas(saida)} linhas{'' if p.poll() is None else ' (fim)'}"
                for nome, (p, saida, _) in processos.items())
            print(time.strftime("%H:%M:%S"), estado)
    except KeyboardInterrupt:
        # o Ctrl+C também chega aos processos do Katana, que gravam o estado
        print("\nInterrompido. Aguardando o Katana gravar o estado de cada site...")
        for p, _, _ in processos.values():
            try:
                p.wait(timeout=60)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                p.kill()

    print("\nResumo:")
    for nome, (p, saida, log) in processos.items():
        print(f"  {nome}: {linhas(saida)} linhas em {saida} (código {p.returncode})")
        with open(log, encoding="utf-8", errors="ignore") as f:
            retomada = re.findall(r"resume file: (\S+\.cfg)", f.read())
        if retomada:
            print(f"    para retomar: python coletar.py --sites {nome} --retomar {retomada[-1]}")
        elif p.returncode not in (0, None):
            print(f"    o Katana terminou com erro; veja {log}")
    prefixo = "teste" if a.teste else "coleta"
    print(f"\nPara aplicar a seleção de documentos e ver as estatísticas:\n"
          f"  python processar.py {prefixo}_*.jsonl")


if __name__ == "__main__":
    main()
