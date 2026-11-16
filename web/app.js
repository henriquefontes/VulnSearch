"use strict";

const API = window.VULNSEARCH_API || "";
const $ = (s, raiz = document) => raiz.querySelector(s);
const $$ = (s, raiz = document) => [...raiz.querySelectorAll(s)];
const NUM = new Intl.NumberFormat("pt-BR");
const fmt = (n) => NUM.format(n);

const FONTES = {
  "www.exploit-db.com":   { curto: "Exploit-DB", sigla: "EDB", cor: "#c62828" },
  "github.com":           { curto: "GitHub Advisories", sigla: "GH", cor: "#24292f" },
  "www.rapid7.com":       { curto: "Rapid7", sigla: "R7", cor: "#e8590c" },
  "cwe.mitre.org":        { curto: "CWE", sigla: "CWE", cor: "#1565c0" },
  "www.drupal.org":       { curto: "Drupal", sigla: "D", cor: "#00796b", icone: "https://www.drupal.org/favicon.ico" },
  "developer.joomla.org": { curto: "Joomla", sigla: "J", cor: "#5e35b1" },
};
const PARAMS = ["k1", "b", "peso_titulo", "peso_codigo"];
const ROTULO_PARAM = { k1: "K₁", b: "b", peso_titulo: "peso do título", peso_codigo: "peso do código" };
const PASSO_PARAM = { k1: 0.1, b: 0.05, peso_titulo: 0.5, peso_codigo: 0.5 };

let modelos = { padrao: "bm25f", modelos: [] };
let sites = [];
let estado = {};
let ultimaResposta = null;
let requisicao = 0;

// ---------------------------------------------------------------- utilidades
function el(tag, props = {}, ...filhos) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") e.className = v;
    else if (k === "dataset") Object.assign(e.dataset, v);
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (k in e) e[k] = v;
    else e.setAttribute(k, v);
  }
  for (const f of filhos) if (f != null && f !== false && f !== 0 && f !== "") e.append(f);
  return e;
}

function segmentos(segs) {
  const frag = document.createDocumentFragment();
  for (const s of segs || []) {
    frag.append(s.destaque ? el("mark", { textContent: s.texto }) : document.createTextNode(s.texto));
  }
  return frag;
}

async function api(caminho, params = {}) {
  const u = new URL(API + caminho, location.href);
  for (const [k, v] of Object.entries(params)) {
    for (const x of [].concat(v)) if (x !== undefined && x !== null && x !== "") u.searchParams.append(k, x);
  }
  const r = await fetch(u);
  let js;
  try { js = await r.json(); } catch { throw new Error(`Resposta inválida do servidor (${r.status}).`); }
  if (!r.ok) throw new Error(js.erro || r.statusText);
  return js;
}

function carregando(sim) { $("#carregando").hidden = !sim; }

function guarda(chave, valor) { try { localStorage.setItem(chave, JSON.stringify(valor)); } catch { } }
function le(chave, padrao) {
  try { const v = localStorage.getItem(chave); return v ? JSON.parse(v) : padrao; } catch { return padrao; }
}

// ---------------------------------------------------------------- logo
let nLogo = 0;
function escudo() {
  const id = "grad-escudo-" + (++nLogo);
  return `<svg class="escudo" viewBox="0 0 24 26" aria-hidden="true"><defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1">` +
    `<stop offset="0" style="stop-color:var(--alto)"/><stop offset="1" style="stop-color:var(--critico)"/></linearGradient></defs>` +
    `<path fill="url(#${id})" d="M12 0 1 4.5v7C1 18.3 5.7 24.4 12 26c6.3-1.6 11-7.7 11-14.5v-7z"/>` +
    `<circle cx="10.8" cy="11.4" r="4.6" fill="none" stroke="#fff" stroke-width="2.2"/>` +
    `<path d="M14.3 15l3.6 3.8" stroke="#fff" stroke-width="2.6" stroke-linecap="round"/>` +
    `<circle cx="10.8" cy="11.4" r="1.5" fill="#fff"/></svg>`;
}
function desenhaLogo(alvo) {
  alvo.insertAdjacentHTML("beforeend", escudo());
  alvo.append(el("span", { class: "marca" }, el("span", { class: "vuln", textContent: "Vuln" }),
    el("span", { class: "search", textContent: "Search" })));
}

// ---------------------------------------------------------------- estado <-> URL
function estadoDaUrl() {
  const p = new URLSearchParams(location.search);
  const e = {
    q: (p.get("q") || "").trim(),
    site: p.get("site") || "",
    modelo: p.get("modelo") || "",
    pagina: Math.max(1, parseInt(p.get("pagina"), 10) || 1),
    por_pagina: parseInt(p.get("por_pagina"), 10) || 10,
    cve: p.getAll("cve"), cwe: p.getAll("cwe"),
    explicar: p.get("explicar") === "true",
    doc: p.get("doc") || "",
  };
  for (const k of PARAMS) e[k] = p.get(k) || "";
  return e;
}

function urlDoEstado(e) {
  const p = new URLSearchParams();
  if (e.q) p.set("q", e.q);
  if (e.site) p.set("site", e.site);
  for (const x of e.cve || []) p.append("cve", x);
  for (const x of e.cwe || []) p.append("cwe", x);
  if (e.modelo && e.modelo !== modelos.padrao) p.set("modelo", e.modelo);
  for (const k of PARAMS) if (e[k] !== "") p.set(k, e[k]);
  if (e.explicar) p.set("explicar", "true");
  if (e.por_pagina && e.por_pagina !== 10) p.set("por_pagina", e.por_pagina);
  if (e.pagina > 1) p.set("pagina", e.pagina);
  if (e.doc) p.set("doc", e.doc);
  const s = p.toString();
  return location.pathname + (s ? "?" + s : "");
}

function navega(mudancas, { substituir = false } = {}) {
  const novo = { ...estado, ...mudancas };
  if (!("doc" in mudancas)) novo.doc = "";
  const url = urlDoEstado(novo);
  const st = novo.doc && estado.q && !estado.doc ? { deResultados: true } : null;
  if (substituir) history.replaceState(st, "", url); else history.pushState(st, "", url);
  renderiza();
}

// ---------------------------------------------------------------- roteamento
function mostra(id) {
  for (const s of ["inicio", "resultados", "cache"]) $("#" + s).hidden = s !== id;
}

function renderiza() {
  estado = estadoDaUrl();
  for (const i of $$("input[name=q]")) i.value = estado.q;
  atualizaLimpar();
  fechaSugestoes();
  if (estado.doc) { mostra("cache"); abreDocumento(); return; }
  if (!estado.q) {
    mostra("inicio");
    document.title = "VulnSearch";
    setTimeout(() => $("#inicio input[name=q]").focus(), 0);
    return;
  }
  mostra("resultados");
  document.title = `${estado.q} - VulnSearch`;
  sincronizaFerramentas();
  busca();
}

// ---------------------------------------------------------------- busca
function paramsBusca(e) {
  const p = { q: e.q, pagina: e.pagina, por_pagina: e.por_pagina, site: e.site || undefined,
              cve: e.cve, cwe: e.cwe };
  if (e.modelo) p.modelo = e.modelo;
  for (const k of PARAMS) if (e[k] !== "") p[k] = e[k];
  if (e.explicar) p.explicar = "true";
  return p;
}

async function busca() {
  const minha = ++requisicao;
  carregando(true);
  $("#estatistica").textContent = "";
  let r;
  try {
    r = await api("/api/busca", paramsBusca(estado));
  } catch (err) {
    if (minha !== requisicao) return;
    carregando(false);
    $("#avisos").replaceChildren();
    $("#lista").replaceChildren(el("p", { class: "vazio erro", textContent: "Erro: " + err.message }));
    $("#paginacao").replaceChildren();
    $("#painel").hidden = true;
    return;
  }
  if (minha !== requisicao) return;
  carregando(false);
  ultimaResposta = r;
  guardaHistorico(estado.q);
  desenhaAbas(r);
  desenhaFiltros(r);
  desenhaEstatistica(r);
  desenhaAvisos(r);
  desenhaLista(r);
  desenhaPaginacao(r);
  desenhaPainel(r);
  scrollTo(0, 0);
}

function desenhaAbas(r) {
  const abas = $("#abas");
  const todos = Object.values(r.facetas.sites).reduce((a, b) => a + b, 0);
  const itens = [{ id: "", nome: "Todos", n: todos }];
  for (const s of sites) itens.push({ id: s.id, nome: (FONTES[s.id] || {}).curto || s.nome, n: r.facetas.sites[s.id] || 0 });
  abas.replaceChildren(...itens.map((x) => el("button", {
    type: "button", class: "aba" + (x.id === estado.site ? " ativa" : ""),
    onclick: () => navega({ site: x.id, pagina: 1 }),
  }, x.nome, el("span", { class: "n", textContent: fmt(x.n) }))));
  const ferr = el("button", { type: "button", class: "aba ferr" + ($("#ferramentas").hidden ? "" : " aberta"),
    textContent: "Ferramentas", onclick: () => {
      $("#ferramentas").hidden = !$("#ferramentas").hidden;
      ferr.classList.toggle("aberta", !$("#ferramentas").hidden);
      guarda("vs-ferramentas", !$("#ferramentas").hidden);
    } });
  abas.append(ferr);
}

function desenhaFiltros(r) {
  const caixa = $("#filtros-ativos");
  caixa.replaceChildren();
  for (const tipo of ["cve", "cwe"]) {
    for (const v of r.filtros[tipo]) {
      caixa.append(el("span", { class: "filtro" }, v, el("button", {
        type: "button", "aria-label": "Remover filtro " + v, textContent: "×",
        onclick: () => navega({ [tipo]: estado[tipo].filter((x) => x.toUpperCase() !== v), pagina: 1 }),
      })));
    }
  }
}

function desenhaEstatistica(r) {
  const seg = (r.tempo_ms.total / 1000).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const nomeModelo = (modelos.modelos.find((m) => m.id === r.modelo) || {}).nome || r.modelo;
  let txt = r.pagina > 1 ? `Página ${r.pagina} de aproximadamente ${fmt(r.total)} resultados`
                         : `Aproximadamente ${fmt(r.total)} resultados`;
  txt += ` (${seg} segundos${r.cache ? ", do cache" : ""}) · ${nomeModelo}`;
  $("#estatistica").textContent = r.total ? txt : "";
}

function desenhaAvisos(r) {
  $("#avisos").replaceChildren(...r.avisos.map((a) => el("div", { class: "aviso", textContent: a })));
}

function caminhoUrl(url) {
  try {
    const u = new URL(url);
    const partes = u.pathname.split("/").filter(Boolean).map(decodeURIComponent);
    return { origem: u.origin, resto: partes.length ? " › " + partes.join(" › ") : "" };
  } catch { return { origem: url, resto: "" }; }
}

const FAVICON = (dominio, tamanho = 32) =>
  `https://www.google.com/s2/favicons?domain=${encodeURIComponent(dominio)}&sz=${tamanho}`;

function avatar(site) {
  const f = FONTES[site] || { sigla: site.slice(0, 2).toUpperCase(), cor: "#5f6368" };
  const caixa = el("span", { class: "avatar" });
  const img = el("img", { src: f.icone || FAVICON(site), alt: "", width: 18, height: 18, loading: "lazy",
    referrerPolicy: "no-referrer",
    onerror: () => {
      caixa.replaceChildren(f.sigla);
      caixa.classList.add("sigla");
      caixa.style.background = f.cor;
    } });
  caixa.append(img);
  return caixa;
}

function desenhaLista(r) {
  const lista = $("#lista");
  lista.replaceChildren();
  if (!r.resultados.length) {
    if (r.total) return;
    lista.append(el("div", { class: "vazio" },
      el("p", {}, "Sua pesquisa - ", el("b", { textContent: r.consulta }), " - não encontrou nenhum documento correspondente."),
      el("p", { textContent: "Sugestões:" }),
      el("ul", {},
        el("li", { textContent: "Verifique a ortografia (os documentos estão em inglês)." }),
        el("li", { textContent: "Tente palavras diferentes ou mais gerais." }),
        (estado.site || estado.cve.length || estado.cwe.length) ?
          el("li", {}, el("button", { class: "link", type: "button", textContent: "Remova os filtros",
            onclick: () => navega({ site: "", cve: [], cwe: [], pagina: 1 }) }), ".") : null,
        el("li", { textContent: "Frases entre aspas exigem as palavras em sequência; tente sem as aspas." }))));
    return;
  }
  for (const x of r.resultados) lista.append(desenhaResultado(x));
}

function desenhaResultado(x) {
  const nome = (sites.find((s) => s.id === x.site) || {}).nome || x.site;
  const cam = caminhoUrl(x.url);
  const menu = el("button", { type: "button", class: "res-menu", "aria-label": "Mais opções", textContent: "⋮",
    onclick: (ev) => { ev.stopPropagation(); abreMenu(menu, x); } });
  const div = el("div", { class: "res" },
    el("div", { class: "res-fonte" }, avatar(x.site),
      el("div", { class: "res-origem" },
        el("div", { class: "res-site" }, nome,
          el("span", { class: "escore", textContent: ` · #${x.posicao} · score ${x.escore.toLocaleString("pt-BR", { maximumFractionDigits: 3 })}` })),
        el("div", { class: "res-url", textContent: cam.origem + cam.resto })),
      menu),
    el("h3", {}, el("a", { href: x.url, target: "_blank", rel: "noopener noreferrer" }, segmentos(x.titulo))),
    el("p", { class: "trecho" }, segmentos(x.trecho)));
  if (x.trecho_codigo) div.append(el("pre", {}, segmentos(x.trecho_codigo)));
  const ids = [...x.cves.map((v) => ["cve", v]), ...x.cwes.map((v) => ["cwe", v])];
  if (ids.length) {
    const etq = el("div", { class: "etiquetas" });
    for (const [tipo, v] of ids.slice(0, 6)) {
      etq.append(el("button", { type: "button", class: "etq " + tipo, textContent: v, title: `Filtrar por ${v}`,
        onclick: () => { if (!estado[tipo].includes(v)) navega({ [tipo]: [...estado[tipo], v], pagina: 1 }); } }));
    }
    if (ids.length > 6) etq.append(el("span", { class: "etq mais", textContent: `+${ids.length - 6}` }));
    div.append(etq);
  }
  if (x.explicacao) div.append(desenhaExplicacao(x.explicacao, x.escore));
  return div;
}

function achata(o, pre = "", saida = {}) {
  for (const [k, v] of Object.entries(o)) {
    const chave = pre ? pre + "." + k : k;
    if (v && typeof v === "object" && !Array.isArray(v)) achata(v, k === "campos" ? "" : chave, saida);
    else saida[chave] = v;
  }
  return saida;
}

function num(v) {
  if (typeof v !== "number") return String(v);
  return Number.isInteger(v) ? fmt(v) : v.toLocaleString("pt-BR", { maximumFractionDigits: 4 });
}

function desenhaExplicacao(parcelas, escore) {
  const linhas = parcelas.map((p) => achata(p));
  const chaves = [];
  for (const l of linhas) for (const k of Object.keys(l)) if (!chaves.includes(k)) chaves.push(k);
  const ordem = chaves.filter((k) => k !== "palavra" && k !== "parcela");
  const cab = ["palavra", ...ordem, "parcela"].filter((k) => chaves.includes(k));
  const tabela = el("table", { class: "tabela" },
    el("tr", {}, ...cab.map((k) => el("th", { textContent: k }))),
    ...linhas.map((l) => el("tr", {}, ...cab.map((k) => el("td", {
      class: typeof l[k] === "number" ? "num" : "", textContent: l[k] === undefined ? "" : num(l[k]) })))));
  return el("details", { class: "explica" },
    el("summary", { textContent: `Por que este resultado? (score ${num(escore)})` }), tabela);
}

let menuAberto = null;
function fechaMenu() { if (menuAberto) { menuAberto.remove(); menuAberto = null; } }
function abreMenu(botao, x) {
  const ja = menuAberto && menuAberto.parentNode === botao;
  fechaMenu();
  if (ja) return;
  menuAberto = el("div", { class: "menu", onclick: (ev) => ev.stopPropagation() },
    el("button", { type: "button", textContent: "Ver cópia em cache", onclick: () => { fechaMenu(); navega({ doc: String(x.id) }); } }),
    el("a", { href: x.url, target: "_blank", rel: "noopener noreferrer", textContent: "Abrir página original" }),
    el("button", { type: "button", textContent: "Copiar link", onclick: () => {
      fechaMenu(); navigator.clipboard && navigator.clipboard.writeText(x.url).catch(() => {}); } }));
  menuAberto.style.right = "0";
  menuAberto.style.top = "100%";
  botao.append(menuAberto);
}
document.addEventListener("click", fechaMenu);

function desenhaPaginacao(r) {
  const nav = $("#paginacao");
  nav.replaceChildren();
  if (r.paginas <= 1) return;
  const ini = Math.max(1, Math.min(r.pagina - 5, r.paginas - 9));
  const fim = Math.min(r.paginas, ini + 9);
  const vai = (p) => (ev) => { ev.preventDefault(); navega({ pagina: p }); };
  const letra = (txt, cls, rotulo, pagina) => {
    const filhos = [el("span", { class: cls, textContent: txt }), el("small", { textContent: rotulo })];
    if (!pagina) return el("span", { class: "letra" }, ...filhos);
    return el("a", { class: "letra", href: urlDoEstado({ ...estado, pagina, doc: "" }), onclick: vai(pagina) }, ...filhos);
  };
  const pag = el("div", { class: "pag" });
  const v = letra("V", "pv", r.pagina > 1 ? "‹ Anterior" : " ", r.pagina > 1 ? r.pagina - 1 : 0);
  v.classList.add("seta-esq");
  pag.append(v);
  for (let p = ini; p <= fim; p++) {
    const atual = p === r.pagina;
    const a = letra("u", atual ? "pv" : "pv apagado", String(p), atual ? 0 : p);
    if (atual) a.classList.add("atual");
    pag.append(a);
  }
  "lnSearch".split("").forEach((c, i) => {
    const ultima = i === 7;
    const tem = ultima && r.pagina < r.paginas;
    const l = letra(c, i < 2 ? "pv" : "ps", tem ? "Próxima ›" : " ", tem ? r.pagina + 1 : 0);
    if (ultima) l.classList.add("seta-dir");
    pag.append(l);
  });
  nav.append(pag);
}

function desenhaPainel(r) {
  const painel = $("#painel");
  const m = (estado.q.match(/\b(CVE-\d{4}-\d{4,}|CWE-\d+)\b/i) || [])[1]
         || r.filtros.cve[0] || r.filtros.cwe[0];
  if (!m || !r.total) { painel.hidden = true; return; }
  const id = m.toUpperCase();
  const cve = id.startsWith("CVE");
  const fac = Object.entries(r.facetas.sites);
  const max = Math.max(1, ...fac.map(([, n]) => n));
  const dl = el("dl");
  for (const [s, n] of fac) {
    dl.append(el("dt", { textContent: (FONTES[s] || {}).curto || s }),
      el("dd", {}, el("div", { class: "barra" }, el("i", { style: `width:${Math.round(140 * n / max)}px` }),
        el("span", { textContent: fmt(n) }))));
  }
  const numero = id.split("-").slice(1).join("-");
  const links = cve
    ? [["NVD (NIST)", `https://nvd.nist.gov/vuln/detail/${id}`], ["CVE.org", `https://www.cve.org/CVERecord?id=${id}`]]
    : [["Definição no MITRE", `https://cwe.mitre.org/data/definitions/${numero}.html`]];
  painel.replaceChildren(
    el("h2", { textContent: id }),
    el("p", { class: "sub", textContent: cve ? "Identificador de vulnerabilidade (CVE)" : "Tipo de fraqueza (CWE)" }),
    el("div", { textContent: "Documentos por fonte nesta pesquisa:" }),
    dl,
    el("div", { class: "ext" }, ...links.map(([t, u]) => el("a", { href: u, target: "_blank", rel: "noopener noreferrer", textContent: t + " ↗" })),
      !r.filtros[cve ? "cve" : "cwe"].includes(id) && el("button", { type: "button", class: "link", style: "text-align:left",
        textContent: `Só documentos que citam ${id}`,
        onclick: () => navega({ [cve ? "cve" : "cwe"]: [...estado[cve ? "cve" : "cwe"], id], pagina: 1 }) })));
  painel.hidden = false;
}

// ---------------------------------------------------------------- ferramentas
function sincronizaFerramentas() {
  const sel = $("#modelo");
  const modelo = estado.modelo || modelos.padrao;
  sel.value = modelo;
  $("#explicar").checked = estado.explicar;
  const pp = $("#por-pagina");
  if (![...pp.options].some((o) => o.value === String(estado.por_pagina))) {
    pp.append(el("option", { textContent: String(estado.por_pagina) }));
  }
  pp.value = String(estado.por_pagina);
  const m = modelos.modelos.find((x) => x.id === modelo);
  const caixa = $("#parametros");
  caixa.replaceChildren();
  if (m) {
    for (const [k, padrao] of Object.entries(m.parametros)) {
      const inp = el("input", { type: "number", step: PASSO_PARAM[k] || 0.1, min: 0, value: estado[k] !== "" ? estado[k] : padrao,
        onchange: () => {
          const v = inp.value.trim();
          navega({ [k]: v === "" || Number(v) === padrao ? "" : v, pagina: 1 });
        } });
      caixa.append(el("label", { title: `padrão ${padrao}` }, ROTULO_PARAM[k] || k, inp));
    }
  }
  const mudou = estado.modelo || estado.explicar || estado.por_pagina !== 10 || PARAMS.some((k) => estado[k] !== "");
  if (mudou || le("vs-ferramentas", false)) $("#ferramentas").hidden = false;
}

function iniciaFerramentas() {
  const sel = $("#modelo");
  for (const m of modelos.modelos) {
    sel.append(el("option", { value: m.id, textContent: m.nome, title: m.descricao }));
  }
  sel.addEventListener("change", () => {
    const limpa = Object.fromEntries(PARAMS.map((k) => [k, ""]));
    navega({ ...limpa, modelo: sel.value === modelos.padrao ? "" : sel.value, pagina: 1 });
  });
  $("#explicar").addEventListener("change", (e) => navega({ explicar: e.target.checked }));
  $("#por-pagina").addEventListener("change", (e) => navega({ por_pagina: parseInt(e.target.value, 10), pagina: 1 }));
  $("#restaurar").addEventListener("click", () => {
    navega({ ...Object.fromEntries(PARAMS.map((k) => [k, ""])), modelo: "", explicar: false, por_pagina: 10, pagina: 1 });
  });
}

// ---------------------------------------------------------------- cópia em cache
function termosDaConsulta(q) {
  const termos = [];
  const sem = q.replace(/(^|\s)(-|NOT\s+)("[^"]*"|\S+)/g, " ");
  for (let t of sem.replace(/"/g, " ").split(/\s+/)) {
    t = t.replace(/^codigo:/i, "").replace(/^[^\w]+|[^\w]+$/g, "");
    if (t.length < 2 || /^(the|of|and|or|in|to|a|an|for|on|with|is)$/i.test(t)) continue;
    termos.push(t.length > 5 && /^[a-z]+$/i.test(t) ? t.slice(0, -2) : t);
  }
  return [...new Set(termos)];
}

function destacaTexto(texto, termos) {
  const frag = document.createDocumentFragment();
  if (!termos.length || !texto) { frag.append(texto || ""); return frag; }
  const esc = termos.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"));
  const re = new RegExp(`(\\b(?:${esc.join("|")})[\\w-]*)`, "gi");
  texto.split(re).forEach((parte, i) => frag.append(i % 2 ? el("mark", { textContent: parte }) : document.createTextNode(parte)));
  return frag;
}

const ROTULOS_FICHA = ["EDB-ID", "CVE", "EDB Verified", "Author", "Type", "Exploit", "Platform", "Date",
  "Vulnerable App", "Tags", "Advisory/Source"];
const VALORES_SEM_INFORMACAO = new Set(["/", "Link", "N/A"]);

function fichaExploitDb(texto, titulo) {
  const linhas = (texto || "").split("\n").map((l) => l.trim());
  const rotulos = new Set(ROTULOS_FICHA.map((r) => r + ":"));
  let k = linhas[0] && linhas[0] === (titulo || "").trim() ? 1 : 0;
  if (linhas[k] !== "EDB-ID:") return null;
  const pares = [];
  while (k < linhas.length && rotulos.has(linhas[k])) {
    const rotulo = linhas[k].slice(0, -1);
    k++;
    const valores = [];
    while (k < linhas.length && !rotulos.has(linhas[k])) {
      if (rotulo === "Advisory/Source" && valores.length) break;
      if (linhas[k]) valores.push(linhas[k]);
      k++;
    }
    const uteis = valores.filter((v) => !VALORES_SEM_INFORMACAO.has(v));
    if (uteis.length) pares.push([rotulo, uteis]);
    if (rotulo === "Advisory/Source") break;
  }
  return { pares, resto: linhas.slice(k).join("\n").trim() };
}

function desenhaFicha(pares, termos) {
  const dl = el("dl", { class: "ficha" });
  for (const [rotulo, valores] of pares) {
    const dd = el("dd");
    valores.forEach((v, i) => {
      if (i) dd.append(", ");
      dd.append(destacaTexto(rotulo === "CVE" && /^\d{4}-\d+$/.test(v) ? "CVE-" + v : v, termos));
    });
    dl.append(el("dt", { textContent: rotulo }), dd);
  }
  return dl;
}

async function abreDocumento() {
  const doc = $("#cache-doc");
  doc.replaceChildren();
  carregando(true);
  let d;
  try {
    d = await api("/api/documento/" + encodeURIComponent(estado.doc));
  } catch (err) {
    carregando(false);
    doc.append(el("p", { class: "erro", textContent: "Erro: " + err.message }));
    return;
  }
  carregando(false);
  document.title = `${d.titulo} - cópia do VulnSearch`;
  const url = $("#cache-url");
  url.href = d.url; url.textContent = d.url;
  const termos = termosDaConsulta(estado.q);
  const idLinks = [...d.cves, ...d.cwes].map((x) => el("a", { href: urlDoEstado({ q: x, cve: [], cwe: [], site: "", pagina: 1 }), textContent: x,
    onclick: (ev) => { ev.preventDefault(); navega({ q: x, site: "", cve: [], cwe: [], pagina: 1 }); } }));
  const meta = el("div", { class: "meta" }, `${d.nome_site} · documento ${d.id} · ${fmt(d.n_termos_texto)} termos no texto`
    + (d.n_termos_codigo ? `, ${fmt(d.n_termos_codigo)} no código` : ""));
  doc.append(el("div", {}, avatar(d.site)), el("h1", {}, destacaTexto(d.titulo, termos)), meta);
  if (idLinks.length) {
    const p = el("p", {}, "Identificadores: ");
    idLinks.forEach((a, i) => { if (i) p.append(", "); p.append(a); });
    doc.append(p);
  }
  if (d.descricao) doc.append(el("h2", { textContent: "Descrição" }), el("div", { class: "texto" }, destacaTexto(d.descricao, termos)));
  if (d.palavras_chave) doc.append(el("p", { class: "meta", textContent: "Palavras-chave: " + d.palavras_chave }));
  const ficha = d.site === "www.exploit-db.com" ? fichaExploitDb(d.texto, d.titulo) : null;
  if (ficha && ficha.pares.length) doc.append(desenhaFicha(ficha.pares, termos));
  const corpo = ficha ? ficha.resto : d.texto;
  if (corpo) doc.append(el("h2", { textContent: "Texto" }), el("div", { class: "texto" }, destacaTexto(corpo, termos)));
  if (d.codigo) {
    doc.append(el("h2", { textContent: "Código" }), el("pre", {}, destacaTexto(d.codigo, termos)));
    if (d.codigo_truncado) {
      doc.append(el("p", { class: "meta", textContent: `Código cortado em 20.000 de ${fmt(d.tamanho_codigo)} caracteres; a página original tem o restante.` }));
    }
  }
  scrollTo(0, 0);
}

// ---------------------------------------------------------------- caixa de busca e sugestões
function historico() { return le("vs-historico", []); }
function guardaHistorico(q) {
  const h = historico().filter((x) => x.toLowerCase() !== q.toLowerCase());
  h.unshift(q);
  guarda("vs-historico", h.slice(0, 15));
}

const ICO_RELOGIO = '<svg viewBox="0 0 24 24"><path d="M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20zm0 18a8 8 0 1 1 0-16 8 8 0 0 1 0 16zm.5-13H11v6l5.2 3.2.8-1.3-4.5-2.7z"/></svg>';
const ICO_LUPA = '<svg viewBox="0 0 24 24"><path d="M15.5 14h-.8l-.3-.3A6.5 6.5 0 1 0 9.5 16a6.5 6.5 0 0 0 4.2-1.6l.3.3v.8l5 5 1.5-1.5zm-6 0a4.5 4.5 0 1 1 0-9 4.5 4.5 0 0 1 0 9z"/></svg>';
const EXEMPLOS = ["log4j", "remote code execution", "sql injection wordpress", "cross-site scripting", "buffer overflow",
  "privilege escalation linux", "CVE-2021-44228", "CWE-79", "\"use-after-free\"", "codigo:strcpy", "drupal access bypass",
  "joomla xss", "path traversal", "deserialization java", "csrf"];

function fechaSugestoes() {
  for (const u of $$(".sugestoes")) { u.hidden = true; u.replaceChildren(); }
  for (const c of $$(".caixa")) c.classList.remove("aberta");
}

function mostraSugestoes(input) {
  const caixa = input.closest(".caixa");
  const ul = $(".sugestoes", caixa);
  const v = input.value.trim().toLowerCase();
  const hist = historico().filter((x) => !v || x.toLowerCase().startsWith(v) && x.toLowerCase() !== v);
  const ex = v ? EXEMPLOS.filter((x) => x.toLowerCase().includes(v) && x.toLowerCase() !== v && !hist.includes(x)) : [];
  const itens = [...hist.slice(0, 6).map((t) => [t, true]), ...ex.slice(0, 8 - Math.min(6, hist.length)).map((t) => [t, false])];
  ul.replaceChildren();
  if (!itens.length) { fechaSugestoes(); return; }
  for (const [t, doHist] of itens) {
    const li = el("li", { role: "option", onmousedown: (ev) => { ev.preventDefault(); input.value = t; enviar(input.form); } });
    li.insertAdjacentHTML("afterbegin", doHist ? ICO_RELOGIO : ICO_LUPA);
    li.append(el("span", { textContent: t }));
    if (doHist) {
      li.append(el("button", { type: "button", class: "link tirar", textContent: "Remover",
        onmousedown: (ev) => { ev.preventDefault(); ev.stopPropagation();
          guarda("vs-historico", historico().filter((x) => x !== t)); mostraSugestoes(input); } }));
    }
    ul.append(li);
  }
  ul.hidden = false;
  caixa.classList.add("aberta");
}

function moveSugestao(input, passo) {
  const itens = $$(".sugestoes li", input.closest(".caixa"));
  if (!itens.length) return false;
  let i = itens.findIndex((li) => li.classList.contains("ativa"));
  itens.forEach((li) => li.classList.remove("ativa"));
  i = (i + passo + itens.length + 1) % (itens.length + 1);
  if (i === itens.length) { input.value = input.dataset.digitado || ""; return true; }
  itens[i].classList.add("ativa");
  input.value = $("span", itens[i]).textContent;
  return true;
}

function atualizaLimpar() {
  for (const f of $$("[data-form]")) $(".limpar", f).hidden = !$("input[name=q]", f).value;
}

function enviar(form) {
  const q = $("input[name=q]", form).value.trim();
  fechaSugestoes();
  if (!q) return;
  $("input[name=q]", form).blur();
  navega({ q, pagina: 1, cve: [], cwe: [] });
}

async function sorte(form) {
  const q = $("input[name=q]", form).value.trim();
  if (!q) return;
  carregando(true);
  try {
    const r = await api("/api/busca", { q, por_pagina: 1 });
    if (r.resultados.length) { location.href = r.resultados[0].url; return; }
    navega({ q, pagina: 1 });
  } catch (err) {
    navega({ q, pagina: 1 });
  } finally { carregando(false); }
}

function iniciaFormularios() {
  for (const form of $$("[data-form]")) {
    const input = $("input[name=q]", form);
    form.addEventListener("submit", (ev) => { ev.preventDefault(); enviar(form); });
    input.addEventListener("input", () => { input.dataset.digitado = input.value; atualizaLimpar(); mostraSugestoes(input); });
    input.addEventListener("focus", () => { input.dataset.digitado = input.value; });
    input.addEventListener("mousedown", () => { if ($(".sugestoes", input.closest(".caixa")).hidden) setTimeout(() => mostraSugestoes(input), 0); });
    input.addEventListener("blur", () => setTimeout(fechaSugestoes, 100));
    input.addEventListener("keydown", (ev) => {
      if (ev.key === "ArrowDown" || ev.key === "ArrowUp") {
        if (moveSugestao(input, ev.key === "ArrowDown" ? 1 : -1)) ev.preventDefault();
      } else if (ev.key === "Escape") fechaSugestoes();
    });
    $(".limpar", form).addEventListener("click", () => { input.value = ""; atualizaLimpar(); input.focus(); });
    const b = $("[data-acao=sorte]", form);
    if (b) b.addEventListener("click", () => sorte(form));
  }
  document.addEventListener("keydown", (ev) => {
    if (ev.key === "/" && !/^(INPUT|SELECT|TEXTAREA)$/.test(document.activeElement.tagName) && !$("#janela").open) {
      const i = $("section:not([hidden]) input[name=q]");
      if (i) { ev.preventDefault(); i.focus(); i.select(); }
    }
  });
  for (const a of $$(".experimente a")) {
    a.addEventListener("click", (ev) => {
      ev.preventDefault();
      navega({ q: new URL(a.href).searchParams.get("q"), pagina: 1, cve: [], cwe: [] });
    });
  }
  $("#cache-voltar").addEventListener("click", (ev) => {
    ev.preventDefault();
    if (history.state && history.state.deResultados) history.back(); else navega({ doc: "" });
  });
}

// ---------------------------------------------------------------- janelas "sobre" e "sintaxe"
async function janelaSobre() {
  const corpo = $("#janela-corpo");
  corpo.replaceChildren(el("h2", { textContent: "Sobre o VulnSearch" }), el("p", { textContent: "Carregando…" }));
  $("#janela").showModal();
  try {
    const e = await api("/api/estatisticas");
    const n = (rotulo, v) => el("div", { class: "numero" }, el("b", { textContent: v }), el("span", { textContent: rotulo }));
    const data = e.data_indexacao ? new Date(e.data_indexacao).toLocaleDateString("pt-BR") : "—";
    corpo.replaceChildren(
      el("h2", { textContent: "Sobre o VulnSearch" }),
      el("p", { textContent: "Buscador vertical de vulnerabilidades de software e hardware. Coleta, índice invertido e modelos de " +
        "ranqueamento próprios, sem bibliotecas de busca nem banco de dados." }),
      el("div", { class: "numeros" },
        n("documentos", fmt(e.documentos)), n("termos no vocabulário", fmt(e.vocabulario.total)),
        n("ocorrências", fmt(e.ocorrencias)), n("MB de índice", e.indice_mb.total.toLocaleString("pt-BR")),
        n("documentos com CVE", fmt(e.textos.docs_com_cve)), n("indexado em", data)),
      el("table", { class: "tabela" },
        el("tr", {}, el("th", { textContent: "Fonte" }), el("th", { textContent: "Documentos" })),
        ...sites.map((s) => el("tr", {}, el("td", { textContent: s.nome }), el("td", { class: "num", textContent: fmt(s.documentos) })))));
  } catch (err) {
    corpo.append(el("p", { class: "erro", textContent: "Erro: " + err.message }));
  }
}

function janelaSintaxe() {
  $("#janela-corpo").replaceChildren($("#tpl-sintaxe").content.cloneNode(true));
  $("#janela").showModal();
}

// ---------------------------------------------------------------- início
async function inicia() {
  for (const l of $$(".logo")) desenhaLogo(l);
  $(".logo-pequeno").addEventListener("click", (ev) => { ev.preventDefault(); navega({ q: "", cve: [], cwe: [], site: "", pagina: 1 }); });
  for (const a of $$("[data-acao=sobre]")) a.addEventListener("click", (ev) => { ev.preventDefault(); janelaSobre(); });
  for (const a of $$("[data-acao=sintaxe]")) a.addEventListener("click", (ev) => { ev.preventDefault(); janelaSintaxe(); });
  iniciaFormularios();
  const topo = $(".topo");
  const alturaTopo = () => document.documentElement.style.setProperty("--altura-topo", topo.offsetHeight + "px");
  if ("ResizeObserver" in window) new ResizeObserver(alturaTopo).observe(topo);
  window.addEventListener("resize", alturaTopo);
  try {
    [modelos, { sites }] = await Promise.all([api("/api/modelos"), api("/api/sites")]);
  } catch (err) {
    mostra("inicio");
    $(".slogan").textContent = "Servidor indisponível: " + err.message;
    $(".slogan").classList.add("erro");
    return;
  }
  iniciaFerramentas();
  $("#rodape-fontes").textContent = sites.map((s) => s.nome).join(" · ");
  window.addEventListener("popstate", renderiza);
  renderiza();
}

inicia();
