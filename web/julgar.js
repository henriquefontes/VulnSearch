"use strict";

// ---------------------------------------------------------------- utilidades
const $ = (s) => document.querySelector(s);
const NUM = new Intl.NumberFormat("pt-BR");
const NOMES = { "0": "não serve", "1": "relacionado", "2": "trata do assunto" };

function el(tag, props = {}, ...filhos) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props)) {
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else if (k in e) e[k] = v;
    else e.setAttribute(k, v);
  }
  for (const f of filhos) if (f != null && f !== false && f !== "") e.append(f);
  return e;
}

function segmentos(segs) {
  const frag = document.createDocumentFragment();
  for (const s of segs || []) frag.append(s.destaque ? el("mark", { textContent: s.texto }) : document.createTextNode(s.texto));
  return frag;
}

function guarda(k, v) { try { localStorage.setItem(k, v); } catch { } }
function le(k) { try { return localStorage.getItem(k) || ""; } catch { return ""; } }

async function api(caminho, opcoes = {}) {
  const r = await fetch(caminho, opcoes);
  let js;
  try { js = await r.json(); } catch { throw new Error(`Resposta inválida do servidor (${r.status}).`); }
  if (!r.ok) throw new Error(js.erro || r.statusText);
  return js;
}

// ---------------------------------------------------------------- estado
let resumo = null;
let consulta = null;   // {id, consulta, documentos}
let atual = 0;

const avaliador = () => $("#avaliador").value.trim();

function aviso(texto) {
  const a = $("#aviso");
  a.textContent = texto || "";
  a.hidden = !texto;
}

function progresso() {
  if (!resumo) return;
  const c = consulta && resumo.consultas.find((x) => x.id === consulta.id);
  const pct = resumo.total ? (100 * resumo.julgados / resumo.total) : 0;
  $("#barra").style.width = pct.toFixed(1) + "%";
  let t = `${NUM.format(resumo.julgados)} de ${NUM.format(resumo.total)} documentos julgados`;
  if (c) t += ` · ${c.id}: ${c.julgados} de ${c.total}` + (avaliador() ? ` · seus nesta consulta: ${c.meus}` : "");
  $("#progresso").textContent = t;
  const sel = $("#consulta");
  for (const o of sel.options) {
    const x = resumo.consultas.find((y) => y.id === o.value);
    if (x) o.textContent = `${x.id} · ${x.consulta} — ${x.julgados}/${x.total}`;
  }
}

// ---------------------------------------------------------------- carga
async function carregaResumo() {
  resumo = await api("/api/julgamento?avaliador=" + encodeURIComponent(avaliador()));
  const sel = $("#consulta");
  if (sel.disabled) {
    sel.replaceChildren(...resumo.consultas.map((c) => el("option", { value: c.id })));
    const pedida = new URLSearchParams(location.search).get("consulta") || le("vs-julgar-consulta");
    if (resumo.consultas.some((c) => c.id === pedida)) sel.value = pedida;
    sel.disabled = false;
    $("#criterio").replaceChildren(...resumo.criterio.flatMap((c) => [
      el("dt", { textContent: `${c.valor} · ${c.nome}` }), el("dd", { textContent: c.descricao })]));
  }
  progresso();
}

async function carregaConsulta() {
  const cid = $("#consulta").value;
  guarda("vs-julgar-consulta", cid);
  const c = resumo.consultas.find((x) => x.id === cid);
  $("#pergunta").replaceChildren("Consulta ", el("b", { textContent: c ? c.consulta : cid }),
    ": o documento ajuda quem buscou isso?");
  if (!avaliador()) {
    consulta = null;
    $("#lista").replaceChildren();
    $("#avaliador").classList.add("falta");
    aviso("Digite seu nome no campo Avaliador para começar. Ele vai junto com cada julgamento.");
    progresso();
    return;
  }
  $("#avaliador").classList.remove("falta");
  aviso("");
  $("#carregando").hidden = false;
  try {
    consulta = await api(`/api/julgamento/${encodeURIComponent(cid)}?avaliador=${encodeURIComponent(avaliador())}`);
  } catch (e) {
    aviso("Erro: " + e.message);
    return;
  } finally {
    $("#carregando").hidden = true;
  }
  desenhaLista();
  const primeiro = consulta.documentos.findIndex((d) => !d.relevante);
  seleciona(primeiro >= 0 ? primeiro : 0, false);
  progresso();
}

// ---------------------------------------------------------------- lista
function urlCache(d) {
  return `/?q=${encodeURIComponent(consulta.consulta)}&doc=${d.id}`;
}

function desenhaLista() {
  const n = consulta.documentos.length;
  $("#lista").replaceChildren(...consulta.documentos.map((d, i) => {
    const estado = el("span", { class: "j-estado" });
    const notas = ["0", "1", "2"].map((v) => el("button", {
      type: "button", class: `j-nota n${v}`, textContent: `${v} · ${NOMES[v]}`,
      title: `Atalho: tecla ${v}`, "aria-pressed": String(d.relevante === v),
      onclick: () => { seleciona(i, false); julga(i, v, false); } }));
    const obs = el("input", { class: "j-obs", type: "text", maxLength: 500, value: d.observacao,
      placeholder: "observação (opcional)",
      onchange: () => { if (d.relevante) julga(i, d.relevante, false); else estado.textContent = "julgue para salvar a observação"; } });
    const li = el("li", { class: "j-doc" + (d.relevante ? " v" + d.relevante : ""), id: "d" + i,
      onclick: (ev) => { if (!ev.target.closest("a, button, input")) seleciona(i, false); } },
      el("div", { class: "j-cab" }, el("span", { class: "j-num", textContent: `${i + 1}/${n}` }),
        el("span", { textContent: d.nome_site }),
        d.julgado_por_outra_pessoa ? el("span", { class: "j-outro",
          textContent: "outra pessoa já julgou este documento: o seu julgamento vai para a segunda avaliação (concordância)" }) : null),
      el("h3", {}, el("a", { href: d.url, target: "_blank", rel: "noopener noreferrer" }, segmentos(d.titulo))),
      el("a", { class: "j-url", href: d.url, target: "_blank", rel: "noopener noreferrer", textContent: d.url }),
      el("p", { class: "trecho" }, segmentos(d.trecho)),
      d.trecho_codigo ? el("pre", {}, segmentos(d.trecho_codigo)) : null,
      el("div", { class: "j-acoes" }, ...notas, obs,
        d.id != null ? el("a", { class: "j-cache", href: urlCache(d), target: "_blank", rel: "noopener",
          textContent: "Abrir cópia em cache ↗" }) : null,
        el("button", { type: "button", class: "link", textContent: "desfazer",
          title: "Apaga o seu julgamento deste documento", onclick: () => julga(i, "", false) }),
        estado));
    li._estado = estado; li._obs = obs; li._notas = notas;
    return li;
  }));
}

function seleciona(i, rolar = true) {
  if (!consulta || !consulta.documentos.length) return;
  atual = Math.max(0, Math.min(consulta.documentos.length - 1, i));
  document.querySelectorAll(".j-doc.atual").forEach((e) => e.classList.remove("atual"));
  const li = $("#d" + atual);
  li.classList.add("atual");
  if (rolar) li.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

async function julga(i, valor, avancar) {
  const d = consulta.documentos[i];
  const li = $("#d" + i);
  if (!avaliador()) { $("#avaliador").focus(); $("#avaliador").classList.add("falta"); return; }
  li._estado.classList.remove("erro");
  li._estado.textContent = "salvando…";
  try {
    const r = await api(`/api/julgamento/${encodeURIComponent(consulta.id)}`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: d.url, relevante: valor, observacao: li._obs.value, avaliador: avaliador() }) });
    d.relevante = valor;
    d.observacao = valor ? li._obs.value : "";
    if (!valor) li._obs.value = "";
    li.className = "j-doc" + (valor ? " v" + valor : "") + (i === atual ? " atual" : "");
    li._notas.forEach((b, k) => b.setAttribute("aria-pressed", String(String(k) === valor)));
    li._estado.textContent = !valor ? "desfeito" : r.arquivo === "principal" ? "salvo" : "salvo (2ª avaliação)";
    resumo.julgados = r.julgados;
    resumo.total = r.total;
    const k = resumo.consultas.findIndex((x) => x.id === r.consulta.id);
    if (k >= 0) resumo.consultas[k] = r.consulta;
    progresso();
    if (avancar) {
      const docs = consulta.documentos;
      let prox = -1;
      for (let s = 1; s <= docs.length; s++) {
        const j = (i + s) % docs.length;
        if (!docs[j].relevante) { prox = j; break; }
      }
      if (prox >= 0) seleciona(prox);
      else { seleciona(Math.min(i + 1, docs.length - 1)); aviso("Todos os documentos desta consulta foram julgados por você. Obrigado!"); }
    }
  } catch (e) {
    li._estado.classList.add("erro");
    li._estado.textContent = "erro: " + e.message;
  }
}

// ---------------------------------------------------------------- teclado
document.addEventListener("keydown", (ev) => {
  const alvo = ev.target;
  if (alvo.matches("input, select, textarea")) {
    if (ev.key === "Escape" || (ev.key === "Enter" && alvo.classList.contains("j-obs"))) alvo.blur();
    return;
  }
  if (!consulta || ev.ctrlKey || ev.metaKey || ev.altKey) return;
  if (["0", "1", "2"].includes(ev.key)) { ev.preventDefault(); julga(atual, ev.key, true); }
  else if (ev.key === "ArrowDown" || ev.key === "ArrowRight") { ev.preventDefault(); seleciona(atual + 1); }
  else if (ev.key === "ArrowUp" || ev.key === "ArrowLeft") { ev.preventDefault(); seleciona(atual - 1); }
  else if (ev.key === "c") {
    const d = consulta.documentos[atual];
    if (d && d.id != null) window.open(urlCache(d), "_blank", "noopener");
  }
});

// ---------------------------------------------------------------- início
async function inicia() {
  const logo = $(".logo");
  logo.append(el("span", { class: "marca" }, el("span", { class: "vuln", textContent: "Vuln" }),
    el("span", { class: "search", textContent: "Search" })));
  $("#avaliador").value = le("vs-avaliador");
  let espera = null;
  $("#avaliador").addEventListener("input", () => {
    clearTimeout(espera);
    espera = setTimeout(async () => { guarda("vs-avaliador", avaliador()); await carregaResumo(); await carregaConsulta(); }, 500);
  });
  $("#consulta").addEventListener("change", carregaConsulta);
  try {
    await carregaResumo();
  } catch (e) {
    aviso("Servidor indisponível: " + e.message);
    return;
  }
  await carregaConsulta();
}

inicia();
