# Julgamento de relevância: guia do grupo

Precisamos julgar **447 documentos** de **20 consultas** (os *pools*: top-10 dos modelos
TF-IDF, vetorial, BM25 e BM25F). Com esses julgamentos, o `avaliar.py` calcula P@10, MAP e
nDCG@10 e escolhe K₁, b e os pesos do BM25F.

## 1. Subir o servidor e abrir a página

É preciso o índice completo (`indice/`). Quem ainda não tem: baixe o `corpus.jsonl.gz` da
release `coleta-v1` do repositório e rode `python indexar.py` (~4 min).

```
pip install -r requirements.txt
python servidor.py
```

Abra **http://127.0.0.1:8000/julgar**:

1. digite seu **nome** no campo Avaliador (ele é gravado em cada julgamento);
2. escolha a **consulta**;
3. julgue cada documento com os botões ou com o teclado:

| Tecla | Ação |
|---|---|
| `2`, `1`, `0` | julga o documento atual e vai para o próximo sem julgamento |
| `↓` / `↑` (ou `→` / `←`) | muda o documento atual |
| `c` | abre a cópia em cache (texto e código completos) |

Para fechar: Ctrl+C no terminal do servidor. Tudo já fica gravado a cada clique; dá para
parar e continuar depois, inclusive em outro dia: a página lembra o seu nome e mostra o que
você já julgou.

## 2. Critério

Pergunta: **o documento ajuda quem fez essa consulta?**

| Nota | Significado | Exemplos |
|---|---|---|
| **2** | **Trata da vulnerabilidade ou do assunto pedido** | Exploit ou aviso do próprio CVE pedido; definição do CWE pedido; exploit de SQL injection num plugin do WordPress para `sql injection wordpress plugin` |
| **1** | **Relacionado**, mas não é o que foi pedido | Outra versão ou produto parecido; CWE vizinho; o assunto aparece só de passagem |
| **0** | **Não serve** | Assunto diferente; casou só palavras soltas (ex.: "injection" num documento sobre outra falha) |

Regras:

- **Julgue o documento**, não o trecho. Na dúvida, abra a cópia em cache (`c`).
- A ordem é aleatória e a página **não mostra o modelo, a posição nem o score**, para não
  enviesar. Não procure esses dados no arquivo `.tsv` antes de julgar.
- Use o campo **observação** quando a decisão for difícil; ajuda a discutir depois.
- Errou? Clique na nota certa (substitui) ou em **desfazer**.
- Não combine notas com os colegas antes de julgar as consultas da concordância.

## 3. Divisão das consultas

Cada consulta é julgada por **uma pessoa**, e **duas consultas são julgadas por duas
pessoas**, para medir a concordância entre avaliadores. A sugestão é usar **q03** (`CWE-79`,
19 documentos, identificador) e **q14** (`java deserialization`, 22, conceito), que são de
tipos diferentes e de tamanho médio.

Tamanho de cada pool:

| Consulta | Docs | Consulta | Docs | Consulta | Docs | Consulta | Docs |
|---|---:|---|---:|---|---:|---|---:|
| q01 CVE-2021-44228 | 6 | q06 remote code execution apache struts | 23 | q11 privilege escalation linux kernel | 26 | q16 csrf token bypass | 27 |
| q02 MS17-010 | 5 | q07 cross site scripting drupal | 26 | q12 log4j | 10 | q17 use after free | 30 |
| q03 CWE-79 | 19 | q08 joomla sql injection | 30 | q13 path traversal | 30 | q18 strcpy stack overflow | 34 |
| q04 SA-CORE-2018-002 | 7 | q09 buffer overflow windows smb | 22 | q14 java deserialization | 22 | q19 codigo:shellcode | 28 |
| q05 sql injection wordpress plugin | 32 | q10 openssh vulnerability | 16 | q15 denial of service | 29 | q20 codigo:system | 25 |

**Exemplo para 4 integrantes** (ajuste os nomes e, se o grupo tiver outro tamanho, divida os
447 + 41 da concordância por igual, somando os tamanhos acima):

| Pessoa | Consultas | Docs |
|---|---|---:|
| A | q05, q13, q19, q04, q10 + **q14** (concordância) | 113 + 22 = 135 |
| B | q18, q08, q11, q01, q12 + **q03** (concordância) | 106 + 19 = 125 |
| C | q17, q15, q07, q02, q20 | 115 |
| D | q16, q06, q09, q03, q14 | 113 |

Na concordância, o **primeiro** a julgar grava no arquivo principal; o **segundo** grava em
`julgamentos/segunda_avaliacao/` (a página avisa "outra pessoa já julgou este documento" e
não mostra a nota dela). Só o principal entra na avaliação; a segunda avaliação serve para
comparar as duas pessoas (ex.: kappa de Cohen).

## 4. Onde ficam os julgamentos e como juntar

- `julgamentos/pool_qXX.tsv`: colunas `relevante`, `observacao` e `avaliador` preenchidas
  pela página (as outras colunas não mudam).
- `julgamentos/segunda_avaliacao/pool_qXX.tsv`: julgamentos da concordância.

Há duas formas de trabalhar; escolham uma antes de começar:

1. **Um servidor para todos** (recomendado): uma pessoa sobe o servidor e os outros julgam
   pelo navegador, na rede da faculdade ou numa VPS com acesso restrito pelo firewall
   (`python servidor.py --host 0.0.0.0` + `ufw allow from <IP>`; ver README). Todos os
   julgamentos ficam no mesmo lugar, e a concordância funciona sozinha.
2. **Cada um na sua máquina**: cada pessoa julga **só as suas consultas** e faz commit apenas
   dos `pool_qXX.tsv` delas. Nas duas consultas da concordância, o segundo avaliador precisa
   dar `git pull` **depois** que o primeiro terminou e enviou; senão os dois gravam no mesmo
   arquivo e o Git acusa conflito.

Quando todas as consultas estiverem julgadas:

```
python avaliar.py --juntar     # julgamentos/pool_*.tsv -> julgamentos/qrels.tsv
python avaliar.py              # P@10, MAP, nDCG@10 e busca em grade de K1, b e pesos
```
