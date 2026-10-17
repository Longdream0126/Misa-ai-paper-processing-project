/* Misa's AI Paper Processing Project — front-end (vanilla JS, no build step). */

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const ESC = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ESC[c]);
const pct = (x) => `${Math.round(x * 100)}%`;

const COLOR = { good: "#4fd1b0", mid: "#f2b544", bad: "#f2606a", mute: "#8896a8" };

const scoreColor = (s) => (s >= 70 ? COLOR.bad : s >= 40 ? COLOR.mid : COLOR.good);
const subColor = (x) => (x >= 0.66 ? COLOR.bad : x <= 0.33 ? COLOR.good : COLOR.mid);

const state = {
  locale: "en",
  strings: {},
  samples: [],
  lastAnalyze: null,
  lastHumanize: null,
  lastInvisible: null,
  lastWatermark: null,
  lastFile: null,
  lastFileRaw: null,
};

/* ------------------------------------------------------------------ i18n */

function t(key, vars) {
  let s = state.strings[key] ?? key;
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, v);
  return s;
}

function applyI18n() {
  $$("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  $$("[data-i18n-ph]").forEach((el) => { el.placeholder = t(el.dataset.i18nPh); });
  $$("[data-i18n-title]").forEach((el) => { el.title = t(el.dataset.i18nTitle); });
  const made = $("#foot-made");
  if (made) made.textContent = `${t("app.made_by")} · v0.1`;
  document.documentElement.lang = state.locale;
  updateCounters();
}

function updateCounters() {
  const n = (v) => v.replace(/\s/g, "").length;
  $("#counter").textContent = t("analyze.count", { n: n($("#input").value) });
  $("#h-counter").textContent = t("analyze.count", { n: n($("#h-input").value) });
  $("#m-counter").textContent = t("analyze.count", { n: n($("#m-input").value) });
}

async function loadStrings(locale) {
  const res = await fetch(`/api/i18n?locale=${encodeURIComponent(locale)}`);
  const data = await res.json();
  state.locale = data.locale;
  state.strings = data.strings;
  const sel = $("#lang-select");
  sel.innerHTML = "";
  for (const code of data.locales) {
    const opt = document.createElement("option");
    opt.value = code;
    opt.textContent = data.names[code];
    if (code === data.locale) opt.selected = true;
    sel.appendChild(opt);
  }
  applyI18n();
}

function currentLocale() {
  const q = new URLSearchParams(location.search).get("lang");
  if (q) return q;
  return localStorage.getItem("misa-locale") || navigator.language || "en";
}

async function setLocale(locale) {
  localStorage.setItem("misa-locale", locale);
  const url = new URL(location.href);
  url.searchParams.set("lang", locale);
  history.replaceState(null, "", url);
  await loadStrings(locale);
  if (state.lastAnalyze) renderAnalyze(state.lastAnalyze);
  if (state.lastHumanize) renderHumanize(state.lastHumanize);
  if (state.lastInvisible) renderInvisible(state.lastInvisible);
  if (state.lastWatermark) renderWatermark(state.lastWatermark);
  if (state.lastFile) renderFileReport(state.lastFile, $("#marks-result"));
}

/* ------------------------------------------------------------------ http */

async function api(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ locale: state.locale, ...(body || {}) }),
  });
  let data = null;
  try { data = await res.json(); } catch { throw new Error(`HTTP ${res.status}`); }
  if (!res.ok) throw new Error(data && data.error ? data.error : `HTTP ${res.status}`);
  return data;
}

function withLoading(btn, task) {
  if (!btn) return Promise.resolve().then(task);
  btn.classList.add("is-loading");
  btn.disabled = true;
  return Promise.resolve().then(task).finally(() => {
    btn.classList.remove("is-loading");
    btn.disabled = false;
  });
}

function errorCard(err) {
  return `<div class="warnbox"><p><strong>${esc(err.message || err)}</strong></p></div>`;
}

/* ------------------------------------------------------------------ tabs */

$$(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    $$(".tab").forEach((x) => x.classList.toggle("is-active", x === tab));
    $$(".panel").forEach((p) => p.classList.toggle("is-active", p.id === `panel-${tab.dataset.tab}`));
  });
});

$("#lang-select").addEventListener("change", (e) => setLocale(e.target.value));

["#input", "#h-input", "#m-input"].forEach((sel) => {
  $(sel).addEventListener("input", updateCounters);
});

["#btn-fill-humanize", "#btn-fill-marks"].forEach((id, i) => {
  $(id).addEventListener("click", () => {
    const target = i === 0 ? $("#h-input") : $("#m-input");
    target.value = $("#input").value;
    updateCounters();
    target.focus();
  });
});

/* ------------------------------------------------------------------ samples */

async function loadSamples() {
  try {
    const res = await fetch("/api/samples");
    const data = await res.json();
    state.samples = data.samples || [];
    const sel = $("#sample-select");
    state.samples.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s.name;
      opt.textContent = `${s.kind === "ai" ? "🤖" : "🙂"} ${s.label}`;
      sel.appendChild(opt);
    });
    sel.addEventListener("change", () => {
      const hit = state.samples.find((s) => s.name === sel.value);
      if (!hit) return;
      $("#input").value = hit.text.trim();
      updateCounters();
      runAnalyze();
    });
    applyDeepLink();
  } catch { /* samples are optional */ }
}

function applyDeepLink() {
  const params = new URLSearchParams(location.search);
  const tab = params.get("tab");
  const want = params.get("sample");
  const run = params.get("run");
  if (tab) { const b = $(`.tab[data-tab="${tab}"]`); if (b) b.click(); }
  const hit = want ? state.samples.find((s) => s.name === want) : null;
  if (hit) {
    const text = hit.text.trim();
    $("#input").value = text;
    $("#h-input").value = text;
    $("#m-input").value = text;
    updateCounters();
  }
  if (!hit && !run) return;
  if (tab === "humanize") runHumanize();
  else if (tab === "marks") runScanText();
  else if (tab === "watermark") $("#btn-watermark").click();
  else if (hit) runAnalyze();
}

/* ------------------------------------------------------------------ analyze */

function gauge(score) {
  const arc = 157.08;
  const offset = arc * (1 - score / 100);
  const col = scoreColor(score);
  return `
  <svg class="gauge" viewBox="0 0 120 70" role="img" aria-label="${score}">
    <defs>
      <linearGradient id="gaugeGrad" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="${COLOR.good}"/>
        <stop offset="0.5" stop-color="${COLOR.mid}"/>
        <stop offset="1" stop-color="${COLOR.bad}"/>
      </linearGradient>
    </defs>
    <path d="M10 62 A50 50 0 0 1 110 62" fill="none" stroke="#1b222c" stroke-width="9" stroke-linecap="round"/>
    <path d="M10 62 A50 50 0 0 1 110 62" fill="none" stroke="url(#gaugeGrad)" stroke-width="9"
      stroke-linecap="round" stroke-dasharray="${arc}" stroke-dashoffset="${offset}"/>
    <text x="60" y="50" text-anchor="middle" fill="${col}" font-size="27" font-weight="600"
      font-family="ui-monospace, Consolas, monospace">${score}</text>
    <text x="60" y="65" text-anchor="middle" fill="#5f6c7d" font-size="8"
      font-family="ui-monospace, Consolas, monospace">/ 100</text>
  </svg>`;
}

function renderAnalyze(d) {
  state.lastAnalyze = d;
  const box = $("#analyze-result");
  const stats = d.stats || {};
  const unit = stats.unit_key === "char" ? t("unit.char") : t("unit.word");
  const bits = [];
  if (stats.units != null) bits.push(`${stats.units} ${unit}`);
  if (stats.sentences != null) bits.push(t("stat.sentences", { n: stats.sentences }));
  if (stats.paragraphs != null) bits.push(t("stat.paragraphs", { n: stats.paragraphs }));
  if (stats.avg_sentence_len != null) bits.push(t("stat.avg_len", { n: stats.avg_sentence_len }));
  if (stats.cliche_hits != null) bits.push(t("stat.cliches", { n: stats.cliche_hits }));
  if (stats.readability_flesch != null) bits.push(t("stat.readability", { n: stats.readability_flesch }));

  const feats = [...(d.features || [])]
    .sort((a, b) => b.weight * b.sub - a.weight * a.sub)
    .map((f) => `
      <div class="feat" title="${esc(f.detail)}">
        <span class="feat-name">${esc(f.label)}</span>
        <span class="feat-bar"><i style="width:${Math.max(2, f.sub * 100)}%;background:${subColor(f.sub)}"></i></span>
        <span class="feat-val">${f.value.toFixed(2)} · ${f.weight.toFixed(2)}</span>
      </div>`)
    .join("");

  const flags = (d.flags || [])
    .map((f) => `<div class="flag ${esc(f.level)}"><b>${esc(f.title)}</b><p>${esc(f.detail)}</p></div>`)
    .join("");

  const sents = [...(d.sentences || [])]
    .filter((s) => s.score >= 40)
    .sort((a, b) => b.score - a.score)
    .slice(0, 5)
    .map((s) => `
      <div class="sent" style="border-left-color:${scoreColor(s.score)}">
        <span class="sent-score" style="color:${scoreColor(s.score)}">${s.score}</span>
        <span><span class="sent-text">${esc(s.text)}</span>
        ${s.reasons && s.reasons.length ? `<div class="sent-reasons">${s.reasons.map(esc).join(" · ")}</div>` : ""}</span>
      </div>`)
    .join("");

  const confClass = d.confidence_key === "high" ? "accent" : d.confidence_key === "medium" ? "" : "warn";

  box.innerHTML = `
    <div class="score-card">
      <div>${gauge(d.score)}</div>
      <div class="score-right">
        <div class="score-meta">
          <span class="chip ${d.score >= 70 ? "danger" : d.score >= 40 ? "warn" : "accent"}">${esc(d.band)}</span>
          <span class="chip ${confClass}">${esc(d.confidence)}</span>
          <span class="chip">${d.lang === "zh" ? t("result.lang.zh") : t("result.lang.en")}</span>
          ${d.calibrated ? `<span class="chip accent">${esc(t("result.calibrated"))}</span>` : ""}
        </div>
        <div class="meter"><div class="meter-fill" style="width:${d.score}%;background:${scoreColor(d.score)}"></div></div>
        <div class="meter-labels"><span>${esc(t("result.left"))}</span><span>${esc(t("result.middle"))}</span><span>${esc(t("result.right"))}</span></div>
        <div class="score-stats">${bits.map((b) => `<span>${esc(b)}</span>`).join("")}</div>
      </div>
    </div>

    <div class="block">
      <div class="block-head"><h3>${esc(t("result.features"))}</h3><span class="sub">${esc(t("result.features_hint"))}</span></div>
      <div class="feature-list">${feats || `<div class="placeholder"><p>${esc(t("result.no_features"))}</p></div>`}</div>
    </div>

    ${flags ? `<div class="block"><div class="block-head"><h3>${esc(t("result.diagnosis"))}</h3></div>${flags}</div>` : ""}
    ${sents ? `<div class="block"><div class="block-head"><h3>${esc(t("result.sentences"))}</h3><span class="sub">${esc(t("result.sentences_hint"))}</span></div><div class="sent-list">${sents}</div></div>` : ""}
    <p class="note">${esc(d.disclaimer)}</p>`;

  $$(".sent", box).forEach((row) => {
    row.addEventListener("click", () => {
      const text = $(".sent-text", row)?.textContent || "";
      const ta = $("#input");
      const idx = ta.value.indexOf(text);
      if (idx >= 0) { ta.focus(); ta.setSelectionRange(idx, idx + text.length); }
    });
  });
}

function runAnalyze() {
  const text = $("#input").value;
  if (!text.trim()) {
    $("#analyze-result").innerHTML =
      `<div class="placeholder"><div class="placeholder-icon">◔</div><p>${esc(t("analyze.empty"))}</p></div>`;
    return;
  }
  withLoading($("#btn-analyze"), async () => {
    try { renderAnalyze(await api("/api/analyze", { text })); }
    catch (err) { $("#analyze-result").innerHTML = errorCard(err); }
  });
}

$("#btn-analyze").addEventListener("click", runAnalyze);
$("#btn-clear").addEventListener("click", () => {
  $("#input").value = "";
  updateCounters();
  state.lastAnalyze = null;
  $("#analyze-result").innerHTML =
    `<div class="placeholder"><div class="placeholder-icon">◔</div><p>${esc(t("analyze.empty"))}</p></div>`;
  $("#input").focus();
});
$("#input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); runAnalyze(); }
});

/* ------------------------------------------------------------------ humanize */

let currentLevel = "standard";
$$("#h-level button").forEach((b) => {
  b.addEventListener("click", () => {
    $$("#h-level button").forEach((x) => x.classList.toggle("is-active", x === b));
    currentLevel = b.dataset.level;
  });
});

function renderHumanize(d) {
  state.lastHumanize = d;
  const box = $("#humanize-result");
  const delta = d.after.score - d.before.score;
  const improved = delta < 0;
  const col = improved ? COLOR.good : delta === 0 ? COLOR.mute : COLOR.bad;
  const changes = (d.changes || []).map((c) => `<span class="change-pill">${esc(c.kind)} ×${c.count}</span>`).join("");
  const warnings = (d.warnings || []).map((w) => `<p>${esc(w)}</p>`).join("");

  box.innerHTML = `
    <div class="delta-card">
      <div><div class="delta-label">${esc(t("humanize.before"))}</div>
        <div class="delta-num" style="color:${scoreColor(d.before.score)}">${d.before.score}</div></div>
      <div class="delta-arrow">→</div>
      <div><div class="delta-label">${esc(t("humanize.after"))}</div>
        <div class="delta-num" style="color:${scoreColor(d.after.score)}">${d.after.score}</div></div>
      <div class="delta-note">
        <div style="color:${col};font-family:var(--mono)">${delta > 0 ? "+" : ""}${delta}</div>
        <div>${esc(t("humanize.retention", { pct: pct(d.retention) }))}</div>
        <div>${esc(t("humanize.strength", { level: d.level }))}</div>
      </div>
    </div>
    ${changes ? `<div class="changes">${changes}</div>` : ""}
    ${warnings ? `<div class="warnbox">${warnings}</div>` : ""}
    <div class="out-box">
      <div class="out-head">
        <span>${esc(t("humanize.output"))}</span><span class="grow"></span>
        <button class="btn ghost" id="btn-copy-h">${esc(t("humanize.copy"))}</button>
        <button class="btn ghost" id="btn-reanalyze">${esc(t("humanize.reanalyze"))}</button>
      </div>
      <div class="out-body">${esc(d.text)}</div>
    </div>`;

  $("#btn-copy-h", box).addEventListener("click", async (e) => {
    try {
      await navigator.clipboard.writeText(d.text);
      e.target.textContent = t("humanize.copied");
      setTimeout(() => (e.target.textContent = t("humanize.copy")), 1400);
    } catch { /* clipboard blocked */ }
  });
  $("#btn-reanalyze", box).addEventListener("click", () => {
    $("#input").value = d.text;
    updateCounters();
    $('.tab[data-tab="analyze"]').click();
    runAnalyze();
  });
}

function runHumanize() {
  const text = $("#h-input").value;
  if (!text.trim()) {
    $("#humanize-result").innerHTML =
      `<div class="placeholder"><div class="placeholder-icon">✎</div><p>${esc(t("humanize.empty"))}</p></div>`;
    return;
  }
  withLoading($("#btn-humanize"), async () => {
    try {
      renderHumanize(await api("/api/humanize", {
        text,
        level: currentLevel,
        contractions: $("#h-contractions").checked,
        typography: $("#h-typography").checked,
      }));
    } catch (err) { $("#humanize-result").innerHTML = errorCard(err); }
  });
}

$("#btn-humanize").addEventListener("click", runHumanize);
$("#h-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); runHumanize(); }
});

/* ------------------------------------------------------------------ marks */

function renderInvisible(d, box = $("#marks-result")) {
  state.lastInvisible = d;

  if (!d.total) {
    box.innerHTML = `
      <div class="clean-state">
        <div class="clean-icon">✓</div>
        <h3>${esc(t("marks.empty_title"))}</h3>
        <p>${esc(d.verdict)}</p>
        <p class="tiny">${esc(t("marks.empty_note", { n: d.chars }))}</p>
      </div>`;
    return;
  }

  const cats = (d.categories || []).map((c) => `
    <div class="mark-cat">
      <header>
        <h4>${esc(c.label)}</h4><span class="count">${c.count}</span>
        <span class="chip ${c.risk === "high" ? "danger" : c.risk === "medium" ? "warn" : ""}">${esc(c.risk)}</span>
      </header>
      <p>${esc(c.note)}</p>
      <div class="cp-list">${(c.chars || [])
        .map((ch) => `<span class="cp" title="${esc(ch.name)}">${esc(ch.codepoint)}<small>×${ch.count}</small></span>`)
        .join("")}</div>
    </div>`).join("");

  const runs = (d.long_runs || []).map((r) => `
    <div class="sent"><span class="sent-score" style="color:${COLOR.bad}">${r.length}</span>
      <span><span class="sent-text">${esc(t("marks.run_item", { n: r.length, pos: r.start }))}</span>
      <div class="sent-reasons">${esc((r.codepoints || []).join(" "))}</div></span></div>`).join("");

  const mixed = (d.mixed_script_words || []).map((w) => {
    const script = w.foreign_key === "greek" ? t("script.greek") : t("script.cyrillic");
    return `<div class="sent"><span class="sent-score" style="color:${COLOR.mid}">⚠</span>
      <span><span class="sent-text">${esc(w.word)}</span>
      <div class="sent-reasons">${esc(t("marks.mixed_item", { script }))}</div></span></div>`;
  }).join("");

  box.innerHTML = `
    <div class="score-card" style="grid-template-columns:1fr">
      <div class="score-right">
        <div class="score-meta">
          <span class="chip ${d.level === "high" ? "danger" : d.level === "medium" ? "warn" : ""}">${esc(t("marks.hit", { n: d.total }))}</span>
          <span class="chip">${esc(t("marks.chars", { n: d.chars }))}</span>
        </div>
        <div style="font-size:13px;color:#c8d2e0">${esc(d.verdict)}</div>
      </div>
    </div>
    ${cats}
    ${runs ? `<div class="block"><div class="block-head"><h3>${esc(t("marks.runs"))}</h3></div><div class="sent-list">${runs}</div></div>` : ""}
    ${mixed ? `<div class="block"><div class="block-head"><h3>${esc(t("marks.mixed"))}</h3></div><div class="sent-list">${mixed}</div></div>` : ""}`;
}

function runScanText() {
  const text = $("#m-input").value;
  if (!text.trim()) return;
  withLoading($("#btn-scan-text"), async () => {
    try { renderInvisible(await api("/api/scan-text", { text })); }
    catch (err) { $("#marks-result").innerHTML = errorCard(err); }
  });
}

$("#btn-scan-text").addEventListener("click", runScanText);

$("#btn-clean-text").addEventListener("click", async () => {
  const text = $("#m-input").value;
  if (!text.trim()) return;
  const btn = $("#btn-clean-text");
  withLoading(btn, async () => {
    try {
      const data = await api("/api/clean-text", { text });
      $("#m-input").value = data.text;
      updateCounters();
      await navigator.clipboard.writeText(data.text).catch(() => {});
      btn.textContent = t("marks.cleaned", { n: data.total });
      setTimeout(() => (btn.textContent = t("marks.clean")), 2000);
      renderInvisible(await api("/api/scan-text", { text: data.text }));
    } catch (err) { $("#marks-result").innerHTML = errorCard(err); }
  });
});

/* ------------------------------------------------------------------ files */

function renderFileReport(d, box) {
  state.lastFile = d;
  const badges = [
    `<span class="chip accent">${esc(d.kind.toUpperCase())}</span>`,
    `<span class="chip">${(d.size / 1024).toFixed(1)} KB</span>`,
    d.has_c2pa ? `<span class="chip danger">C2PA / JUMBF</span>` : "",
    (d.ai_hints || []).length ? `<span class="chip warn">${(d.ai_hints || []).length} AI</span>` : "",
  ].filter(Boolean).join("");

  const rows = (d.findings || []).map((f) => `
    <tr><td>${esc(f.key)}<br><span class="tiny">${esc(f.source)}</span></td>
    <td class="val">${esc(f.value)}</td></tr>`).join("");

  const hints = (d.ai_hints || []).map((h) => `<p>· ${esc(h)}</p>`).join("");
  const notes = (d.notes || []).map((n) => `<p>${esc(n)}</p>`).join("");

  box.innerHTML = `
    <div class="badge-row">${badges}</div>
    ${rows ? `<table class="meta-table">${rows}</table>` : `<p class="note">${esc(t("meta.no_fields"))}</p>`}
    ${hints ? `<div class="warnbox">${hints}</div>` : ""}
    ${notes ? `<p class="note">${notes}</p>` : ""}
    ${d.strippable ? `<button class="btn ghost" id="btn-strip" style="margin-top:14px">${esc(t("meta.strip"))}</button>` : ""}
    <div id="strip-info"></div>`;

  const stripBtn = $("#btn-strip", box);
  if (stripBtn && state.lastFileRaw) {
    stripBtn.addEventListener("click", () => withLoading(stripBtn, async () => {
      try {
        const res = await fetch(
          `/api/strip?name=${encodeURIComponent(state.lastFileRaw.name)}&locale=${state.locale}`,
          { method: "POST", body: state.lastFileRaw });
        const info = await res.json();
        if (!res.ok) throw new Error(info.error || `HTTP ${res.status}`);
        const bytes = Uint8Array.from(atob(info.download), (c) => c.charCodeAt(0));
        const url = URL.createObjectURL(new Blob([bytes]));
        const a = document.createElement("a");
        a.href = url; a.download = info.name; a.click();
        URL.revokeObjectURL(url);
        $("#strip-info", box).innerHTML =
          `<p class="note">${esc(t("meta.stripped", { items: (info.removed || []).join(", "), name: info.name }))}</p>`;
      } catch (err) { $("#strip-info", box).innerHTML = errorCard(err); }
    }));
  }
}

async function handleFile(file) {
  state.lastFileRaw = file;
  const box = $("#marks-result");
  box.innerHTML = `<div class="placeholder"><p>${esc(file.name)}…</p></div>`;
  try {
    const res = await fetch(`/api/file?name=${encodeURIComponent(file.name)}&locale=${state.locale}`,
      { method: "POST", body: file });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
    renderFileReport(data, box);
    if (data.invisible) {
      const wrap = document.createElement("div");
      wrap.className = "block";
      wrap.innerHTML = `<div class="block-head"><h3>${esc(t("marks.text_pane"))}</h3></div>`;
      box.appendChild(wrap);
      const inner = document.createElement("div");
      wrap.appendChild(inner);
      renderInvisible(data.invisible, inner);
    }
  } catch (err) { box.innerHTML = errorCard(err); }
}

$("#file-input").addEventListener("change", (e) => {
  if (e.target.files && e.target.files[0]) handleFile(e.target.files[0]);
});

const drop = $("#drop-zone");
["dragenter", "dragover"].forEach((ev) => drop.addEventListener(ev, (e) => {
  e.preventDefault(); drop.classList.add("is-over");
}));
["dragleave", "drop"].forEach((ev) => drop.addEventListener(ev, (e) => {
  e.preventDefault(); drop.classList.remove("is-over");
}));
drop.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files && e.dataTransfer.files[0];
  if (file) handleFile(file);
});

/* ------------------------------------------------------------------ watermark */

function renderWatermark(d) {
  state.lastWatermark = d;
  const block = (title, text, res) => {
    const cls = res.level === "strong" ? "z-strong" : res.level === "medium" ? "z-mid" : "z-none";
    return `
    <div class="wm-block">
      <h4>${esc(title)}<span class="chip ${res.level === "strong" ? "danger" : res.level === "medium" ? "warn" : "accent"}">p ${res.p_value < 1e-6 ? "<1e-6" : res.p_value.toExponential(1)}</span></h4>
      <div class="wm-text">${esc(text)}</div>
      <div class="wm-stat ${cls}">${esc(t("wm.green", { g: res.green, n: res.n_pairs, pct: pct(res.green_ratio) }))} · z = ${res.z.toFixed(2)}</div>
      <div class="wm-verdict">${esc(res.verdict)}</div>
    </div>`;
  };

  const wrong = d.wrong_keys || [];
  const lo = wrong.length ? Math.min(...wrong.map((w) => w.z)) : 0;
  const hi = wrong.length ? Math.max(...wrong.map((w) => w.z)) : 0;
  const wrongBlock = `
    <div class="wm-block">
      <h4>${esc(t("wm.wrong", { n: wrong.length }))}<span class="chip accent">${esc(t("wm.not_detected"))}</span></h4>
      <div class="wm-text">${esc(d.marked_text)}</div>
      <div class="wm-stat">${wrong.map((w) => `z=${w.z >= 0 ? "+" : ""}${w.z.toFixed(2)}`).join(" · ")}</div>
      <div class="wm-verdict">${esc(t("wm.range", { lo: lo.toFixed(2), hi: hi.toFixed(2), z: d.marked.z.toFixed(2) }))}<br>${esc(t("wm.single"))}</div>
    </div>`;

  $("#wm-out").innerHTML = `
    ${block(t("wm.plain"), d.plain_text, d.plain)}
    ${block(t("wm.marked"), d.marked_text, d.marked)}
    ${wrongBlock}
    <div class="wm-block" style="grid-column:1/-1">
      <h4>${esc(t("wm.title"))}</h4>
      <div class="wm-verdict" style="color:#c8d2e0">${esc(d.note)}</div>
    </div>`;
}

$("#btn-watermark").addEventListener("click", () => {
  const key = $("#wm-key").value.trim() || "misa-demo";
  const length = parseInt($("#wm-length").value, 10) || 120;
  withLoading($("#btn-watermark"), async () => {
    try { renderWatermark(await api("/api/watermark", { key, length })); }
    catch (err) { $("#wm-out").innerHTML = errorCard(err); }
  });
});

/* ------------------------------------------------------------------ boot */

async function boot() {
  try { await loadStrings(currentLocale()); } catch { applyI18n(); }
  loadSamples();
  $("#input").focus();
}

boot();
