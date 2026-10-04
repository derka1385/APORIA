# PROGRESS — Crux Lab overnight build

Work top to bottom. Tick `[x]` and add the evidence after the task (e.g. `→ 412 records`).
Blocked: mark `[!]` with a one-line reason and continue; revisit `[!]` tasks about once an hour.
Times are Europe/Stockholm targets. Gates are hard: if one is missed, cut scope until it is met.

## P0 Scaffold — target 03:00

- [x] P0.1 Python package skeleton, `requirements.txt`, `Makefile` + `crux_lab/cli.py` with all
  targets from CLAUDE.md (stubs allowed), `.gitignore` verified (.env, .venv, cache/, data/raw/,
  data/*.sqlite, logs/, mlruns/, node_modules/, web/dist/).
  **Check:** `make setup && make check` passes.
  → done: 8 tests pass; venv py3.11 via uv.
- [x] P0.2 LLM client: provider chain, disk cache, budget guard, JSON-mode helper with Pydantic
  validation and 2 retries, fake provider for tests.
  **Check:** unit tests pass; cache hit on a repeated call costs $0.
  → test_cache_hit_costs_zero + live codex repeat call cached=True cost 0.0.
- [x] P0.3 `make providers`: probe candidates from `config/models.yaml`, write
  `config/resolved_models.json`, assign roles with family diversity.
  **Check:** at least 1 working model resolved, or NOTES.md says clearly that no provider works
  (then continue with every non-LLM task).
  → 3 working (codex_cli gpt-5.6-terra/sol/luna, OpenAI family); claude_cli OAuth expired; no API keys → diversity degraded: 1 family.
- [x] P0.4 MLflow tracing wrapper (Databricks experiment if creds, else local `mlruns/`).
  **Check:** one traced call recorded.
  → local sqlite in mlruns/, search_traces found 1.
- [x] P0.5 Crux inventory (15 min max): if `reference/crux/` exists, write
  `docs/CRUX_INVENTORY.md` classifying every file as ADAPT / REFERENCE / IGNORE per
  "Reusing Crux" in CLAUDE.md. Copy nothing yet.
  **Check:** the file exists, or NOTES.md says no Crux reference was provided.
  → docs/CRUX_INVENTORY.md: 227 files, ADAPT 2 (backend/debate.py, backend/prompts.py steelman wording), REFERENCE 10, IGNORE 215.

## P1 Corpus — target 03:45

- [x] P1.1 OpenAlex harvester (queries: divine hiddenness; nonresistant nonbelief; divine silence;
  hiddenness of God; skeptical theism hiddenness; Schellenberg hiddenness argument), abstracts
  rebuilt from the inverted index → `data/corpus.jsonl`.
  **Check:** ≥ 300 records with abstracts, or the true count noted.
  → 577 classic hiddenness records with abstracts + 635 fresh (1212 total, all with abstracts).
- [!] P1.2 PhilArchive OAI-PMH client: Identify, ListRecords (`oai_dc`, `from`/`until`,
  resumptionToken), GetRecord; 1 req/s; raw XML to `data/raw/oai/`.
  **Check:** records from 2026-08-01 onward fetched and parsed.
  → BLOCKED: api.philpapers.org needs an API key; philarchive.org/oai.pl is behind Cloudflare bot checks for our client (403); not circumvented. Client + parser built; the one page fetched while testing (999 records since 2026-08-01) parsed fine but was all deletion stubs. Fresh targets come from OpenAlex (from_publication_date ≥ 2026-08-01) instead.
  → 11:25 retried with a PhilPapers API key: api host answers Not found for OAI, philarchive.org/oai.pl still 403; bulk access needs PhilPapers' written agreement. Still [!].
- [x] P1.3 Full texts: up to 50 open-access PDFs relevant to hiddenness / philosophy of religion,
  text via PyMuPDF.
  **Check:** ≥ 20 full texts extracted, or the true count noted.
  → 75 (50 fresh + 25 classic hiddenness), 67 in English.
- [x] P1.4 Target selection → `data/targets.json`: 3 fresh targets (deposited ≥ 2026-08-01;
  prefer hiddenness, then philosophy of religion, then any paper whose abstract says it argues
  for a thesis; full text required) + 2 classic fallback targets from the corpus, each with a
  reason. Include `data/manual_targets/*.md` if present.
  **Check:** 3–5 targets with reasons.
  → 5 targets (3 fresh, 2 classic hiddenness), LLM screen of 75 full-text papers + code checks; no fresh paper on hiddenness itself.

## P2 Mapping — target 04:30

- [x] P2.1 SQLite store + Pydantic schemas for every object in CLAUDE.md.
  **Check:** round-trip tests pass.
  → tests/test_store.py round-trips all 6 kinds + edges.
- [x] P2.2 Cartographer: chunked claim + argument extraction; quote verification drops
  ungrounded claims. Map all targets, plus abstracts-level claims for the whole corpus.
  **Check:** each target has ≥ 1 argument with ≥ 2 premises; drop rate logged.
  → 5/5 targets: 1 argument each, 3–6 premises; full-text claims 303/319 kept (drop 5%), abstract claims 2615/2642 (drop 1%) → data/map_stats.json.
- [x] P2.3 `graph/logic.py` + Formalizer: parser, truth-table validity, missing-premise proposal
  re-checked.
  **Check:** tests (modus ponens valid; affirming the consequent invalid; added premise fixes
  an invalid form); every target argument has a skeleton and validity flag.
  → 11 logic tests pass; all 5 arguments invalid as stated, each with a truth-table-checked missing premise.
- [x] P2.4 Index: embeddings (provider or local fallback) + BM25, over claims and over abstracts
  (both needed for E1).
  **Check:** query "God would ensure everyone capable of relationship believes" returns
  hiddenness claims in the top 5.
  → 5/5 top hits are hiddenness claims (bge-small-en-v1.5 local + BM25, RRF); 2918 claims, 1212 abstracts.

## P3 Thin slice — target 05:30 · GATE A

- [x] P3.1 Generators: blind thought-experimenter, hidden-premise attacker, tradition lens, with
  code-enforced constraints.
  **Check:** 6 objections stored for target 1, each naming a real premise id.
  → 10 objections for target 1 (blind ×4 models, hidden-premise, 2 tradition lenses, naive→sharpened, 2 depth-1 attacks on revised premises); ids validated in code.
- [x] P3.2 Novelty check: 3 restatements, hybrid search, live OpenAlex query, rerank verdicts,
  novelty score, records_searched.
  **Check:** runs on all 6 objections.
  → all 10: 3 restatements, hybrid claims+abstracts search, live OpenAlex (cached), reranked verdicts; records_searched ≈ 4139.
- [x] P3.3 Gauntlet: `lab/debate.py` exchange engine (adapt the ADAPT items from the Crux
  inventory, with origin headers; 30-minute timebox, else write fresh), then pre-screen, two
  defenders, rejoinders, Referee labels, citation verification.
  **Check:** ≥ 2 trials end in valid outcomes with only verified citations.
  → 6/6 trials valid (2 revision_required, 4 misreading); unverifiable ids struck in code. debate.py adapted from Crux (origin header).
- [x] P3.4 Brief generator (JSON + Markdown).
  **Check:** `make run TARGET=<first target>` ends with `data/briefs/<id>.md` and
  `data/runs/<run_id>.json`. **GATE A.**
  → GATE A MET 03:25: data/runs/run-oa-W7203761940.json + 2 briefs (.json/.md).

## P4 Website v1 — target 06:30 · GATE B

- [x] P4.1 `make export`: runs index, run details, trials, briefs, cited corpus records →
  `web/public/data/`.
  **Check:** schema test on exported JSON.
  → tests/test_export.py (3 tests) on the real export: 5 runs, 14 briefs, 2940 claims, 1086 records.
- [x] P4.2 Vite + React + TS + Tailwind scaffold, routing, design tokens from CLAUDE.md.
  **Check:** `npm run build` passes.
  → build + typecheck pass (Vite 8, React 19, Tailwind 4, react-router 7, @xyflow/react 12, recharts 3).
- [x] P4.3 `/lab/:run` replay: argument map (React Flow), trial feed with autoplay/step,
  Director queue, outcome chips, family badges.
  **Check:** renders real run data; Playwright smoke screenshot in `docs/screens/`.
  → docs/screens/lab.png (+ lab-mobile.png); replay driven by run.events (turn events carry trial_id).
- [x] P4.4 `/trial/:id`, `/briefs`, `/brief/:id`; citations open a corpus-record drawer.
  **Check:** smoke test passes. **GATE B.**
  → GATE B MET ~03:45: 10/10 Playwright smoke tests pass on the final export.

## P5 Full lab — target 07:30

- [x] P5.1 Director: priority formula, queue, recursion on revision_required (max depth 2),
  per-target budget; queue snapshots saved per step for the replay.
  **Check:** unit test of ordering; a run log shows the queue reordering.
  → tests/test_director.py; run-oa-W7203761940 director_steps: od9294e 0.244 → 0.144 once its family was tried; 2 revised premises spawned depth-1 attacks.
- [x] P5.2 Mixed families across all roles; Naive Questioner if ≥ 2 families (else skip, note).
  **Check:** run JSON shows the families used.
  → families_used [anthropic, openai]; Naive Questioner (haiku) → sharpened by gpt-5.6-sol.
- [x] P5.3 Run all targets in the background, then export.
  **Check:** ≥ 3 runs and ≥ 3 briefs exported.
  → 5 runs, 55 objections, 30 trials (18 revision_required, 11 misreading, 1 known_answer — final re-run), 14 briefs exported.
- [x] P5.4 Live mode: FastAPI `/api/run` (SSE) + `/api/prior-art`; frontend switches on
  `VITE_API_URL`.
  **Check:** SSE emits events for a cached run.
  → crux_lab/api/server.py; tests/test_api.py replays a cached run over SSE (run_start…run_end, done). Frontend switch on VITE_API_URL is in the web build.

## P6 Evaluation — target 08:30 · GATE C (feature freeze)

- [x] P6.1 E1 prior-art recall → `results/e1.json`.
  → n=50 recall@5 per work (duplicate records merged): BM25 abstracts 16%, embeddings abstracts 24%, embeddings claims 64%, claims+3-way restatement+rerank 86% (strict per record: 12/20/58/86); run-to-run variance kept in previous_runs.
- [x] P6.2 E2 gauntlet calibration → `results/e2.json`.
  → misreadings caught 10/10; known_answer with correct reply 1/10, but a defender cited a verified gold reply in 7/10 (Referee labels revision_required when defenders also narrow the premise). v1 discarded (construction bug), kept as e2_v1_discarded.json.
- [x] P6.3 E3 diversity ablation → `results/e3.json`. (First to cut if behind.)
  → n=20/condition: distinct premises per argument 1.8 / 2.4 / 2.6; mean pairwise distance 0.114 / 0.224 / 0.213; pass pre-screen 100% / 85% / 80%; novelty>0.5 50% / 55% / 45% (plain / constrained one model / constrained mixed). share_surviving attempted 04:00 but only 3–4/20 trials per condition completed (Codex hit the ChatGPT workspace spend cap) → reported n/a, limits say why.
- [x] P6.4 `/results` page: E1 grouped bars, E2 and E3 compact tables, limits text, all read from
  `results/*.json` via export.
  **Check:** build + smoke screenshot. **GATE C — after this, no new features.**
  → docs/screens/results.png. GATE C MET ~03:45 → feature freeze; only polish, docs, fixes from here.

## P7 Polish — from 08:30

- [x] P7.1 Landing page: one-liner, loop ring, 3 headline numbers pulled from results.
- [x] P7.2 `/atlas`: claim graph + "Has this move been made?" box (live API, else client-side
  BM25 over exported claims).
- [x] P7.3 `/about`: how it works, stack, Databricks components, honest limits, diversity status.
- [x] P7.4 README: what, why, quickstart, architecture, results with real numbers, limits,
  screenshots, and "Prior work" listing every file adapted from Crux.
- [x] P7.5 `docs/DEMO.md`: the 2-minute script with real numbers filled in and the exact
  run/trial/brief ids to show, in order.
- [x] P7.6 `make demo-video`: Playwright walkthrough of the DEMO.md path → `docs/demo.webm`.
  → 53 s walkthrough recorded on the final build (6 MB).
- [x] P7.7 Databricks wiring, only if creds exist: MLflow traces to a Databricks experiment;
  `claims` Delta table + AI Search Delta Sync index; `app.yaml` for Databricks Apps. Document
  in README. Never block on this.
  → no creds: code + app.yaml + README section; `make databricks` reports not configured. MLflow traces local (1100+).

## P8 After the freeze (human requests, 2026-10-04 morning)

- [x] P8.1 GitHub Pages deploy + public repo (https://univerdread.github.io/crux-lab/).
- [x] P8.2 Home-page guide for new readers: outcome labels, one experiment per paper, PhilArchive note.
- [x] P8.3 Topics: config/topics/*.yaml, per-topic paths, /topics and /start pages, topic switching.
- [x] P8.4 Assessor agent (journal-referee grade) + revision round; quality panels at the bottom of briefs.
- [x] P8.5 evroc Think provider: 8 model families; per-topic model snapshot for About.
- [x] P8.6 Second topic run end to end: decision theory in philosophy of religion (6 papers, 36 trials,
  18 briefs, Assessor + revision, E1 replication, audit 0 problems).
- [x] P8.7 Ranking by lead score (survival × novelty × quality); strongest-lead card; rank on briefs.
- [x] P8.8 Reviewer's bug report: unavailable novelty → not assessed (never 1.0); trials need both
  defender labels; export screens legacy records; 18 regression tests + 3 replay tests.
- [x] P8.9 Novelty calibration note per topic; demo video re-recorded (76 s); submission draft per topic.
- [x] P8.11 Stricter judging (Claude Sonnet novelty checks, Kimi briefs); decision theory v2; divine simplicity.
- [x] P8.12 Merged into derka1385/APORIA as one research-directions finder: cognitive profiles as generators,
  Director in-session learning, bridge, one site and header in APORIA's design (https://derka1385.github.io/APORIA/docs/).
- [ ] P8.10 Human: record the video (docs/DEMO.md) and submit (docs/SUBMISSION.md) before 15:00.

## Polish forever (when everything above is ticked; never stop)

- Run the full pipeline from a clean clone of the repo; fix whatever breaks.
- Read every brief and trial: anything ungrounded gets fixed or removed.
- Mobile layout and accessibility pass (contrast, focus, alt text).
- Lazy-load large JSON; check bundle size.
- Tests for any untested module.
- Better README screenshots; tighten copy on every page.

## Scope cuts, in order, if behind a gate

1. E3 → 2. Atlas → 3. Naive Questioner → 4. Defender B (single defender, say so on /about)
→ 5. Targets 3 → 1 → 6. Full texts → abstracts only.
