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

export function connectLive(onInfo) {
  const levels = {} // agent -> latest levels
  const imp = { focus: 0, insight: 0, collapse: 0, conflict: 0, explore: 0 }
  const live = { delta: 0, tint: new THREE.Color('#a9c8ff'), tintAmt: 0, uncertainty: 0, connected: false }
  const bump = (k, v) => { imp[k] = Math.min(1, Math.max(imp[k], v)) }

  const es = new EventSource(`${LAB}/api/live`)
  es.onopen = () => { live.connected = true; onInfo({ connected: true }) }
  es.onerror = () => { live.connected = false; onInfo({ connected: false }) }
  es.onmessage = (m) => {
    const e = JSON.parse(m.data)
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
  live.close = () => es.close()
  return live
}
