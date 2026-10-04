// Live mode: drives the engine from the lab's real cognitive stream (lab/STREAM.md).
// Scalar `levels` set the slow form, discrete `cog` events add decaying impulses.
import * as THREE from 'three'

export const LAB = 'http://localhost:8740'

const FUNC_COLOR = {
  memory: '#e2a85a', reason: '#a9c8ff', imagine: '#b38cff', intuit: '#ff8fb4', introspect: '#5fd4c4',
  doubt: '#ff6b4f', counterfactual: '#3fd0f2', formalize: '#8c93ff', inquire: '#ffc999',
  adjudicate: '#f0d562', revise: '#8fe08c', conclude: '#ffffff',
}
// impulse half-lives in seconds
const HALF = { focus: 2, insight: 3, collapse: 2.5, conflict: 3, explore: 3 }

// replay: URL of a recorded run (lab/runs/*.json); events are rebuilt from its trace and fed to the same handler
export function connectLive(onInfo, replay) {
  const levels = {} // agent -> latest levels
  const imp = { focus: 0, insight: 0, collapse: 0, conflict: 0, explore: 0 }
  const live = { delta: 0, tint: new THREE.Color('#a9c8ff'), tintAmt: 0, uncertainty: 0, connected: false }
  const bump = (k, v) => { imp[k] = Math.min(1, Math.max(imp[k], v)) }

  const handle = (e) => {
    if (e.type === 'run_start') {
      live.delta = e.delta
      for (const k in levels) delete levels[k]
      onInfo({ question: e.question, delta: e.delta, op: null, agent: null, done: false })
    } else if (e.type === 'op') {
      live.tint.set(FUNC_COLOR[e.op] || '#a9c8ff')
      live.tintAmt = 1
      onInfo({ op: e.op, agent: e.agent, why: e.why })
    } else if (e.type === 'done') {
      onInfo({ done: true })
    } else if (e.type === 'cog') {
      if (e.kind === 'levels') levels[e.agent] = e
      else if (e.kind === 'attention') bump('focus', 0.35 + 0.5 * e.concentration)
      else if (e.kind === 'insight') bump('insight', 1)
      else if (e.kind === 'rejection') bump('collapse', 1)
      else if (e.kind === 'contradiction') bump('conflict', 0.7)
      else if (e.kind === 'curiosity') bump('explore', Math.min(1, 0.4 + 0.5 * e.value))
    }
  }
  let es = null, timer = null
  if (replay) {
    live.connected = true
    fetch(replay).then((r) => r.json()).then((run) => {
      const ticks = replayTicks(run)
      const play = (i) => {
        if (i >= ticks.length) { timer = setTimeout(() => play(0), 4000); return } // loop after a pause
        ticks[i].forEach(handle)
        timer = setTimeout(() => play(i + 1), 650)
      }
      onInfo({ connected: true, replay: run.id })
      play(0)
    }).catch(() => onInfo({ connected: false }))
  } else {
    es = new EventSource(`${LAB}/api/live`)
    es.onopen = () => { live.connected = true; onInfo({ connected: true }) }
    es.onerror = () => { live.connected = false; onInfo({ connected: false }) }
    es.onmessage = (m) => handle(JSON.parse(m.data))
  }

  // called every frame by the engine: decays impulses, returns state weights
  live.step = (dt) => {
    for (const k in imp) imp[k] *= Math.pow(0.5, dt / HALF[k])
    live.tintAmt *= Math.pow(0.5, dt / 2.5)
    const ls = Object.values(levels)
    const avg = (f) => (ls.length ? ls.reduce((a, l) => a + l[f], 0) / ls.length : 0)
    live.uncertainty = avg('uncertainty') * (1 - 0.5 * avg('confidence'))
    const w = {
      explore: Math.max(0.8 * avg('curiosity'), imp.explore),
      conflict: Math.max(avg('contradiction'), imp.conflict),
      focus: imp.focus,
      insight: imp.insight,
      collapse: imp.collapse,
    }
    // keep the blend from overdriving the shape when everything fires at once
    const sum = w.explore + w.conflict + w.focus + w.insight + w.collapse
    if (sum > 1.2) for (const k in w) w[k] *= 1.2 / sum
    w.idle = Math.max(0, 1 - sum)
    return w
  }
  live.close = () => { es?.close(); clearTimeout(timer) }
  return live
}

// One tick per reasoning step, all five reasoners together. Saved runs keep each step's operation, focus,
// probabilities and levels, and when each node and experiment was made (a node made during step k carries
// step k-1); when a node was rejected is not saved, so rejection follows a revision of the hypothesis.
function replayTicks(run) {
  const names = Object.keys(run.agents)
  const last = Math.max(...names.map((n) => run.agents[n].history.length - 1))
  const ticks = [[{ type: 'run_start', delta: run.delta, question: run.question }]]
  for (let s = 1; s <= last; s++) {
    const tick = []
    for (const agent of names) {
      const st = run.agents[agent], h = st.history[s]
      if (!h) continue
      const made = st.nodes.filter((n) => n.step === s - 1 && s > 1)
      const lv = st.series[s] || st.series[st.series.length - 1]
      const open = st.experiments.filter((x) => x.step < s && x.step >= s - 3).length
      const cog = (kind, extra) => tick.push({ type: 'cog', agent, step: s, kind, ...extra })
      tick.push({ type: 'op', agent, op: h.op, focus: h.focus, why: h.why })
      cog('attention', { node: h.focus, op: h.op, concentration: h.probs?.[h.op] ?? 0.3 })
      cog('levels', { ...lv, curiosity: Math.max(0, ...made.map((n) => n.novelty || 0)), contradiction: Math.min(1, open / 3) })
      for (const x of st.experiments.filter((x) => x.step === s - 1)) cog('contradiction', { node: x.node, target: x.target, via: x.kind })
      if (h.op === 'revise' && made.some((n) => n.type === 'hypothesis')) cog('rejection', { node: h.focus, node_type: 'hypothesis', why: 'revised' })
      if (made.some((n) => n.formal && n.type === 'evidence') || h.op === 'conclude') cog('insight', { node: h.focus, reason: h.op === 'conclude' ? 'stable_conclusion' : 'formally_valid' })
      if (['imagine', 'intuit', 'counterfactual', 'inquire'].includes(h.op)) cog('curiosity', { node: h.focus, value: Math.max(0.3, ...made.map((n) => n.novelty || 0)) })
    }
    ticks.push(tick)
  }
  ticks.push([{ type: 'done' }])
  return ticks
}
