# Submission draft — APORIA

**Challenge:** 3 — Agentic Scientific Discovery

## One-liner
APORIA is an AI research lab that makes *how an agent thinks* the experimental variable. Five reasoners on one LLM get
the same question and differentiated cognitive policies, and the lab measures how differently they actually reasoned.

## Short description (≈100 words)
Agent swarms built on one LLM converge: same moves, same objections, same answer. APORIA externalizes the cognitive
functions around the model as explicit, measurable machinery: a typed argument graph, metacognition, curiosity as
expected information value, counterfactual and adversarial experiments, memory, a truth-table checker and in-session
learning. Five reasoners (explorer, formalist, skeptic, synthesizer, minimalist) run the same engine with different
policy vectors, and one parameter, Δ, sets how far apart those policies are. On Qwen3-30B (evroc VM), raising Δ made
the five research processes measurably more different. Conclusions still converge, and the lab reports that too.

## What is new
- **Cognition as a controlled variable.** Profiles are policy vectors (about twenty real parameters: operation weights,
  attention temperature, thresholds, tool and memory access, adversarial damage), not persona prompts. A `prompt`
  condition, with persona sentences and identical policies, is the control.
- **An experiment loop inside each reasoner.** Metacognition reads the graph ("confident but weakly supported",
  "rests on an untested assumption") and pushes specific operations at specific nodes. Every objection, counterfactual
  and formal countermodel becomes an experiment that is adjudicated, and information gain retrains routing during the run.
- **Measured divergence, never rewarded.** Path similarity, branch diversity, unique objections, assumptions and
  hypotheses, disagreement and conclusion similarity are computed from what each reasoner produced alone. No reasoner
  is told to disagree.
- **Live, inspectable state.** Every cognitive event streams over SSE to a lab UI (five growing argument graphs) and to
  a particle object whose form follows the real state. The site replays recorded runs.
- **Compression as a cognitive intervention (next).** LobBot TaskSpecs per profile, seeded with that profile's real
  outputs, so REAP expert pruning can give each reasoner different experts of Qwen3-30B-A3B.

## Results (Qwen3-30B, one question, five reasoners per run; generated in `README.md`)
- Δ 0 → Δ 1, architecture condition: path similarity 0.44 → 0.28, branch diversity 0.44 → 0.62, unique objections
  0.5 → 4 (Δ 0: n = 2, Δ 1: n = 1; the remaining sweep points are in the README table).
- At Δ 1: architecture 0.28 path similarity vs 0.33 for persona prompts and 0.46 for identical policies.
- Conclusion similarity stays around 0.9 in every condition. Different processes, so far, the same answer.

## Honest limits
Small n (one or two runs per condition, one question); the verdicts inside the loop are the same LLM's judgements;
similarity uses a small embedding model; the model-variant condition failed once when the VM tunnel dropped, and that
run is shown as failed and excluded. No compression result yet.

## Built with
Python standard library (engine, server, metrics), Ollama, Qwen3-30B on an evroc GPU VM, Qwen2.5-3B locally,
nomic-embed-text, React Three Fiber + GLSL for the particle object, plain HTML/JS for the lab UI, LobBot for the
compression extension.

## Links to fill in
- Live demo: https://derka1385.github.io/APORIA/ (after enabling Pages: Settings → Pages → main, /docs)
- Video: <record from docs/DEMO.md>
- Repo: https://github.com/derka1385/APORIA
