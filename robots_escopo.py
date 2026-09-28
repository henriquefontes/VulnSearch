# robots_escopo.py - gera as exclusões do Katana a partir do robots.txt
# Uso: python3 robots_escopo.py seeds.txt [exclusoes_extra.txt]
# Saídas: exclusoes.txt (uma regex por linha, para -crawl-out-scope)
#         e o Crawl-delay declarado (s), impresso no terminal.
# Tratamento do robots.txt conforme a RFC 9309:
#   2xx -> aplica as regras Disallow do grupo do nosso User-Agent;
#   4xx -> arquivo indisponível: não há restrições;
#   5xx ou erro de rede -> o site inteiro é excluído, por precaução.
import re
import sys
import urllib.error
import urllib.request
from urllib.parse import urlparse, unquote
from urllib.robotparser import RobotFileParser

UA_ROBO = "VulnSearchBot"  # token usado para casar grupos do robots.txt
UA_COMPLETO = "VulnSearchBot/1.0 (trabalho academico PUC Minas)"


def baixa_robots(host):
    """Retorna (status, linhas) do robots.txt do host."""
    req = urllib.request.Request(f"https://{host}/robots.txt",
                                 headers={"User-Agent": UA_COMPLETO})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, resp.read().decode("utf-8", "ignore").splitlines()
    except urllib.error.HTTPError as erro:
        return erro.code, []
    except Exception:  # DNS, timeout, conexão recusada...
        return 599, []


def regras_bloqueadas(rp, ua):
    """Caminhos Disallow do grupo de regras que se aplica ao nosso UA."""
    grupos = rp.entries + ([rp.default_entry] if rp.default_entry else [])
    for grupo in grupos:
        if grupo.applies_to(ua):
            return [unquote(r.path) for r in grupo.rulelines
                    if not r.allowance and r.path]
    return []


def caminho_para_regex(host, caminho):
    """Converte um caminho do robots.txt (com * e $) em regex de URL."""
    fim = caminho.endswith("$")
    if fim:
        caminho = caminho[:-1]
    padrao = re.escape(caminho).replace(r"\*", ".*")
    return "^https?://" + re.escape(host) + padrao + ("$" if fim else "")


def gerar(arq_seeds, arq_extra=None):
    """Retorna (lista de regex de exclusão, Crawl-delay em segundos ou 0)."""
    exclusoes, crawl_delay = [], 0.0
    hosts = {urlparse(l.strip()).netloc for l in open(arq_seeds, encoding="utf-8") if l.strip()}
    for host in sorted(hosts):
        status, linhas = baixa_robots(host)
        if status >= 500:
            print(f"[aviso] {host}: robots.txt com erro {status}; site excluído")
            exclusoes.append("^https?://" + re.escape(host) + "/")
            continue
        if status >= 400:
            print(f"{host}: robots.txt indisponível ({status}); sem restrições")
            continue
        rp = RobotFileParser()
        rp.parse(linhas)
        bloqueados = regras_bloqueadas(rp, UA_ROBO)
        exclusoes += [caminho_para_regex(host, c) for c in bloqueados]
        atraso = rp.crawl_delay(UA_ROBO)
        crawl_delay = max(crawl_delay, float(atraso or 0))
        print(f"{host}: {len(bloqueados)} caminhos proibidos, crawl-delay={atraso}")
    if arq_extra:  # padrões definidos pelo grupo (login, busca, downloads...)
        exclusoes += [l.strip() for l in open(arq_extra, encoding="utf-8")
                      if l.strip() and not l.startswith("#")]
    return exclusoes, crawl_delay


if __name__ == "__main__":
    regras, atraso = gerar(*sys.argv[1:3])
    with open("exclusoes.txt", "w", encoding="utf-8") as saida:
        saida.write("\n".join(regras) + "\n")
    print(f"{len(regras)} exclusões gravadas em exclusoes.txt; crawl-delay: {atraso:g} s")
