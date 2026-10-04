# Crux Lab

**An autonomous AI research lab for philosophy.** Crux Lab reads new papers, reconstructs their
arguments, has AI agents attack single premises, makes other agents defend the argument against
each attack, checks whether the objection has been made before, and hands a human philosopher a
research brief: *here is an open question, here is how far it got, here is what a paper on it
would have to show.*

Built for Hack-Nation's 7th Global AI Hackathon, Challenge 3 "Agentic Scientific Discovery"
(sponsor: Databricks). Topics run so far: **divine hiddenness** (Codex + Claude) and **decision theory in philosophy
of religion** — Newcomb's problem, Pascal's wager, God's choice of world (evroc's open models + Claude, 8 model
families). Any topic can be added with one file (see [Topics](#topics)).

> In philosophy, the debate is the experiment.

**Live site:** https://univerdread.github.io/crux-lab/ (static replay of this repo's results; deployed by
`.github/workflows/pages.yml` on every push to `main` that touches `web/`).

**Who it is for:** philosophers and philosophy students looking for what to research and write
next. The site leads with *research directions*: objections that survived two defenders, ranked by
lead score (survival × novelty × the Assessor's quality grade), each traceable to verbatim quotes and corpus
records.

<!-- RESULTS -->
## What the lab produced (generated from `web/public/data`)

- Corpus: **1212** OpenAlex records (**962** distinct works once duplicate versions are merged; 635 records published since 2026-08-01), **75** open-access full texts.
- Targets: **5** papers; **55** objections generated; **30** full trials; **14** research briefs.
- Model families: degraded: 2 families (anthropic, openai).

| Target | Objections | Trials | Outcomes | Briefs |
| --- | --- | --- | --- | --- |
| Some critical reflections on the hiddenness argument (classic) | 11 | 6 | known_answer 1, misreading 1, revision_required 4 | 3 |
| Divine Hiddenness, Greater Goods, and Accommodation (classic) | 11 | 6 | misreading 3, revision_required 3 | 3 |
| God and the View From Nowhere: De Se Knowledge and Divine Omniscience (fresh) | 12 | 6 | misreading 1, revision_required 5 | 3 |
| DOES GOD EXIST? CAN WE TELL IF WE BASED THIS QUESTION ONLY UPON THE AP (fresh) | 10 | 6 | misreading 4, revision_required 2 | 2 |
| Divine simplicity as symmetric parthood (fresh) | 11 | 6 | misreading 2, revision_required 4 | 3 |

**Academic quality check** (Assessor agent, a journal-referee read of each direction; grade computed from coherence, robustness, significance and specificity): not yet defensible 14 of 14. Each brief shows the strongest objection to it and what the paper would need.

**Revision round** (each direction rewritten to answer its strongest objection, then re-graded in a fresh read): not yet defensible 12, needs work 2 of 14 after revision; overall score up for 9, down for 1.

**Top research directions** (lead score = survival × novelty × Assessor quality/5, best first):

- *Does robust contrastive responsibility require an irreducibly agent-relative mode of representation, or can a rigid third-personal representation of an agent's intention and act suffice?* — revision_required, novelty 0.88, 4140 records searched; assessor: not yet defensible (3.0/5); lead score 0.422. Further human review required.
- *Can a similarity-relative parthood relation adequately track the metaphysical constituency denied by the traditional doctrine of divine simplicity?* — revision_required, novelty 0.92, 4139 records searched; assessor: not yet defensible (2.75/5); lead score 0.405. Further human review required.
- *Does robust contrastive responsibility require irreducibly de se representation of the selected outcome, or only representation of that outcome as resulting from an act the agent performs or selects?* — revision_required, novelty 0.84, 4138 records searched; assessor: not yet defensible (3.0/5); lead score 0.403. Further human review required.
- *Can instantiation be modelled as similarity-based parthood in a way that preserves the persistence of ordinary objects and supports the divine-simplicity application?* — revision_required, novelty 0.82, 4140 records searched; assessor: not yet defensible (3.0/5); lead score 0.394. Further human review required.
- *Does robust contrastive responsibility require an agent to represent the selected outcome as attributable to that agent’s own exercise of control, and if so, must this representation contain irreducible de se content?* — revision_required, novelty 0.86, 4140 records searched; assessor: not yet defensible (2.75/5); lead score 0.378. Further human review required.

**Second topic: Decision theory in philosophy of religion** (8 model families: anthropic, kimi, glm, mistral, qwen, llama, gpt-oss, gemma). 6 papers, 72 objections, 36 trials (24 standing or forcing a revision), 18 research directions. Strongest lead (lead score 0.361): *Does diachronic psychological coherence, read as evidence-responsive, disposition-level coherence rather than persistence of every intention, license the backtracking counterfactuals in c004 that tie a token choice in Newcomb's Problem to the predictor's prediction, and if so, does this support one-boxing as the rational choice?* E1 replicated: 78% (embeddings over claims) vs 28% keyword search (n=50). Switch topics on the site's /topics page.

### Evaluation (automatic, no human labels)

**E1 prior-art recall@5** (n=50; scored per work, duplicate records merged):

| Method | recall@5 | strict, per record |
| --- | --- | --- |
| BM25 over abstracts | 16% (8/50) | 12% |
| embeddings over abstracts | 24% (12/50) | 20% |
| embeddings over claims | 64% (32/50) | 58% |
| claims + 3-way restatement + rerank | 86% (43/50) | 86% |

**E2 gauntlet calibration**: 1/10 published objections labelled known_answer, 1/10 with the correct reply cited and verified; a defender cited (verified) a gold reply in 7/10 items; 10/10 deliberate misreadings labelled misreading.

**E3 diversity ablation**:

| Condition | n | distinct premises / argument | mean pairwise distance | passes pre-screen | novelty > 0.5 |
| --- | --- | --- | --- | --- | --- |
| plain prompt, one model | 20 | 1.8 | 0.114 | 100% | 50% |
| constrained roles, one model | 20 | 2.4 | 0.224 | 85% | 55% |
| constrained roles, mixed families | 20 | 2.6 | 0.213 | 80% | 45% |
<!-- /RESULTS -->

## Screenshots

| Research directions (landing) | Lab replay |
| --- | --- |
| ![Landing page with research directions](docs/screens/landing.png) | ![Lab replay: argument map, trial feed, Director queue](docs/screens/lab.png) |
| **Research brief** | **Results (E1–E3)** |
| ![A research brief](docs/screens/brief.png) | ![Evaluation results](docs/screens/results.png) |

Walkthrough video (Playwright, ~1 minute): [`docs/demo.webm`](docs/demo.webm). Two-minute talk track with
real ids and numbers: [`docs/DEMO.md`](docs/DEMO.md).

## The discovery loop

```
corpus ─▶ argument graph ─▶ objection generation ─▶ gauntlet ─▶ prior-art check ─▶ Director ─▶ research brief
  ▲                                                                                   │
  └──────────────── revised premise becomes a new node and is attacked (depth ≤ 2) ◀──┘
```

1. **Corpus.** OpenAlex: 6 hiddenness queries (phrase matched) plus fresh philosophy-of-religion
   papers published since 2026-08-01 (models cannot recall replies to them). Open-access PDFs are
   downloaded politely (≤ 1 request/second per host) and parsed with PyMuPDF.
2. **Argument graph.** The **Extractor** pulls claims from each target paper chunk by chunk; every
   claim stores a verbatim quote (≤ 2 sentences) that must be found in the source text
   (rapidfuzz `partial_ratio ≥ 90`) or the claim is dropped. It then rebuilds the paper's main
   argument from claim ids. The **Formalizer** writes a propositional skeleton (atoms A–H,
   `~ & | -> <->`); a truth table in `graph/logic.py` decides validity, and a proposed *missing
   premise* is accepted only if the re-check makes the argument valid without making the premises
   inconsistent.
3. **Objections.** Generators never see literature (enforced by construction and tested):
   Blind Thought-Experimenters (one per model), a Hidden-Premise Attacker (must target the
   Formalizer's missing premise), Tradition Lenses (skeptical theism, Molinism, open theism,
   Reformed epistemology, naturalism) and a Naive Questioner whose question only counts once
   another agent sharpens it. Every objection must name a real premise id, give a concrete case,
   stay under 180 words, and cite nothing.
4. **Prior-art check.** Each objection is restated three ways (paper vocabulary, plain English,
   a neighbouring tradition), searched with BM25 + embeddings over claims and abstracts plus a live
   OpenAlex query, and reranked with one question: *does this passage make the same move against
   the same premise?* → `same_move | related | different`, with the passage quoted.
   `novelty = 1 − max similarity among same_move/related matches`. The lab never claims novelty:
   it reports the score, the records searched, the three nearest matches and
   "Further human review required."
5. **Gauntlet.** Referee pre-screen for misreading → retrieved literature for the defenders →
   Defender A replies, the objector rejoins (still without literature), Defender A closes;
   Defender B (more concessive, another model family) repeats independently → the Referee labels
   each defense. The objection keeps the outcome most favourable to the original argument.

   | Outcome | Meaning | Survival S |
   | --- | --- | --- |
   | misreading | Attacks something the argument does not claim | 0.0 |
   | known_answer | A reply in the corpus resolves it, cited by id and verified | 0.1 |
   | rebutted | A defender gave an adequate new reply not found in the corpus | 0.3 |
   | revision_required | The argument survives only by changing or adding a premise | 0.8 |
   | standing | Every defense failed, or a defender conceded | 1.0 |

   Citations are corpus claim ids only; the code verifies each one (it exists and was in the
   literature the defender was shown) and strikes the rest. `known_answer` is impossible without
   a verified citation.
6. **Director** (plain code, no LLM): `priority = S · N · (0.5 + 0.5·C) + 0.1·E`
   (S survival, 0.5 before a trial; N novelty; C share of graph arguments depending on the premise;
   E exploration bonus for an agent/family not yet tried on this argument). Budget per target:
   12 objections, 6 full trials. Queue snapshots are saved for the replay.
7. **Brief.** Research question, the argument, the challenged premise, the objection, the strongest
   responses and why they failed, the closest literature (rendered from corpus records, never from
   model text), novelty, records searched, open questions, and "A paper here would argue…".

## Quickstart

```bash
make setup          # .venv (Python 3.11) + requirements + web deps; copies .env.example → .env
make providers      # probes every candidate model, writes config/resolved_models.json
make corpus         # OpenAlex harvest + open-access full texts → data/corpus.jsonl
make map            # claims, arguments, skeletons, abstract claims, BM25 + embedding indexes
make run TARGET=oa-W2072673546   # one full lab run → data/runs/, data/briefs/
make runs           # all targets in parallel
make eval           # E1–E3 → results/
make export         # → web/public/data/
make demo           # build + preview the site (http://localhost:4680) from the committed export
make check          # pytest (no network) + web typecheck + web unit/replay tests
make smoke          # Playwright: 10 page smoke tests (+ screenshots) and 8 axe accessibility checks
make live-test      # live mode end to end: FastAPI SSE server + a VITE_API_URL build
make docs           # export, then regenerate docs/DEMO.md, README results/limits, docs/AUDIT.md, docs/SUBMISSION.md
make databricks     # claims Delta table + AI Search Delta Sync index (needs workspace credentials)
```

Without `make`: `python -m crux_lab.cli <cmd>`.

**Just want to see it?** `cd web && npm install && npm run build && npm run preview` serves the
committed results (`web/public/data`) — no API keys, no model calls. Re-running the lab needs a model
provider (see below); the claim store and LLM cache it builds stay local (gitignored).

### Topics

The lab works on one topic at a time. A topic is a file in `config/topics/<slug>.yaml`; pick it with
`make <targets> TOPIC=<slug>` (or `CRUX_LAB_TOPIC=<slug>`, or `python -m crux_lab.cli --topic <slug> …`). The default
topic, `divine-hiddenness`, keeps its data in `data/`, `results/` and `web/public/data/`; any other topic gets
`data/topics/<slug>/`, `results/topics/<slug>/` and `web/public/data/topics/<slug>/`, and the site switches
between them on `/topics` (`?topic=<slug>`). The site's **Start a topic** page writes the file with you.

```bash
make corpus targets map runs assess revise export TOPIC=decision-theory
```

| Field | What it does |
| --- | --- |
| `name`, `description`, `area` | Shown on the site; `area` also tells the target screen and the Assessor what field they are in |
| `queries` | label → OpenAlex search string, harvested for the corpus |
| `max_per_query` | records per search (default 400; 200 = one request, useful under the keyless daily allowance) |
| `fresh_from`, `fresh_queries` | searches for papers published since that date (target candidates the models cannot have read replies to) |
| `relevant`, `fresh_relevant` | regexes an abstract must match to enter the corpus; `fresh_relevant` holds broad fresh searches to a stricter test |
| `relevance_levels` | the 0–3 scale the target screen uses |
| `targets` | `fresh`, `classic` (how many of each), `fresh_min_relevance`, and `spread: true` to take classic targets from each search in turn |
| `schools` | the traditions the Tradition-Lens agents argue from |
| `e2_fixture` | optional: a canonical argument with published replies, for the E2 calibration test |

Three topics are configured: divine hiddenness (run overnight on Codex + Claude), decision theory in philosophy
of religion (run on evroc + Claude, see `NOTES.md`), and the fine-tuning argument (set up, not run).

### Model providers

Provider chain, using whatever exists: **Databricks** Model Serving (`DATABRICKS_HOST`,
`DATABRICKS_TOKEN`) → **evroc Think** (`EVROC_API_KEY`; EU-hosted open models — Llama, Qwen, Mistral, gpt-oss,
Kimi, Gemma — behind an OpenAI-compatible API) → **OpenRouter** → **Anthropic API** → subscription CLIs (`codex`
from the ChatGPT app, `claude -p`). With evroc plus one other provider, Defender A, Defender B and the Referee
get three different model families, as the design intends. The CLI providers run as isolated completions: no tools, no shell, no
web, no user config. Every call goes through one client with a disk cache keyed on
`sha256(provider, model, messages, params)`, a spend guard, Pydantic-validated JSON with two
retries carrying the validation error, and an MLflow trace (Databricks experiment when credentials
exist, otherwise local `mlruns/`). `DISABLE_PROVIDERS=codex_cli` (in `.env`) switches a provider off
while cached calls still replay.

## Layout

```
crux_lab/
  config.py  cli.py  export.py  databricks_sync.py
  llm/       client, providers, cache, budget, tracing, resolve
  corpus/    openalex, philarchive_oai, pdf, targets, dedup (same-work detection), build
  graph/     schema, store (SQLite), extract, logic, formalize, index, build
  agents/    roles.py, prompts/*.md
  lab/       debate (exchange engine), generators, novelty, gauntlet, director, brief, run
  eval/      e1_prior_art, e2_calibration, e3_diversity (+ fixtures/)
  api/       server.py (FastAPI + SSE live mode)
scripts/     audit.py (grounding audit), make_demo_md.py, readme_results.py, make_submission_md.py, dedupe_nearest.py
data/        corpus.jsonl, targets.json, runs/, briefs/, map_stats.json (raw texts, SQLite store: local only)
results/     e1.json, e2.json, e3.json (+ e2_v1_discarded.json)
docs/        DEMO.md, SUBMISSION.md, AUDIT.md, CRUX_INVENTORY.md, screens/, demo.webm
web/         Vite + React + TypeScript + Tailwind site (replay by default; VITE_API_URL = live)
```

## Databricks (sponsor)

Wired in, never blocking; the local index stays the source of truth.

- **Model Serving / Foundation Model APIs** — first in the provider chain: `make providers` lists
  `GET {host}/api/2.0/serving-endpoints`, probes the candidates in `config/models.yaml` (Llama, Qwen,
  gpt-oss, Gemma, Claude) and assigns roles across families.
- **MLflow tracing** — every LLM call is one trace (`crux_lab/llm/tracing.py`): to a Databricks experiment
  when `DATABRICKS_HOST`/`DATABRICKS_TOKEN` are set, otherwise to local `mlruns/`.
- **AI Search (formerly Vector Search)** — `make databricks` writes every extracted claim to a `claims`
  Delta table (Change Data Feed on) through a SQL warehouse (`DATABRICKS_WAREHOUSE_ID`) and creates a
  Delta Sync index over it with managed `databricks-gte-large-en` embeddings; `crux_lab.databricks_sync.query()`
  answers "Has this move been made?" from it.
- **Databricks Apps** — `app.yaml` serves the FastAPI live-mode API.

**In this build no Databricks workspace credentials were available**, so the agents ran on subscription CLIs,
MLflow traced locally, and `make databricks` reports "not configured" and exits. The /about page states this.

## Prior work

Crux Lab reuses only the debate loop of **Crux**, Univer's earlier project (agents debate a
contested question and a cartographer maps the cruxes, without a verdict). A read-only copy was
inventoried file by file in [`docs/CRUX_INVENTORY.md`](docs/CRUX_INVENTORY.md). Adapted files:

| Crux Lab file | Origin in Crux | What changed |
| --- | --- | --- |
| `crux_lab/lab/debate.py` | `backend/debate.py` | Asymmetric defender/attacker exchange (reply → rejoinder → close) instead of symmetric sides; a structured concession field replaces the convergence judge; turn events kept for replay/SSE. |
| `crux_lab/agents/prompts/defender.md` | `backend/prompts.py` (`steelman_system`) | Steelman wording rewritten for an asymmetric defender: misreading check first, claim-id citations, explicit concession with a stated premise. |

Everything else was written for Crux Lab.

<!-- LIMITS -->
## Limits (read before trusting anything)

- **Never a novelty claim.** Novelty is `1 − max similarity` to what our retrieval found in 2918 indexed claims, 1212 abstracts and a live OpenAlex query. Books, paywalled papers and anything OpenAlex lacks are invisible to it.
- **PhilArchive was unavailable**: api.philpapers.org asks for an API key and, with one, no longer serves OAI-PMH; philarchive.org/oai.pl (the channel PhilPapers' terms name) blocks automated clients, and the terms forbid mass-querying by scripts, so bulk access needs PhilPapers' agreement. Fresh targets come from OpenAlex instead, and none of the fresh open-access full texts was about divine hiddenness itself, so fresh targets are philosophy of religion more broadly.
- **Model diversity is degraded: 2 families.** The design wants Defender A, Defender B and the Referee from three different families; without Databricks/OpenRouter keys only Anthropic (Claude) and OpenAI (Codex) models were reachable, through subscription CLIs.
- **The gauntlet's outcome distribution is skewed** (revision_required 18, misreading 11, known_answer 1). No trial ended rebutted or standing: defenders usually save the argument by narrowing a premise, which the Referee scores as revision_required. Read revision_required as 'the premise needs work', not as a defeated argument.
- The Referee and defenders are LLMs; outcome labels are dialectical judgements by models, not verdicts on truth, and they are noisy. The evals are small (n reported with each) and have no human labels.
- Grounding is audited mechanically: [`docs/AUDIT.md`](docs/AUDIT.md) re-checks every quote, cited id, deciding sentence and brief reference against its source.
- Reconstructions are the Extractor's; every premise has a verbatim quote, but an author might reconstruct their argument differently. Read the paper.

- E1: The query is a reworded version of a claim the Extractor took from the source paper's abstract, and that claim is itself in the claims index, so this measures recovery of a known move under paraphrase, not discovery of unknown prior art. Items come from the whole corpus (hiddenness papers and recent philosophy of religion), not only from hiddenness. Corpus: OpenAlex abstracts only (no PhilArchive). One rewording per item; no human labels. Recall is scored per work: OpenAlex lists many papers more than once (versions), so duplicate records are merged (title + first-author surname) before taking the top 5; recall_at_5_strict_record gives the stricter record-level score. Embedding-based retrieval is not bit-reproducible across runs (local model on Apple MPS): previous_runs holds the scores of earlier runs over the same 50 items and the same cached rewordings (each with its scoring unit; compare record-level runs with recall_at_5_strict_record), which shows the run-to-run variance.
- E2: correct_reply_cited counts items labelled known_answer whose verified citations include a gold reply paper; gold_reply_cited_by_a_defender counts items where a defender cited (verified) a claim from a gold reply paper, whatever the label. Small n (10 + 10). Objections are LLM restatements of published claims, and the 'published reply' is chosen by retrieval + an LLM judge from abstract-level claims, so both the pairing and the gold reply are model-made. A first version of this eval paired each objection with its own source paper as the 'reply' (0/10 correct by construction) and was discarded. Misreadings are written by a model from the same pool as the defenders. The argument is a paraphrased fixture, not a corpus record. No human labels.
- E3: Only 2 model families were available (anthropic, openai), so 'mixed families' means 2 families. share_surviving = share of objections whose full gauntlet trial (pre-screen, two defenders, Referee) ended in revision_required or standing (S >= 0.8); trials use the lab's gauntlet without updating the argument between trials. CLI providers ignore temperature, so 'plain' variation comes from the 'objection k of n' prompt. 5 arguments x 4 objections per condition. Full trials were attempted for every objection, but fewer than 80% completed in 3 condition(s) (plain prompt, one model: 4/20; constrained roles, one model: 3/20; constrained roles, mixed families: 4/20 trials completed) because the OpenAI/Codex provider hit its ChatGPT workspace spend cap during the run; share_surviving is therefore reported as not available for those conditions rather than computed on a biased remainder.
<!-- /LIMITS -->
