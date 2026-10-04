// APORIA lab front end. Everything drawn here is driven by streamed engine state.
const $ = (s) => document.querySelector(s);
const css = getComputedStyle(document.documentElement);
const FN = ["memory", "reason", "imagine", "intuit", "introspect", "doubt", "counterfactual", "formalize", "inquire", "adjudicate", "revise", "conclude"];
const COLOR = Object.fromEntries(FN.map((f) => [f, css.getPropertyValue("--" + f).trim()]));
const RGB = Object.fromEntries(FN.map((f) => [f, hexRgb(COLOR[f])]));
const TYPE_FN = { hypothesis: "reason", claim: "reason", premise: "reason", assumption: "introspect", objection: "doubt",
  counterexample: "doubt", contradiction: "doubt", counterfactual: "counterfactual", thought_experiment: "imagine",
  alternative: "imagine", evidence: "memory", question: "inquire", response: "adjudicate" };
const PER_AGENT = matchMedia("(max-width: 640px)").matches ? 600 : 1300;

function hexRgb(h) { const n = parseInt(h.slice(1), 16); return [n >> 16, (n >> 8) & 255, n & 255]; }
function esc(s) { return String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])); }
function hash(s) { let h = 2166136261; for (const c of String(s)) h = Math.imul(h ^ c.charCodeAt(0), 16777619); return (h >>> 0) / 4294967296; }
function gauss() { return Math.sqrt(-2 * Math.log(Math.random() + 1e-9)) * Math.cos(2 * Math.PI * Math.random()); }
function nodeFn(n) {
  if (n.text.startsWith("Hunch:")) return "intuit";
  if (n.formal) return "formalize";
  return TYPE_FN[n.type] || "reason";
}

// ------------------------------------------------------------------ state
let profiles = [];
let agents = {};      // name -> { idx, state, op, focus, layout, cum, model, budget, error }
let mode = "landing";
let STATIC = false;   // no lab server (e.g. GitHub Pages): replay recorded runs from ../data/
let sweep = [];       // metrics per Δ in the current job
let lastMetrics = null;
let links = [];       // transient association / compute visuals
const sourceUse = {}; // literature source -> Set(agent) for cross-reasoner associations

// ------------------------------------------------------------------ particles
const cv = $("#nebula"), ctx = cv.getContext("2d");
let W = 0, H = 0, DPR = 1;
function resize() { DPR = Math.min(2, devicePixelRatio || 1); W = innerWidth; H = innerHeight; cv.width = W * DPR; cv.height = H * DPR; ctx.setTransform(DPR, 0, 0, DPR, 0, 0); }
addEventListener("resize", resize); resize();

let P = null;
function buildParticles(nAgents) {
  const N = nAgents * PER_AGENT;
  P = { N, x: new Float32Array(N), y: new Float32Array(N), vx: new Float32Array(N), vy: new Float32Array(N),
    ag: new Uint8Array(N), u: new Float32Array(N), g1: new Float32Array(N), g2: new Float32Array(N),
    s: new Float32Array(N), kick: new Float32Array(N), node: new Int16Array(N).fill(-1) };
  for (let i = 0; i < N; i++) {
    P.ag[i] = Math.floor(i / PER_AGENT); P.u[i] = Math.random(); P.g1[i] = gauss(); P.g2[i] = gauss(); P.s[i] = Math.random();
    P.x[i] = W / 2 + gauss() * 60; P.y[i] = H / 2 + gauss() * 60;
  }
}
buildParticles(5);

function geometry() {
  if (mode === "landing") return { centers: Array(5).fill([W / 2, H * 0.5]), R: Math.min(W, H) * 0.2 };
  const r = $("#stage").getBoundingClientRect();
  const cx = r.left + r.width / 2, cy = r.top + r.height / 2 - 6;
  const n = profiles.length || 5, rx = r.width * 0.36, ry = r.height * 0.33;
  const centers = profiles.map((_, i) => {
    const a = -Math.PI / 2 + (i * 2 * Math.PI) / n;
    return [cx + Math.cos(a) * rx, cy + Math.sin(a) * ry];
  });
  return { centers, R: Math.min(r.width / 9, r.height / 5.6), cx, cy, rect: r };
}

// Radial argument-graph layout, in units of R. Open objections are pushed out into a competing cluster.
function layout(a) {
  const st = a.state, nodes = st.nodes, kids = {}, pos = {};
  nodes.forEach((n) => { (kids[n.parent ?? "_"] ||= []).push(n); });
  const open = new Set(st.conflicts.filter((c) => c.status === "open").map((c) => c.objection));
  const place = (n, ang, span, depth) => {
    const rad = [0, 0.45, 0.72, 0.9, 1.0][Math.min(depth, 4)];
    let x = Math.cos(ang) * rad, y = Math.sin(ang) * rad;
    if (open.has(n.id)) { x *= 1.35; y *= 1.35; }
    pos[n.id] = [x, y];
    const ch = kids[n.id] || [];
    ch.forEach((c, i) => {
      const s = depth === 0 ? (2 * Math.PI) / Math.max(ch.length, 1) : span / Math.max(ch.length, 1);
      const a0 = depth === 0 ? ang + hash(c.id) * 0.5 : ang - span / 2 + s / 2;
      place(c, a0 + i * s, Math.min(s, 1.4), depth + 1);
    });
  };
  const roots = kids["_"] || [];
  roots.forEach((r, i) => {
    if (r.id === st.root) place(r, 0, 2 * Math.PI, 0);
    else { // abandoned claims drift at the rim with their branch
      const ang = hash(r.id) * 2 * Math.PI;
      place(r, ang, 1, 3);
    }
  });
  a.layout = pos;
  // particle share per node: attention (focus), curiosity, status
  const w = nodes.map((n) => {
    let v = n.status === "rejected" ? 0.12 : n.status === "supported" ? 2 : n.status === "stable" ? 9 : 1.3;
    if (n.id === st.root && n.status !== "rejected") v += 4;
    if (n.id === a.focus && a.op) v += 6;
    if (open.has(n.id)) v += 3;
    return v + 2 * (n.curiosity || 0);
  });
  const z = w.reduce((s, x) => s + x, 0) || 1;
  let acc = 0;
  a.cum = w.map((x) => (acc += x / z));
  a.ids = nodes.map((n) => n.id);
  a.fn = nodes.map((n) => (n.status === "rejected" ? null : nodeFn(n)));
  a.open = open;
  for (let i = 0; i < P.N; i++) {
    if (P.ag[i] !== a.idx) continue;
    let k = 0; while (k < a.cum.length - 1 && a.cum[k] < P.u[i]) k++;
    P.node[i] = a.cum.length ? k : -1;
  }
}

function frame(t) {
  const g = geometry();
  ctx.globalCompositeOperation = "source-over";
  ctx.fillStyle = "rgba(8,9,11,0.32)";
  ctx.fillRect(0, 0, W, H);
  ctx.globalCompositeOperation = "lighter";
  const list = profiles.map((p) => agents[p]);

  // structure: edges of each argument graph, and open contradictions
  if (mode === "lab") for (const a of list) {
    if (!a?.layout) continue;
    const [cx, cy] = g.centers[a.idx];
    for (const n of a.state.nodes) {
      if (!n.parent || !a.layout[n.parent]) continue;
      const p1 = a.layout[n.id], p2 = a.layout[n.parent];
      ctx.strokeStyle = n.status === "rejected" ? "rgba(255,255,255,0.025)" : "rgba(233,230,223,0.07)";
      ctx.beginPath(); ctx.moveTo(cx + p1[0] * g.R, cy + p1[1] * g.R); ctx.lineTo(cx + p2[0] * g.R, cy + p2[1] * g.R); ctx.stroke();
    }
    for (const c of a.state.conflicts) {
      if (c.status !== "open" || !a.layout[c.objection] || !a.layout[c.target]) continue;
      const p1 = a.layout[c.objection], p2 = a.layout[c.target];
      ctx.strokeStyle = `rgba(255,107,79,${0.15 + 0.25 * Math.random()})`;
      ctx.beginPath(); ctx.moveTo(cx + p1[0] * g.R, cy + p1[1] * g.R); ctx.lineTo(cx + p2[0] * g.R, cy + p2[1] * g.R); ctx.stroke();
    }
    // core glow in the colour of the function currently running
    const glow = a.state.conclusion ? "conclude" : a.op;
    if (glow) {
      const [r, gg, b] = RGB[glow], pulse = a.state.conclusion ? 0.35 : 0.22 + 0.12 * Math.sin(t / 220);
      const grd = ctx.createRadialGradient(cx, cy, 0, cx, cy, g.R * 0.9);
      grd.addColorStop(0, `rgba(${r},${gg},${b},${pulse})`); grd.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = grd; ctx.beginPath(); ctx.arc(cx, cy, g.R * 0.9, 0, 7); ctx.fill();
    }
    if (a.state.conclusion) { // stabilised hypothesis: a persistent ring
      ctx.strokeStyle = "rgba(255,255,255,0.18)"; ctx.beginPath(); ctx.arc(cx, cy, g.R * 0.22, 0, 7); ctx.stroke();
    }
  }

  // particles
  for (let i = 0; i < P.N; i++) {
    const a = list[P.ag[i]], ci = g.centers[P.ag[i]] || [W / 2, H / 2];
    let tx = ci[0], ty = ci[1], unc = 0.8, conf = 0.3, cur = 0.3, col = RGB.reason, alpha = 0.35, stable = false;
    if (a?.layout && P.node[i] >= 0) {
      const st = a.state, k = P.node[i], id = a.ids[k], p = a.layout[id] || [0, 0];
      unc = st.uncertainty; conf = st.confidence; cur = st.curiosity; stable = !!st.conclusion;
      const fn = a.fn[k];
      col = fn ? RGB[fn] : [90, 90, 88];
      alpha = fn ? (a.open.has(id) ? 0.75 : 0.55) : 0.18;
      tx += p[0] * g.R; ty += p[1] * g.R;
      // curiosity: a streak of particles reaching away from the centre into unexplored space
      if (P.s[i] < cur * 0.35 && g.cx) {
        const dx = ci[0] - g.cx, dy = ci[1] - g.cy, d = Math.hypot(dx, dy) || 1, reach = g.R * (0.5 + P.u[i]) * cur;
        tx += (dx / d) * reach + P.g2[i] * g.R * 0.15; ty += (dy / d) * reach + P.g1[i] * g.R * 0.15;
      }
    } else if (mode === "landing") {
      const breath = 1 + 0.06 * Math.sin(t / 1400 + P.s[i] * 6);
      tx += Math.cos(P.s[i] * 6.283 + t / 9000) * g.R * 0.6 * P.u[i] * breath;
      ty += Math.sin(P.s[i] * 6.283 + t / 9000) * g.R * 0.6 * P.u[i] * breath;
      col = RGB[FN[P.ag[i] % FN.length]]; alpha = 0.22;
    }
    // uncertainty diffuses the cloud, confidence tightens it, conclusion freezes it
    const crystal = a?.crystal?.[a.ids?.[P.node[i]]] || 0;
    const sigma = g.R * (0.04 + 0.2 * unc) * (1.2 - 0.6 * conf) * (stable ? 0.5 : 1) * (1 - 0.7 * crystal);
    tx += P.g1[i] * sigma; ty += P.g2[i] * sigma;
    const k = stable ? 0.02 : 0.012 + 0.01 * conf;
    P.vx[i] = P.vx[i] * 0.86 + (tx - P.x[i]) * k + (stable ? 0 : (Math.random() - 0.5) * unc * 0.6);
    P.vy[i] = P.vy[i] * 0.86 + (ty - P.y[i]) * k + (stable ? 0 : (Math.random() - 0.5) * unc * 0.6);
    if (P.kick[i] > 0) { P.kick[i] -= 0.012; alpha *= 1 - P.kick[i]; }
    P.x[i] += P.vx[i]; P.y[i] += P.vy[i];
    ctx.fillStyle = `rgba(${col[0]},${col[1]},${col[2]},${alpha})`;
    ctx.fillRect(P.x[i], P.y[i], 1.3, 1.3);
  }

  // transient links: memory associations to the literature ring, cross-reasoner shared sources, compute pulses
  links = links.filter((l) => (l.life -= 0.006) > 0);
  for (const l of links) {
    const a = agents[l.agent]; if (!a) continue;
    const c = g.centers[a.idx];
    if (l.kind === "association" && a.layout?.[l.node]) {
      const p = a.layout[l.node], ang = hash(l.source) * 2 * Math.PI;
      const ex = g.cx + Math.cos(ang) * Math.max(W, g.rect.width) * 0.48, ey = g.cy + Math.sin(ang) * g.rect.height * 0.55;
      const [r, gg, b] = RGB.memory;
      ctx.strokeStyle = `rgba(${r},${gg},${b},${0.35 * l.life})`;
      ctx.setLineDash(l.recall ? [3, 4] : []);
      ctx.beginPath(); ctx.moveTo(c[0] + p[0] * g.R, c[1] + p[1] * g.R);
      ctx.quadraticCurveTo(g.cx, g.cy, ex, ey); ctx.stroke(); ctx.setLineDash([]);
      for (const other of l.shared || []) {
        const o = agents[other]; if (!o) continue;
        const oc = g.centers[o.idx];
        ctx.strokeStyle = `rgba(${r},${gg},${b},${0.5 * l.life})`;
        ctx.beginPath(); ctx.moveTo(c[0], c[1]); ctx.quadraticCurveTo(g.cx, g.cy, oc[0], oc[1]); ctx.stroke();
      }
    } else if (l.kind === "insight" && a.layout?.[l.node]) {
      const p = a.layout[l.node];
      ctx.strokeStyle = `rgba(255,255,255,${0.7 * l.life})`;
      ctx.beginPath(); ctx.arc(c[0] + p[0] * g.R, c[1] + p[1] * g.R, 4 + (1 - l.life) * g.R * 0.5, 0, 7); ctx.stroke();
    } else if (l.kind === "tool") {
      const [r, gg, b] = l.ok ? RGB.formalize : RGB.doubt, sz = 6 + (1 - l.life) * 18;
      ctx.strokeStyle = `rgba(${r},${gg},${b},${0.8 * l.life})`;
      ctx.strokeRect(c[0] - sz / 2, c[1] - sz / 2, sz, sz);
    } else if (l.kind === "compute") {
      ctx.strokeStyle = `rgba(240,213,98,${0.5 * l.life})`;
      ctx.beginPath(); ctx.arc(c[0], c[1], g.R * (1.6 - l.life * 0.6), 0, 7); ctx.stroke();
    }
  }
  if (mode === "lab") placeLabels(g);
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);

function placeLabels(g) {
  profiles.forEach((p, i) => {
    const el = document.getElementById("lab-" + p), a = agents[p];
    if (!el || !a) return;
    const [x, y] = g.centers[i], r = g.rect;
    el.style.left = x - r.left + "px"; el.style.top = y - r.top + g.R * 0.95 + "px";
  });
}

// ------------------------------------------------------------------ events
function onEvent(e) {
  if (e.type === "run_start") return startRun(e);
  if (e.type === "op") {
    const a = agents[e.agent]; a.op = e.op; a.focus = e.focus; a.why = e.why || [];
    if (a.state.nodes.length) layout(a);
    return updateLabel(e.agent);
  }
  if (e.type === "op") return;
  if (e.type === "state") {
    const a = agents[e.agent];
    a.state = e.state; a.budget = e.budget;
    if (a.state.conclusion) a.op = null;
    layout(a);
    updateLabel(e.agent); scheduleCard(e.agent);
    return;
  }
  if (e.type === "cog" && agents[e.agent]) return visualEvent(e.agent, e);
  if (e.type === "metrics") return showMetrics(e);
  if (e.type === "error") {
    if (e.agent && agents[e.agent]) { agents[e.agent].error = e.msg; scheduleCard(e.agent); }
    else $("#runinfo").textContent += " · error: " + e.msg;
  }
  if (e.type === "done") { $("#runinfo").textContent = $("#runinfo").textContent.replace(" · reasoning…", " · finished"); loadRuns(); }
}

function visualEvent(agent, ev) {
  const a = agents[agent];
  if (ev.kind === "rejection") {
    if (!a.ids) return;
    const k = a.ids.indexOf(ev.node);
    for (let i = 0; i < P.N; i++) if (P.ag[i] === a.idx && P.node[i] === k) {
      P.kick[i] = 1; P.vx[i] += gauss() * 4; P.vy[i] += gauss() * 4;
    }
  } else if (ev.kind === "association") {
    const set = (sourceUse[ev.source] ||= new Set());
    const shared = ev.source ? [...set].filter((x) => x !== agent) : [];
    if (ev.source) set.add(agent);
    links.push({ kind: "association", agent, node: ev.node, source: ev.source || ev.node, shared, life: 1 });
  } else if (ev.kind === "compute") {
    links.push({ kind: "compute", agent, life: 1 });
  } else if (ev.kind === "insight") {
    (a.crystal ||= {})[ev.node] = 1;  // local crystallisation, permanent for a stable conclusion
    links.push({ kind: "insight", agent, node: ev.node, life: 1 });
  } else if (ev.kind === "recall") {
    links.push({ kind: "association", agent, node: ev.node, source: "memory:" + ev.memory_kind, shared: [], life: 1, recall: true });
  } else if (ev.kind === "tool") {
    links.push({ kind: "tool", agent, ok: ev.ok, life: 1 });
  }
}

// ------------------------------------------------------------------ run setup
function startRun(e) {
  profiles = e.profiles;
  for (const k in sourceUse) delete sourceUse[k];
  agents = Object.fromEntries(profiles.map((p, i) => [p, {
    idx: i, op: "start", focus: null, model: e.models[i], policy: e.policies[p], budget: e.policies[p].budget,
    state: { nodes: [], conflicts: [], history: [], series: [], confidence: 0.5, uncertainty: 0.6, curiosity: 0.3, step: 0 },
  }]));
  for (let i = 0; i < P.N; i++) P.node[i] = -1;
  const cond = { architecture: "cognitive architecture", prompt: "prompt persona", model: "model variants", base: "base" }[e.condition];
  $("#runinfo").textContent = `${cond} · Δ ${e.delta.toFixed(1)}` + (e.runs > 1 ? ` · sweep ${e.run + 1}/${e.runs}` : "") + ` · seed ${e.seed} · reasoning…`;
  $("#qtitle").textContent = e.question;
  $("#labels").innerHTML = profiles.map((p) => `<div class="lab" id="lab-${p}"></div>`).join("");
  $("#agents").innerHTML = profiles.map((p) => `<article class="agent" id="card-${p}"></article>`).join("");
  $("#verdict").hidden = true;
  profiles.forEach((p) => { updateLabel(p); renderCard(p); });
}

function updateLabel(p) {
  const a = agents[p], el = document.getElementById("lab-" + p);
  if (!el) return;
  const st = a.state, op = st.conclusion ? "concluded" : a.op || "";
  const c = st.conclusion ? COLOR.conclude : COLOR[a.op] || "var(--dim)";
  const why = !st.conclusion && a.why?.length ? `<br><span class="why">${esc(a.why[0])}</span>` : "";
  el.innerHTML = `<b>${p}</b><span class="op" style="color:${c}">${op}</span>${why}<br>` +
    `conf ${st.confidence.toFixed(2)} · unc ${st.uncertainty.toFixed(2)} · step ${st.step}/${a.budget}`;
}

const pending = new Set();
function scheduleCard(p) {
  if (pending.has(p)) return;
  pending.add(p);
  requestAnimationFrame(() => { pending.delete(p); renderCard(p); });
}

function renderCard(p) {
  const a = agents[p], st = a.state, el = document.getElementById("card-" + p);
  if (!el) return;
  const uniq = lastMetrics?.unique?.[p] || { assumptions: [], objections: [] };
  const uniqSet = new Set([...uniq.assumptions, ...uniq.objections]);
  const strip = st.history.map((h) => `<span title="${h.op}${h.focus ? " → " + h.focus : ""}" style="background:${COLOR[h.op] || "#666"}"></span>`).join("");
  el.innerHTML = `<h4>${p}</h4><div class="model">${esc(a.model)}</div>
    <div class="strip">${strip}</div>${spark(st.series)}
    <div class="sparkkey"><span style="color:var(--ink)">— confidence</span> &nbsp;<span style="color:var(--doubt)">— uncertainty</span> &nbsp;<span style="color:var(--imagine)">— novelty</span></div>
    ${learned(a)}
    <p class="hyp">${esc(st.hypothesis || "…")}</p>
    ${tree(st, uniqSet)}
    ${st.conclusion ? `<div class="final"><div class="stance">${esc(st.conclusion.stance)} · credence ${st.conclusion.credence.toFixed(2)}</div>
      <p>${esc(st.conclusion.position)}</p>${st.conclusion.open_objection ? `<p class="obj">Open: ${esc(st.conclusion.open_objection)}</p>` : ""}</div>` : ""}
    ${experiments(st)}
    ${a.error ? `<p class="err">${esc(a.error)}</p>` : ""}`;
}

// In-session learning: how the controller has re-weighted each function from the information it produced
function learned(a) {
  const v = a.state.values || {}, ops = Object.keys(v);
  if (!ops.length) return "";
  const mean = ops.reduce((s, k) => s + v[k], 0) / ops.length, lr = a.policy.learning_rate;
  return `<div class="learn" title="learned routing multiplier per function">` + ops.filter((k) => k !== "conclude").map((k) => {
    const m = Math.max(0.4, Math.min(2.2, 1 + lr * (v[k] - mean) / (mean + 0.05)));
    return `<span title="${k} ×${m.toFixed(2)}"><i style="height:${m * 9}px;background:${COLOR[k]}"></i></span>`;
  }).join("") + `</div>`;
}

function experiments(st) {
  const xs = st.experiments || [], tl = st.tool_log || [], rc = st.recalls || [];
  if (!xs.length && !tl.length && !rc.length) return "";
  const mark = { pending: "…", defeated: "✕ target lost", answered: "✓ target held", moot: "— moot" };
  const node = (id) => st.nodes.find((n) => n.id === id)?.text || id;
  return `<details class="exps"><summary>${xs.length} experiments · ${tl.length} tool calls · ${rc.length} recalls</summary>` +
    xs.map((x) => `<div class="x ${x.status}"><span>${x.kind}</span> ${esc(node(x.node).slice(0, 110))} <em>${mark[x.status] || x.status}</em></div>`).join("") +
    tl.map((t) => `<div class="x tool"><span>${t.tool}</span> ${t.ok ? "" : "failed: "}${esc(t.summary.slice(0, 90))}</div>`).join("") +
    rc.map((r) => `<div class="x recall"><span>recall ${r.kind}</span> ${esc(r.text.slice(0, 90))} <em>${esc(r.outcome).slice(0, 40)}</em></div>`).join("") +
    `</details>`;
}

function spark(series) {
  if (!series.length) return '<svg class="spark"></svg>';
  const n = Math.max(series.length - 1, 1);
  const line = (k, c) => `<polyline fill="none" stroke="${c}" stroke-width="1.2" points="${series.map((s, i) => `${(i / n) * 100},${40 - s[k] * 38}`).join(" ")}"/>`;
  return `<svg class="spark" viewBox="0 0 100 42" preserveAspectRatio="none">${line("novelty", COLOR.imagine + "88")}${line("uncertainty", COLOR.doubt)}${line("confidence", "#e9e6df")}</svg>`;
}

function tree(st, uniq) {
  const kids = {};
  st.nodes.forEach((n) => (kids[n.parent ?? "_"] ||= []).push(n));
  const item = (n) => {
    const fn = nodeFn(n), ch = kids[n.id] || [];
    return `<li class="${n.status}"><span class="t" style="color:${COLOR[fn]}">${n.type.replace("_", " ")}</span>` +
      `<span class="txt">${esc(n.text)}</span>${uniq.has(n.text) ? '<span class="uniq" title="no other reasoner found this">◆ unique</span>' : ""}` +
      (ch.length ? `<ul>${ch.map(item).join("")}</ul>` : "") + "</li>";
  };
  const roots = (kids["_"] || []).sort((x, y) => (y.id === st.root) - (x.id === st.root));
  const [cur, ...old] = roots;
  return `<ul class="tree">${cur ? item(cur) : ""}</ul>` +
    (old.length ? `<details><summary>${old.length} abandoned hypothes${old.length > 1 ? "es" : "is"}</summary><ul class="tree">${old.map(item).join("")}</ul></details>` : "");
}

// ------------------------------------------------------------------ metrics
const MLABEL = {
  semantic_diversity: ["semantic diversity", 1], branch_diversity: ["branch diversity", 1], disagreement_rate: ["disagreement rate", 1],
  path_similarity: ["reasoning-path similarity", 1], conclusion_similarity: ["conclusion similarity", 1],
  unique_assumptions: ["unique assumptions", 0], unique_objections: ["unique objections", 0], unique_hypotheses: ["unique hypotheses", 0],
};

function showMetrics(e) {
  const m = e.metrics;
  lastMetrics = m;
  sweep.push({ delta: e.delta, m });
  $("#metrics").hidden = false;
  $("#mgrid").innerHTML = Object.entries(MLABEL).map(([k, [label, frac]]) =>
    `<div class="m"><div class="v">${frac ? m[k].toFixed(2) : m[k]}</div><div class="k">${label}</div>` +
    (frac ? `<div class="bar2"><i style="width:${m[k] * 100}%"></i></div>` : "") + "</div>").join("");
  $("#pairs").innerHTML = `<div class="tablewrap"><table><tr><th>pair</th><th>semantic dist.</th><th>branch dist.</th><th>path sim.</th><th>conclusion sim.</th><th>disagree</th></tr>` +
    Object.entries(m.pairs).sort((x, y) => x[1].concl_sim - y[1].concl_sim).map(([k, v]) =>
      `<tr><td>${k.replace("|", " × ")}</td><td>${v.semantic}</td><td>${v.branch}</td><td>${v.path_sim}</td><td>${v.concl_sim}</td><td>${v.disagree ? "yes" : "—"}</td></tr>`).join("") + "</table></div>";
  const pa = m.per_agent || {};
  const cols = [["hypotheses", "hypotheses"], ["rejected_hypotheses", "rejected"], ["surviving_hypotheses", "surviving"],
    ["experiments", "experiments"], ["resolution_rate", "resolution"], ["defeats", "defeats"], ["novelty", "novelty"],
    ["gain_per_step", "info gain/step"], ["tool_calls", "tools"], ["recalls", "recalls"]];
  $("#pairs").innerHTML += `<div class="tablewrap"><table><tr><th>reasoner</th>${cols.map((c) => `<th>${c[1]}</th>`).join("")}<th>compute allocation</th></tr>` +
    Object.entries(pa).map(([n, v]) => `<tr><td>${n}</td>${cols.map((c) => `<td>${v[c[0]]}</td>`).join("")}<td>${alloc(v.compute)}</td></tr>`).join("") + "</table></div>";
  verdict(m);
  profiles.forEach(renderCard);
  if (sweep.length > 1) sweepChart();
}

function alloc(c) {
  return `<span class="alloc">` + Object.entries(c || {}).map(([k, v]) => `<i title="${k} ${(v * 100).toFixed(0)}%" style="width:${v * 160}px;background:${COLOR[k] || "#666"}"></i>`).join("") + "</span>";
}

function verdict(m) {
  if (!m.most_divergent) return;
  const [x, y] = m.most_divergent.split("|"), p = m.pairs[m.most_divergent];
  const side = (n) => { const c = agents[n].state.conclusion || {}; return `<div class="side"><h4 style="color:${COLOR[agents[n].op] || "var(--ink)"}">${n} · ${esc(c.stance)} ${c.credence?.toFixed(2) ?? ""}</h4><p>${esc(c.position)}</p></div>`; };
  $("#verdict").innerHTML = side(x) + `<div class="mid">most divergent pair<strong>${p.concl_sim.toFixed(2)}</strong>conclusion similarity · ${p.disagree ? "they disagree" : "no stance disagreement"}</div>` + side(y);
  $("#verdict").hidden = false;
}

function sweepChart() {
  const keys = ["semantic_diversity", "branch_diversity", "disagreement_rate", "path_similarity", "conclusion_similarity"];
  const cols = [COLOR.imagine, COLOR.introspect, COLOR.doubt, COLOR.reason, COLOR.memory];
  const X = (d) => 40 + d * 520, Y = (v) => 220 - v * 200;
  const pts = sweep.slice().sort((a, b) => a.delta - b.delta);
  const lines = keys.map((k, i) => `<polyline fill="none" stroke="${cols[i]}" stroke-width="1.5" points="${pts.map((p) => `${X(p.delta)},${Y(p.m[k])}`).join(" ")}"/>` +
    pts.map((p) => `<circle cx="${X(p.delta)}" cy="${Y(p.m[k])}" r="2.5" fill="${cols[i]}"/>`).join("")).join("");
  const axis = [0, 0.3, 0.6, 1].map((d) => `<text x="${X(d)}" y="242" fill="#8b8a85" font-size="10" text-anchor="middle" font-family="IBM Plex Mono">Δ ${d}</text>`).join("") +
    [0, 0.5, 1].map((v) => `<line x1="40" x2="560" y1="${Y(v)}" y2="${Y(v)}" stroke="rgba(233,230,223,.08)"/><text x="30" y="${Y(v) + 3}" fill="#8b8a85" font-size="10" text-anchor="end" font-family="IBM Plex Mono">${v}</text>`).join("");
  const legend = keys.map((k, i) => `<text x="580" y="${30 + i * 18}" fill="${cols[i]}" font-size="10" font-family="IBM Plex Mono">${MLABEL[k][0]}</text>`).join("");
  $("#sweepchart").innerHTML = `<svg viewBox="0 0 760 250">${axis}${lines}${legend}</svg>`;
}

async function loadRuns() {
  const data = await (await fetch(STATIC ? "../data/index.json" : "/api/runs")).json();
  const rows = Array.isArray(data) ? data : data.runs;
  if (!rows.length) { $("#runs").innerHTML = '<p class="hint">No finished runs yet.</p>'; return; }
  const k = Object.keys(MLABEL);
  $("#runs").innerHTML = `<div class="tablewrap"><table><tr><th>run</th><th>condition</th><th>Δ</th>${k.map((x) => `<th>${MLABEL[x][0]}</th>`).join("")}<th>model</th><th>question</th></tr>` +
    rows.reverse().map((r) => `<tr class="runrow${r.failed?.length ? " failed" : ""}" data-id="${r.id}" title="${r.failed?.length ? "failed run: the LLM was unreachable for " + r.failed.join(", ") : "replay this run"}"><td>${r.id.slice(0, 15)}${r.failed?.length ? " · failed" : ""}</td><td>${r.condition}</td><td>${r.delta}</td>${k.map((x) => `<td>${r.metrics[x]}</td>`).join("")}<td>${esc((r.models || [""])[0])}</td><td>${esc(r.question.slice(0, 60))}</td></tr>`).join("") + "</table></div>";
}

// Re-open a finished run from the log: same events, replayed from its saved snapshots.
document.addEventListener("click", async (e) => {
  const row = e.target.closest(".runrow");
  if (!row) return;
  openRun(row.dataset.id);
});

async function openRun(id) {
  replay(await (await fetch(STATIC ? `../data/runs/${id}.json` : "/api/runs/" + id)).json());
  if (STATIC) history.replaceState(null, "", "?run=" + id);
  scrollTo({ top: 0, behavior: "smooth" });
}

// Replay a saved run step by step. Intermediate graphs are rebuilt from each node's creation step; when a node
// was rejected or an experiment resolved is not saved, so those show their final status only on the last frame.
let replayTimer = null, replaying = null;
function replay(r) {
  clearTimeout(replayTimer);
  replaying = r;
  const names = Object.keys(r.agents);
  sweep = []; lastMetrics = null;
  onEvent({ type: "run_start", ...r, profiles: names, runs: 1, run: 0,
    policies: Object.fromEntries(names.map((n) => [n, { budget: r.agents[n].step, learning_rate: 0.4 }])) });
  const label = (r.failed?.length ? " · failed run (LLM unreachable)" : "") + " · replay of saved run " + r.id;
  const at = (st, s) => {
    if (s >= st.step) return st;
    // a node made during step k carries step k-1 (the counter moves after the operation); start made step-0 claims
    const made = (x) => (s === 0 ? x.step === 0 && (x.type === "hypothesis" || x.type === "premise") : x.step < s);
    const nodes = st.nodes.filter(made).map((n) => (n.status === "rejected" ? { ...n, status: "open" } : n));
    const ids = new Set(nodes.map((n) => n.id)), hyps = nodes.filter((n) => n.type === "hypothesis");
    const root = hyps.length ? hyps[hyps.length - 1] : null, xs = st.experiments.filter((x) => x.step < s);
    return { ...st, nodes, root: root?.id ?? null, hypothesis: root?.text ?? "", conclusion: null, step: s,
      edges: st.edges.filter((e) => ids.has(e.src) && ids.has(e.dst)), experiments: xs.map((x) => ({ ...x, status: "pending" })),
      conflicts: xs.map((x) => ({ objection: x.node, target: x.target, status: "open" })),
      history: st.history.slice(0, s + 1), series: st.series.slice(0, s + 1), ...(st.series[s] || {}) };
  };
  const last = Math.max(...names.map((n) => r.agents[n].step));
  const tick = (s) => {
    for (const n of names) {
      const st = r.agents[n], h = st.history[s];
      if (s > st.step) continue;
      if (h && s > 0) onEvent({ type: "op", agent: n, op: h.op, focus: h.focus, why: h.why });
      onEvent({ type: "state", agent: n, state: at(st, s), budget: st.step });
    }
    $("#runinfo").textContent = $("#runinfo").textContent.replace(/ · (reasoning…|replay|failed run).*$/, "") + label + (s < last ? ` · step ${s}/${last}` : "");
    if (s < last) replayTimer = setTimeout(() => tick(s + 1), 420);
    else onEvent({ type: "metrics", metrics: r.metrics, delta: r.delta });
  };
  tick(0);
}

// ------------------------------------------------------------------ landing
$("#delta").oninput = (e) => ($("#dval").textContent = (+e.target.value).toFixed(1));
$("#legend").innerHTML = FN.map((f) => `<span><i style="background:${COLOR[f]}"></i>${f}</span>`).join("");
fetch("/api/models").then((r) => r.json()).then((m) => {
  $("#modelnote").textContent = m.available.length
    ? `local model ${m.default} · ${m.available.length} variant${m.available.length > 1 ? "s" : ""} available for the model condition`
    : "Ollama is not reachable. Start it, then reload.";
}).catch(enterStatic);

async function enterStatic() {
  STATIC = true;
  document.body.classList.add("static");
  $("#again").textContent = "Replay";
  $("#again").onclick = () => replaying && replay(replaying);
  $("#past").click();
  const data = await (await fetch("../data/index.json")).json();
  openRun(new URLSearchParams(location.search).get("run") || data.featured);
}
$("#question").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("#ask").requestSubmit(); } });

$("#ask").onsubmit = async (e) => {
  e.preventDefault();
  const body = { question: $("#question").value, condition: $("#condition").value, delta: +$("#delta").value, quick: $("#quick").checked, memory: $("#memory").value };
  if ($("#sweep").checked) body.deltas = [0, 0.3, 0.6, 1];
  const { id } = await (await fetch("/api/run", { method: "POST", body: JSON.stringify(body) })).json();
  $("#landing").classList.add("leaving");
  setTimeout(() => attach(id), 700);
};

// Follow a job's event stream; the job id lives in the URL hash so a reload re-attaches.
function attach(id) {
  sweep = []; lastMetrics = null;
  history.replaceState(null, "", "#job=" + id);
  $("#landing").hidden = true; $("#lab").hidden = false; $("#metrics").hidden = true; $("#sweepchart").innerHTML = "";
  mode = "lab"; loadRuns();
  const es = new EventSource("/api/events/" + id);
  es.onmessage = (m) => onEvent(JSON.parse(m.data));
  es.onerror = () => es.close();
}
const hashJob = location.hash.match(/job=(\w+)/);
if (hashJob) attach(hashJob[1]);
$("#past").onclick = (e) => {
  e.preventDefault(); mode = "lab"; profiles = [];
  $("#landing").hidden = true; $("#lab").hidden = false; $("#metrics").hidden = true;
  $("#runinfo").textContent = "experiment log · pick a run"; loadRuns();
};
$("#again").onclick = () => { location.hash = ""; location.reload(); };
