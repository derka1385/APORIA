import { useEffect, useRef, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { EffectComposer, Bloom, Vignette } from '@react-three/postprocessing'
import Engine, { STATES } from './Engine.jsx'
import { connectLive, LAB } from './live.js'

const LABEL = {
  idle: 'Idle', explore: 'Exploration', focus: 'Concentration',
  conflict: 'Conflict', insight: 'Insight', collapse: 'Collapse',
}
const CAPTION = {
  idle: 'at rest',
  explore: 'searching idea-space',
  focus: 'allocating compute',
  conflict: 'competing lines of thought',
  insight: 'a structure stabilises',
  collapse: 'a hypothesis dissolves',
}
// [state, seconds]: ambient cycle and the scripted "reasoning" run
const CYCLE = [['idle', 5], ['explore', 6], ['conflict', 6], ['focus', 5], ['insight', 5], ['collapse', 4], ['explore', 5], ['insight', 6]]
const RUN = [['explore', 5], ['conflict', 5], ['collapse', 3.5], ['explore', 4], ['focus', 4], ['insight', 7], ['idle', 0]]

export default function App() {
  const [state, setState] = useState('idle')
  const [delta, setDelta] = useState(0.3)
  const [cycling, setCycling] = useState(false)
  const [question, setQuestion] = useState('')
  const [active, setActive] = useState('') // question currently being "reasoned"
  const timer = useRef()
  const [live, setLive] = useState(null) // connection to the lab's cognitive stream
  const [info, setInfo] = useState({})

  const stop = () => { clearTimeout(timer.current); setCycling(false); setActive('') }
  const play = (seq, loop, onDone) => {
    clearTimeout(timer.current)
    const step = (i) => {
      if (i >= seq.length) return loop ? step(0) : onDone?.()
      const [s, secs] = seq[i]
      setState(s)
      timer.current = setTimeout(() => step(i + 1), secs * 1000)
    }
    step(0)
  }
  const leaveLive = () => { live?.close(); setLive(null); setInfo({}) }
  const toggleLive = () => {
    if (live) return leaveLive()
    stop()
    setLive(connectLive((i) => {
      setInfo((p) => ({ ...p, ...i }))
      if (i.done) setActive('')
    }))
  }
  const pick = (s) => { leaveLive(); stop(); setState(s) }
  const toggleCycle = () => {
    if (cycling) return stop()
    leaveLive()
    setActive(''); setCycling(true); play(CYCLE, true)
  }
  const initiate = (e) => {
    e.preventDefault()
    const q = question.trim()
    if (!q) return
    setCycling(false); setActive(q)
    if (!live) return play(RUN, false, () => setActive(''))
    fetch(`${LAB}/api/run`, {
      // text/plain keeps it a simple CORS request (the lab answers no preflight); it parses the JSON body anyway
      method: 'POST',
      body: JSON.stringify({ question: q, condition: 'architecture', delta }),
    }).catch(() => { setActive(''); setInfo((p) => ({ ...p, connected: false })) })
  }

  useEffect(() => {
    const onKey = (e) => {
      if (e.target.tagName === 'INPUT') return
      const i = Number(e.key) - 1
      if (i >= 0 && i < STATES.length) pick(STATES[i])
      if (e.key === 'c') toggleCycle()
      if (e.key === 'l') toggleLive()
      if (e.key === '[') setDelta((d) => Math.max(0, +(d - 0.1).toFixed(2)))
      if (e.key === ']') setDelta((d) => Math.min(1, +(d + 0.1).toFixed(2)))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  })
  useEffect(() => () => clearTimeout(timer.current), [])
  useEffect(() => () => live?.close(), [live])

  return (
    <>
      <Canvas camera={{ position: [0, 0, 6.2], fov: 42 }} dpr={[1, 1.5]} gl={{ antialias: false }}>
        <color attach="background" args={['#030407']} />
        <Engine state={state} delta={delta} live={live} />
        <EffectComposer multisampling={0}>
          <Bloom mipmapBlur intensity={0.9} luminanceThreshold={0.15} luminanceSmoothing={0.4} radius={0.7} />
          <Vignette offset={0.25} darkness={0.85} />
        </EffectComposer>
      </Canvas>

      <header className="brand">
        <span>APORIA</span>
        <span className="dim">cognitive engine · visual prototype</span>
      </header>

      <div className="readout">
        {live ? (
          <>
            <div className="mono dim">{info.connected === false ? 'lab offline · :8740' : 'live'}</div>
            <div className="state">{info.op || 'listening'}</div>
            <div className="caption">{info.agent || (info.done ? 'run complete' : 'waiting for a run')}</div>
            <div className="mono dim">Δ {(info.delta ?? 0).toFixed(2)}</div>
          </>
        ) : (
          <>
            <div className="mono dim">state</div>
            <div className="state">{LABEL[state]}</div>
            <div className="caption">{CAPTION[state]}</div>
            <div className="mono dim">Δ {delta.toFixed(2)}</div>
          </>
        )}
      </div>

      <main className="hero">
        {active ? (
          <p className="question">“{active}”</p>
        ) : (
          <form onSubmit={initiate}>
            <h1>What should we investigate?</h1>
            <div className="ask">
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Is personal identity dependent on psychological continuity?"
              />
              <button type="submit">Initiate reasoning</button>
            </div>
          </form>
        )}
      </main>

      <aside className="panel">
        {STATES.map((s, i) => (
          <button key={s} className={!live && s === state ? 'on' : ''} onClick={() => pick(s)}>
            <span className="mono dim">{i + 1}</span>{LABEL[s]}
          </button>
        ))}
        <button className={cycling ? 'on' : ''} onClick={toggleCycle}>
          <span className="mono dim">C</span>Cycle
        </button>
        <button className={live ? 'on' : ''} onClick={toggleLive}>
          <span className="mono dim">L</span>Live lab
        </button>
        <label className="delta">
          <span>Cognitive differentiation <b>Δ</b></span>
          <input type="range" min="0" max="1" step="0.01" value={delta} onChange={(e) => setDelta(+e.target.value)} />
          <span className="mono dim scale"><i>unified</i><i>divergent</i></span>
        </label>
      </aside>
    </>
  )
}
