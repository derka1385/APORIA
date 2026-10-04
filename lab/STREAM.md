# Cognitive state stream (contract for visual clients)

The lab server (`bash lab/run.sh`, port 8740) streams the real reasoning state as
Server-Sent Events. CORS is open (`*`), so a page on another localhost port can
connect directly.

```js
const es = new EventSource("http://localhost:8740/api/live");   // follows the newest experiment
// or: /api/events/<job id>  (one job, replayed from its start)
es.onmessage = (m) => handle(JSON.parse(m.data));
```

Start an experiment: `POST /api/run` with
`{"question": str, "condition": "architecture"|"prompt"|"model"|"base", "delta": 0..1, "deltas"?: [..], "seed"?: int}`
returns `{"id": job}`.

Every message is one JSON object with `type`, `job`, and for sweeps `run` / `runs`.

## Message types

| type | when | key fields |
|---|---|---|
| `run_start` | a run begins | `question, condition, delta, seed, models[], profiles[], policies{name: policy}` |
| `op` | controller picked an operation | `agent, op, focus (node id), probs{op: p}, why[] (metacognitive signals)` |
| `cog` | a cognitive event (below) | `agent, step, t (ms epoch), kind, ...` |
| `state` | after every step | `agent, budget, state` (full snapshot: nodes, edges, experiments, scalars, history) |
| `metrics` | a run finished | `metrics` (Δ measurements, per-reasoner process stats) |
| `error` | a reasoner failed | `agent?, msg` |
| `done` | job finished | |

`agent` is one of `explorer, formalist, skeptic, synthesizer, minimalist`.

## `cog` kinds

All numbers are in [0, 1] unless noted. `node` is a node id inside that agent's graph.

| kind | meaning (what it should look like) | fields |
|---|---|---|
| `levels` | scalar state after each step (form of the cloud) | `confidence, uncertainty, novelty, surprise, curiosity, contradiction` |
| `attention` | the controller commits compute to a node (local concentration) | `node, op, concentration` (probability the op had) |
| `curiosity` | branch with the highest expected information value (expansion toward it) | `node, value` (unbounded, typically 0-1) |
| `contradiction` | a new attacker/test opened against a node (competing clusters) | `node` (attacker), `target`, `experiment`, `via` (objection, counterexample, counterfactual, formal, evidence, recalled) |
| `rejection` | node rejected; its open children go too (local collapse) | `node, node_type, why` |
| `insight` | a claim survived a strong test, was formally valid, or the conclusion stabilised (crystallisation) | `node, reason` = `survived_test` / `formally_valid` / `stable_conclusion` |
| `association` | literature evidence linked to a node (temporary connection) | `node, source` (literature id) |
| `recall` | long-term memory matched this node or question (déjà vu) | `node, memory_kind, outcome, sim` |
| `reinforce` | a hidden assumption surfaced again and gained importance | `node, recur` (count) |
| `tool` | a tool was called | `tool, ok, summary` |
| `compute` | a surprise spike bought extra steps | `budget` (int) |
| `learning` | in-session learning moved routing | `op, value, multiplier` or `op, note, sim` |

## Colour = cognitive function

`memory #e2a85a, reason #a9c8ff, imagine #b38cff, intuit #ff8fb4, introspect #5fd4c4, doubt #ff6b4f,
counterfactual #3fd0f2, formalize #8c93ff, inquire #ffc999, adjudicate #f0d562, revise #8fe08c, conclude #ffffff`.

Node type → function: hypothesis/premise → reason, assumption → introspect, objection/counterexample/contradiction → doubt,
counterfactual → counterfactual, thought_experiment/alternative → imagine, evidence → memory (formal evidence → formalize),
question → inquire, response → adjudicate.
