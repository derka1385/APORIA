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
policy vectors, and one parameter, Δ, sets how far apart those policies are. On Qwen3-30B (evroc VM), raising Δ from 0 to 1
cut the similarity of the five research paths from 0.44 to 0.30 and multiplied unique objections by five.
Conclusions still converge, and the lab reports that too.

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

## Results (Qwen3-30B on an evroc VM, one question, five reasoners per run; table in `README.md`)
- Δ sweep, two paired seeds per level: from Δ 0 to Δ 1 path similarity falls 0.44 → 0.30, branch diversity rises
  0.44 → 0.56 and unique objections per run rise 0.5 → 2.5. The change appears from Δ 0.75; Δ 0.25 and 0.5 stay at
  the noise floor.
- The Δ 0 → Δ 1 shift replicates on four questions (personal identity, machine understanding, free will, scientific
  realism): path similarity falls on 4 of 4, branch diversity rises on 4 of 4, unique objections rise on 3 of 4.
- At Δ 1: path similarity 0.30 with policy vectors, 0.33 with persona prompts, 0.46 with identical policies.
- Different model families (the `model` condition) give the most unique objections (5) and the highest semantic
  diversity (0.18) but the lowest branch diversity (0.36). Models change the content; policies change the process.
- Conclusion similarity stays between 0.89 and 0.94 in every condition: different processes, so far, the same answer.

## Honest limits
Small n (one or two runs per condition; the full sweep on one question, Δ 0 / Δ 1 on four); the verdicts inside the loop are the same LLM's judgements;
similarity uses a small embedding model; a dropped VM tunnel once produced empty runs; runs whose reasoners mostly
got no answer are flagged and never analysed, and the batch now stops when the endpoint is down. No compression result yet.

## Built with
Python standard library (engine, server, metrics), Ollama, Qwen3-30B on an evroc GPU VM, Qwen2.5-3B locally,
nomic-embed-text, React Three Fiber + GLSL for the particle object, plain HTML/JS for the lab UI, LobBot for the
compression extension.

## Links to fill in
- Live demo: https://derka1385.github.io/APORIA/ (after enabling Pages: Settings → Pages → main, /docs)
- Video: <record from docs/DEMO.md>
- Repo: https://github.com/derka1385/APORIA
