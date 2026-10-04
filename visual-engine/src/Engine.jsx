import { useMemo, useRef } from 'react'
import { useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { vertexShader, fragmentShader } from './shaders.js'

export const STATES = ['idle', 'explore', 'focus', 'conflict', 'insight', 'collapse']
const UNIFORM = { idle: 'uIdle', explore: 'uExplore', focus: 'uFocus', conflict: 'uConflict', insight: 'uInsight', collapse: 'uCollapse' }
// how fast the internal flow field advances in each state
const SPEED = { idle: 0.25, explore: 0.75, focus: 0.45, conflict: 0.6, insight: 0.2, collapse: 0.5 }

const COUNT = 180_000

export default function Engine({ state, delta, live }) {
  const pointer = useThree((s) => s.pointer)
  const group = useRef()

  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry()
    const uv = new Float32Array(COUNT * 2)
    const seed = new Float32Array(COUNT * 4)
    for (let i = 0; i < COUNT; i++) {
      uv[i * 2] = Math.random()
      uv[i * 2 + 1] = Math.random()
      for (let k = 0; k < 4; k++) seed[i * 4 + k] = Math.random()
    }
    // position is unused (computed in the shader) but three needs it for draw count
    g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(COUNT * 3), 3))
    g.setAttribute('aUV', new THREE.BufferAttribute(uv, 2))
    g.setAttribute('aSeed', new THREE.BufferAttribute(seed, 4))
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 10)
    return g
  }, [])

  const material = useMemo(() => {
    const uniforms = {
      uTime: { value: 0 }, uFlow: { value: 0 }, uSize: { value: 2.2 },
      uPixelRatio: { value: Math.min(window.devicePixelRatio, 2) },
      uDelta: { value: 0 }, uCollapseAngle: { value: 0 },
      uUncertainty: { value: 0 }, uTint: { value: new THREE.Color() }, uTintAmt: { value: 0 },
    }
    for (const s of STATES) uniforms[UNIFORM[s]] = { value: s === 'idle' ? 1 : 0 }
    const m = new THREE.ShaderMaterial({
      uniforms, vertexShader, fragmentShader,
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    })
    if (import.meta.env.DEV) window.__aporia = m // inspect uniforms from devtools
    return m
  }, [])

  useFrame((_, dtRaw) => {
    const dt = Math.min(dtRaw, 0.1)
    const u = material.uniforms
    const k = 1 - Math.exp(-dt * 1.3) // ~1.5s morph between states
    // live: targets come from the lab's cognitive stream; otherwise the picked state is one-hot
    const target = live ? live.step(dt) : null
    let speed = 0
    for (const s of STATES) {
      const w = u[UNIFORM[s]]
      w.value += ((target ? target[s] : s === state ? 1 : 0) - w.value) * k
      speed += SPEED[s] * w.value
    }
    // new collapse region only while the previous collapse has healed
    if ((target ? target.collapse > 0.5 : state === 'collapse') && u.uCollapse.value < 0.02) u.uCollapseAngle.value = Math.random() * Math.PI * 2
    u.uDelta.value += ((live ? live.delta : delta) - u.uDelta.value) * k
    u.uUncertainty.value += ((live ? live.uncertainty : 0) - u.uUncertainty.value) * k
    if (live) u.uTint.value.copy(live.tint)
    u.uTintAmt.value = live ? live.tintAmt : 0
    speed += u.uDelta.value * 0.25
    u.uFlow.value += dt * speed
    u.uTime.value += dt

    const g = group.current
    g.rotation.y += dt * (0.05 + 0.1 * speed)
    g.rotation.x += (0.38 + pointer.y * 0.15 - g.rotation.x) * 0.03
    g.rotation.z += (-pointer.x * 0.12 - g.rotation.z) * 0.03
  })

  return (
    <group ref={group} position={[0, 0.3, 0]}>
      <points geometry={geometry} material={material} frustumCulled={false} />
    </group>
  )
}
