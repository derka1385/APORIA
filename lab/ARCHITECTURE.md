# APORIA lab: architecture

Research questions:

1. Can artificially differentiated cognitive architectures built around one LLM
   produce meaningfully different reasoning trajectories and conclusions from
   the same philosophical question?
2. Can explicit cognitive functions, dynamically orchestrated around an LLM,
   produce more adaptive, diverse and useful philosophical reasoning than a
   single-pass LLM?

## Environment (inspected 2026-10-04)

- Apple M4, 16 GB, macOS. Python 3.14 (stdlib only), Ollama 0.35.
- Reasoning model `qwen2.5:3b` (~2-4 s per JSON step). Embeddings
  `nomic-embed-text`, with a bag-of-words fallback. Model-condition variants:
  `qwen2.5:3b-instruct-q8_0`, `qwen2.5:3b-instruct-q2_K`, `qwen2.5:1.5b`, `llama3.2:3b`.
- No API keys. Everything runs on localhost.

## LobBot, what it actually does

`~/Coding/lobbot-repo` (github.com/OliverVillson/LobBot) compresses a 30B
mixture-of-experts teacher (Qwen3-30B-A3B) into a ~6.5 GB task model:
`data` (teacher writes ~2k task examples, vLLM) → `reap` (REAP expert pruning:
experts scored by router weight × output norm on the task data, least used 50%
removed per layer) → `heal` (LoRA distillation on teacher answers) →
`quantize` (per-layer bit widths from layer importance and imatrix energy) →
`eval` / `package` (judge vs teacher, GGUF + Ollama Modelfile).

It specialises a model *for a task* by removing what the task does not route
through. That is a real structural change, but it optimises fidelity to one
task distribution; it does not by itself create a cognitive personality. It
needs a CUDA GPU VM (vLLM, TRL, ~60 GB weights), so it cannot run on this Mac.

The honest version of "compression as cognitive differentiation" would
calibrate REAP on *different reasoning corpora* (counterexample generation,
formal derivation, analogy) so each pruned model keeps different experts.
That is a GPU-VM experiment and is not done here. Locally, the `model`
condition uses quantization levels (q8 / q4 / q2 of the same model), a smaller
size and a different family through Ollama.

## Component map

| Layer | v1 | v2 (now) | Where |
|---|---|---|---|
| Structured state | scalars + tree | scalars + typed graph + experiments + learned values | `engine.State` |
| Argument / world model | parent links only | typed nodes (hypothesis, premise, assumption, evidence, objection, counterexample, counterfactual, contradiction, response, question, alternative, thought_experiment) and typed edges (supports, attacks, depends_on, tests, refines, derived_from, analogous_to, responds_to) | `State.add`, `Reasoner.new` |
| Controller | state drives × policy | state drives + metacognitive signals, × policy weight × learned multiplier, softmax(policy temperature) | `Reasoner.choose` |
| Metacognition | none (scalars only) | per-claim assessment from the graph: evidence strength, attackers, unresolved tests, weakest assumption, source quality, formal status. Rules turn it into signals that push specific ops at specific nodes | `assess`, `metacognition` |
| Curiosity | per-node number set by intuition | expected information value: uncertainty × importance (depth, dependents) × missing evidence × novelty × contradiction × learned branch yield × intuition | `curiosity`, `pick_focus` |
| Attention | weighted node score | softmax over curiosity with the policy's explore temperature (0 = exploit) | `pick_focus` |
| Tool use | literature only, implicit | explicit tool layer with per-policy access: literature_search, memory_search, similarity, graph_query, logic_check (truth-table validity + countermodel), theorem_prover (interface, propositional fallback), calculator. `formalize` = LLM translates, the truth table decides | `tools.py`, `op_formalize` |
| Counterfactual reasoning | none | dedicated op choosing a mode from state: decisive assumption (when the target is an assumption), failure world (when the target is confident), minimal change, opposite conditions. Each output becomes an experiment | `op_counterfactual` |
| Adversarial experiments | conflicts | every objection, counterexample, counterfactual, formal countermodel and recalled objection is an experiment; `adjudicate` runs the most informative pending one and records the outcome and information gain | `experiment`, `op_adjudicate` |
| Learning within a session | none | information gain per step updates an EMA value per op (routing), dead-end branches lose yield (attention), hypotheses resembling rejected ones start with a lower prior, recurring assumptions gain load instead of duplicating | `learn`, `op_revise`, `new` |
| Long-term memory | none | SQLite `memory.db`: hypotheses (survived / rejected), objections (defeated / failed), assumptions (recurrence), counterfactuals, unresolved questions, trajectories, question outcomes. Recalled by embedding similarity: shifts the prior of a hypothesis seen before, brings back objections that defeated similar claims as live experiments, revives unresolved questions, lowers node novelty | `ltm.py`, `recall_start`, `op_memory`, `memories` |
| Decide next question | none | `inquire` poses the sub-question most likely to move confidence, then answers it later | `op_inquire` |
| Cognitive diversity | Δ-scaled policy vectors | same, plus explore temperature, learning rate, long-term memory access and tool access | `profiles.py` |
| Measurement | Δ metrics | + per-reasoner process: hypotheses, rejected / surviving, experiments, resolution rate, defeats, novelty, information gain per step, tool calls, recalls, compute allocation by function | `metrics.py` |
| Visual connection | state-driven nebula | + `cog` event stream (STREAM.md) for any visual client | `server.py /api/live` |

## The loop

```
          ┌──────────── metacognition reads the graph ───────────┐
          │  "confident but weakly supported" → doubt            │
          │  "rests on a weak assumption"     → counterfactual   │
          │  "unresolved contradiction"       → adjudicate       │
          │  "assumptions unexamined"         → introspect       │
          │  "never tested counterfactually"  → counterfactual   │
          │  "not formally checked"           → formalize (tool) │
          │  "stagnating"                     → imagine / revise │
          ▼                                                      │
 controller: drive(op) = (state drive + signals) × policy weight × learned value
          ▼                                                      │
 attention: branch ~ softmax(curiosity / explore)               │
          ▼                                                      │
 operation (LLM call and/or tool) edits graph, opens or resolves experiments
          ▼                                                      │
 learning: information gain → op value, branch yield ────────────┘
```

At the end of a run every reasoner writes what it learned to long-term memory,
so the next session on a related question starts from it.

## Profiles and Δ

A profile is a vector of real parameters: op weights, controller temperature,
explore temperature, learning rate, LLM temperature / top_p, context
visibility, literature k and spread, long-term memory k, tool access, branch
factor, objections per doubt, adversarial intensity, acceptance threshold,
rejection threshold, stop confidence, minimum steps, budget, surprise bonus,
assumption cap.

`param = base + Δ · (target − base)`; tool lists switch at Δ ≥ 0.5. At Δ = 0
every reasoner has the base policy and only seeds differ.

- Explorer: imagination, intuition, counterfactuals, inquiry; high explore and
  sampling temperature; no formal tools.
- Formalist: verification and formalization; strict acceptance; near-greedy
  attention; all tools.
- Skeptic: doubt, counterfactuals, adjudication; 4 objections per doubt; 1.8×
  damage; long-term memory of objections; no literature.
- Synthesizer: memory with deliberately distant literature, 8 recalled
  memories, wide context, fast learning; no formal tools.
- Minimalist: introspection and formalization; at most 2 assumptions; narrow
  context; no literature or long-term memory.

## Conditions

- `base`: identical policies, no persona (noise floor).
- `prompt`: identical policies, a persona sentence whose strength scales with Δ.
- `architecture`: policy vectors scale with Δ, no persona.
- `model`: base policies; each reasoner on a different model variant (Δ < 0.15 = all default).

## Metrics

Across reasoners: semantic diversity (1 − symmetric best-match cosine of
argument sets), branch diversity (Jensen–Shannon distance of node-type
distributions), disagreement rate (stance differs or credence differs by
> 0.3), unique hypotheses / assumptions / objections (no match ≥ 0.8 cosine
in any other reasoner), reasoning-path similarity (1 − normalised edit
distance of op sequences), conclusion similarity. Per reasoner: see the
component map.

## Experimental or not done

- REAP-based model differentiation (needs the GPU VM, see LobBot above).
- Activation steering and adapters: Ollama does not expose activations.
- First-order theorem proving: interface only (`tools.theorem_prover`).
- Metrics rely on a small embedding model; treat absolute values as rough
  and compare conditions against the `base` noise floor.
