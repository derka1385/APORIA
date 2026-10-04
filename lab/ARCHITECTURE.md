# APORIA: architecture

Research question: can artificially differentiated cognitive architectures built
around one LLM produce meaningfully different reasoning trajectories and
conclusions from the same philosophical question?

## Environment (inspected 2026-10-04)

- Apple M4, 16 GB, macOS. Python 3.14, Node 26, Ollama 0.35 (server running).
- Model: `qwen2.5:3b` via Ollama (fits easily, ~3-6 s per JSON step).
  Embeddings: `nomic-embed-text` via Ollama, bag-of-words fallback.
- No external API keys are used. Everything runs on localhost.

## LobBot, what it actually does

`~/Coding/lobbot-repo` (github.com/OliverVillson/LobBot) compresses a 30B
mixture-of-experts teacher (Qwen3-30B-A3B) into a ~6.5 GB task model:

1. `data`: the teacher writes ~2k examples for one task (vLLM).
2. `reap`: REAP expert pruning. Each expert is scored by router weight x
   output norm on the task data; the least used 50% are removed per layer.
3. `heal`: LoRA distillation of the pruned model on teacher answers.
4. `quantize`: per-layer bit widths from layer importance + imatrix energy.
5. `eval` / `package`: judge vs teacher, emit GGUF + Ollama Modelfile.

So LobBot specialises a model *for a task*, by removing what the task does not
route through. That is a real structural modification, but it optimises
fidelity to one task distribution; it does not by itself create a "cognitive
personality". It also needs a CUDA GPU VM (vLLM, TRL, ~60 GB weights), so it
cannot run on this Mac.

How it could create differentiated reasoners (experimental, not done here):
calibrate REAP on *different* reasoning corpora (counterexample generation,
formal derivation, analogy) so each pruned model keeps different experts, then
run each profile on its own pruned model. That is the honest version of
"compression as cognitive differentiation", and it is a GPU-VM job.

What is feasible locally today as the model-level condition: the same base
model at different quantization levels (q2/q4/q8 tags lose different
precision), and different small model families. The `model` condition uses
whatever variants are pulled in Ollama.

## Design

```
question ─► 5 reasoners (same engine, different policy vectors) ─► metrics
              │
              ▼
       ┌─ controller ◄──────────── shared cognitive state ──┐
       │  scores every operation from the state + policy    │
       │  softmax(policy temperature) picks op, attention    │
       │  picks the focus node                               │
       ▼                                                     │
   operation (one LLM call, JSON out) ── updates state ──────┘
```

### Cognitive state (per reasoner, `engine.py: State`)

`hypothesis`, an argument graph of typed nodes (claim, premise, assumption,
objection, counterexample, thought_experiment, alternative, evidence), each
with status (open / supported / rejected / stable) and confidence; scalars
`confidence`, `uncertainty`, `novelty`, `surprise`; `curiosity` per node;
`conflicts` (unresolved contradictions); full op history and time series.

### Operations (cognitive functions)

| op | question | state effect |
|---|---|---|
| memory | what already exists? | retrieves literature entries (k by policy), adds evidence, lowers novelty |
| reason | does this follow? | verifies focus node: supported / rejected; moves confidence |
| imagine | alternative / thought experiment? | adds branches (count = branch factor), raises novelty |
| intuit | promising direction before verification? | sets curiosity on nodes |
| introspect | what does my conclusion depend on? | adds hidden assumptions, raises uncertainty |
| doubt | how could this be wrong? | adds objections / counterexamples, opens conflicts |
| adjudicate | does the objection survive? | resolves a conflict; surviving objection raises surprise, lowers confidence, may reject the hypothesis |
| revise | update the hypothesis | rewrites the hypothesis from surviving material |
| conclude | final position | stance + credence; ends the run |

Attention is the focus choice; curiosity is the per-node value attention uses;
decision is the controller's op choice. They are code, not LLM calls.

### Controller (`engine.py: Controller`)

Each op gets a drive computed from state, multiplied by the policy weight:
verify ∝ uncertainty, memory ∝ novelty·(1−confidence), doubt ∝
confidence·adversarial pressure, adjudicate ∝ open conflicts, imagine ∝
curiosity, introspect ∝ novelty of hypothesis vs. assumptions found, conclude
when confidence > stop threshold and no conflicts, or budget runs out.
High surprise grants extra budget. The op is sampled with the policy's
temperature from a seeded RNG, so runs are reproducible.

### Profiles and Δ (`profiles.py`)

A profile is a vector of real parameters: op weights, controller temperature,
LLM temperature / top_p, context visibility (how many graph nodes the LLM
sees), literature k, branch factor, objections per doubt, premise acceptance
threshold, stop confidence, step budget, surprise budget bonus, focus policy
(curiosity vs. surprise vs. confidence vs. recency).

`param(profile) = base + Δ · (profile_target − base)`. At Δ=0 every reasoner
has the base policy (only seeds differ); at Δ=1 each has its full profile.
Explorer, Formalist, Skeptic, Synthesizer, Minimalist.

### Experimental conditions

- `base`: identical policies, no persona, Δ ignored (noise floor).
- `prompt`: identical controller; a persona sentence whose strength scales with Δ.
- `architecture`: the policy vectors above scale with Δ, no persona text.
- `model`: base policies, no persona; each reasoner runs on a different model
  variant (quantization level or family). Δ < 0.15 puts them all on the default model.

### Metrics (`metrics.py`)

Pairwise across reasoners, from embeddings of their own nodes:
semantic diversity (1 − mean cosine of argument-set centroids), branch
diversity (Jensen–Shannon distance of node-type distributions), disagreement
rate (pairs whose stance differs or credence differs by >0.3), unique
assumptions / objections (no match above 0.8 cosine in any other reasoner),
path similarity (1 − normalised edit distance of op sequences), conclusion
similarity (cosine of final positions). A sweep runs Δ ∈ {0, .3, .6, 1}.

### UI (`static/`)

Landing: "What should we investigate?" → lab. Canvas particle nebula with
one cloud per reasoner, driven only by streamed state: spread = uncertainty,
cohesion = confidence, outward drift = curiosity, split into two competing
clusters while conflicts are open, flashing links on memory/synthesis, a
fading burst on rejection, colour = active cognitive function. Per-reasoner
trajectory strip, confidence/uncertainty traces, argument tree with rejected
branches struck through, final position. Metrics panel and a divergence
callout naming the most different pair.

## Experimental / not done

- REAP-based model differentiation (needs GPU VM, see above).
- Activation steering, adapters: not attempted; small models via Ollama do
  not expose activations.
- Metrics use a small embedding model; treat absolute values as rough.
