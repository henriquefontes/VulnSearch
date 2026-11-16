# grafico_avaliacao.py - resultados_avaliacao/metricas_modelos.svg (sem dependências)
# Três painéis (P@10, MAP, nDCG@10), barras horizontais de uma só cor, modelos na mesma
# ordem (nDCG@10 decrescente); os que não formaram o pool aparecem com a barra tracejada.
import csv
import os

PASTA = "resultados_avaliacao"
linhas = list(csv.DictReader(open(os.path.join(PASTA, "modelos_resumo.csv"), encoding="utf-8")))
linhas.sort(key=lambda l: -float(l["nDCG@10"]))
metricas = ["P@10", "MAP", "nDCG@10"]
W, ROT, PAINEL, ALT, TOPO = 980, 90, 280, 26, 60
H = TOPO + ALT * len(linhas) + 70
cor, tinta, tinta2, grade = "#2a6fb0", "#202124", "#5f6368", "#e3e3e3"
s = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
     f'font-family="Arial, sans-serif" font-size="12">',
     f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
     f'<text x="16" y="24" font-size="15" fill="{tinta}">Métricas por modelo (20 consultas, julgamentos do Claude Code; padrões do BM25F)</text>',
     f'<text x="16" y="42" fill="{tinta2}">Barra tracejada: modelo fora do pool (documentos não julgados contam como não relevantes; métrica subestimada)</text>']
for k, m in enumerate(metricas):
    x0 = ROT + 16 + k * (PAINEL + 10)
    s.append(f'<text x="{x0}" y="{TOPO - 4}" font-weight="bold" fill="{tinta}">{m}</text>')
    for t in (0, 0.5, 1):
        xx = x0 + t * (PAINEL - 50)
        s.append(f'<line x1="{xx}" y1="{TOPO}" x2="{xx}" y2="{TOPO + ALT * len(linhas)}" stroke="{grade}"/>')
        s.append(f'<text x="{xx}" y="{TOPO + ALT * len(linhas) + 14}" text-anchor="middle" fill="{tinta2}">{t:g}</text>')
    for i, l in enumerate(linhas):
        v = float(l[m])
        y = TOPO + i * ALT + 5
        w = max(2, v * (PAINEL - 50))
        fora = l["formou o pool"] == "não"
        estilo = (f'fill="#ffffff" stroke="{cor}" stroke-width="2" stroke-dasharray="4 3"' if fora
                  else f'fill="{cor}"')
        s.append(f'<rect x="{x0}" y="{y}" width="{w:.1f}" height="{ALT - 10}" rx="3" {estilo}/>')
        s.append(f'<text x="{x0 + w + 4:.1f}" y="{y + ALT - 14}" fill="{tinta}">{v:.3f}</text>')
        if k == 0:
            s.append(f'<text x="{ROT + 8}" y="{y + ALT - 14}" text-anchor="end" fill="{tinta}">'
                     f'{l["modelo"]}{" *" if fora else ""}</text>')
s.append(f'<text x="16" y="{H - 16}" fill="{tinta2}">* fora do pool (jaccard, bm1, bm15, bm11). Fonte: resultados_avaliacao/modelos_resumo.csv</text>')
s.append("</svg>")
open(os.path.join(PASTA, "metricas_modelos.svg"), "w", encoding="utf-8").write("\n".join(s))
print("resultados_avaliacao/metricas_modelos.svg")
