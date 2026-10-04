# Aporia · Visual Engine

A localhost prototype of the "intelligence object": a particle-based topological body whose form changes like a mind in reflection. It runs on simulated states or follows the reasoning lab's real cognitive stream (live mode).

## Run

```bash
npm install
npm run dev
```

Opens http://localhost:5277.

## Stack

Vite, React 19, Three.js, React Three Fiber, `@react-three/postprocessing` (bloom + vignette). All geometry and motion are in one custom GLSL point shader (`src/shaders.js`).

## Controls

| Key | Action |
|---|---|
| `1`–`6` | Idle, Exploration, Concentration, Conflict, Insight, Collapse |
| `C` | Cycle mode: auto-transitions through the states |
| `[` / `]` | Lower / raise Δ by 0.1 |
| `L` | Live mode: follow the reasoning lab's real state |

The same controls sit in the bottom-left panel, with a slider for Δ. Typing a question and pressing **Initiate reasoning** plays a scripted run: exploration, conflict, collapse, exploration, concentration, insight, then back to idle.

## How the object is built

**Hidden topology.** 100,000 points each get a fixed `(u, v)` coordinate and four random seeds. The vertex shader maps `(u, v)` onto a twisted elliptical torus: a closed spine (a circle with a saddle fold) carrying an elliptical cross-section that twists 1.5 turns around the loop. The result is a folded band rather than a sphere. A quarter of the points fill the interior so the body reads as volume, and 4.5% become a sparse halo of dust around it. Nothing is stored on the CPU; the whole shape is recomputed per frame on the GPU.

**Deformation.** Layered 3D simplex noise displaces every point. Separately, a flow phase (`uFlow`) advances at a speed set by the current state, so the internal motion is calm at rest and faster while exploring.

**States are weights, not switches.** Each state is a uniform in `[0, 1]`. On every frame the active state eases toward 1 and the others toward 0 (about 1.5 s), so the shader always blends all six deformations. Transitions are continuous morphs, and a state reached mid-transition is a real intermediate form.

| State | What the shader does |
|---|---|
| Idle | slow breathing scale, low noise, cool blue/cyan |
| Exploration | body opens and thickens; filaments extend from a few regions of the spine, each sharing one direction so they read as reaching tendrils, tinted bright |
| Concentration | points pulled toward a focal core and swirled; noise and thickness drop; colour brightens toward cyan |
| Conflict | the loop splits into two poles that separate and counter-rotate; one pole cools, the other warms to amber, with an ember-red turbulent seam between them |
| Insight | each cross-section snaps onto 22 discrete helical ribbons, noise drops and the ribbons brighten to white: a crystallised structure |
| Collapse | one angular region of the band (new region each time) dissolves: its points drift outward and down, dim and redden, while the rest contracts slightly |

**Δ (cognitive differentiation).** Δ changes the geometry itself:
- the band's two cross-section halves become two strands that twist at different rates and separate (internal divergence);
- the spine buckles under a low-frequency noise field, so the loop becomes asymmetric and more complex;
- the strands sample decorrelated noise, raising local turbulence;
- exploration grows more tendrils, and longer ones.

At Δ = 0 the object is one coherent band. Around 0.5 it splits into braided sheets. At 1 it becomes a field of competing folded substructures.

**Colour encodes state**: cool blue and cyan for calm, violet for exploratory spread, amber and ember for tension, white for crystallisation, dim red-violet for dissolution. Points render additively with soft sprites, and the bloom pass turns dense regions into glow.

## Live mode (real cognitive state)

Press `L` (or **Live lab**) to drive the object from the reasoning lab instead of the simulated states. Start the lab first with `bash lab/run.sh` (port 8740). The page subscribes to `http://localhost:8740/api/live` (spec: `lab/STREAM.md`), and **Initiate reasoning** then starts a real run (`POST /api/run`, condition `architecture`, Δ from the slider).

| Lab signal | Effect on the object |
|---|---|
| `levels.curiosity` (mean over reasoners) | exploration: the body opens up and grows tendrils |
| `levels.uncertainty` × (1 − confidence) | diffusion: thicker, noisier shell |
| `levels.contradiction`, `contradiction` events | conflict: two poles and a warm seam |
| `attention` events | concentration impulse, scaled by the op's probability |
| `insight` events | crystallisation impulse |
| `rejection` events | one region collapses |
| `curiosity` events | exploration impulse |
| `run_start.delta` | Δ geometry |
| `op` | the running function's colour (memory amber, doubt red, counterfactual cyan…) tints the body and fades out |

Events are impulses that decay over 2–3 s; levels set the baseline. The readout shows the current operation and reasoner. If the lab isn't running, the readout says `lab offline` and the object rests; keys `1`–`6` and `C` return to the simulated states.

## Integration later

`<Engine state delta />` in `src/Engine.jsx` is the whole visual. A real reasoning engine only has to drive those two props (or set the state uniforms directly for blended states) from its internal state.

## Files

- `src/shaders.js`: topology, state deformations, colour (GLSL)
- `src/Engine.jsx`: particle buffer, state easing, flow clock, rotation
- `src/live.js`: lab stream client, maps cognitive events to state weights
- `src/App.jsx`: page, controls, cycle and scripted run
- `src/styles.css`: typography and layout
