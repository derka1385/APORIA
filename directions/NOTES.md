# NOTES — newest entry first

## 2026-10-04 14:30 — Merged into APORIA as one research-directions finder (Claude, human's request)
- Human: combine Crux Lab with derka1385/APORIA (teammate's repo, human is a collaborator) "in the most synergistic
  way", APORIA's brand and front end, one project, not a section. Live: https://derka1385.github.io/APORIA/docs/
  (Pages serves the repo root; the site is docs/).
- Fusion in the engine (this repo, 5db7bbc; copied to APORIA directions/): APORIA's cognitive profiles generate
  the objections (crux_lab/lab/cognition.py; operation weights pick the move, context/explore/llm_temp used, Δ
  interpolates, Δ 0 = noise floor); Director curiosity term = learned value per profile (mean realized S x N);
  run JSON 'cognition' = per-profile results + APORIA divergence metrics. COGNITION=off restores the old wave.
- Bridge (crux_lab/lab/bridge.py): APORIA's 129 run objections on personal identity vs a new personal-identity
  corpus (abstract-level, 6 OpenAlex requests), Claude Sonnet rerank, no restatement: mean novelty 0.38, 13% above
  0.5; formalist 27% novel, synthesizer and minimalist 0%; Δ 0 0% (n=5) vs Δ 1 12% (n=49). Divergence != new.
- Divine simplicity: families-only baseline (archived data/topics/divine-simplicity/archive/families-only) vs fused
  re-run on the same 5 papers: outcomes 22/7/1 standing vs 21/9; novelty median 0.50 vs 0.50; quality 2.67 vs 2.63.
  Per profile (fused): explorer 17 objections, 8/9 trials surviving, 7 briefs (the Director learned to favour it);
  synthesizer 0/3. Recent-paper bug fixed (a record dated after fresh_from is fresh whichever search found it).
- APORIA site: finder = docs/index.html (re-skinned: APORIA palette/fonts/mark; outcome colours from its operation
  palette; particle object in the hero); APORIA's landing moved to docs/divergence/ (teammate's newest version
  kept through a rebase conflict); one shared header via docs/shell.js on divergence/ and lab/ (also patched in
  lab/static so their export keeps it); finder data in docs/directions-data/; finder run replays renamed /runs
  (APORIA owns lab/); root 404.html for deep links. Build: python3 directions/scripts/build_aporia_site.py.
- Auto mode's classifier blocked the cross-repo copy and pushes ("data exfiltration") until the human left auto
  mode; nothing was worked around. This repo's own web/src/pages/Landing.tsx hero rewrite stays uncommitted (the
  APORIA copy carries the corrected wording); this repo's site keeps its own branding.

## 2026-10-04 13:25 — Decision theory v2 (stricter judging) exported (Claude)
- Same 72 objections (generators replayed from cache), new prior-art checks (Claude Sonnet), new trials and
  briefs (Kimi-K2.6), Assessor (Claude Opus) + revision round. v1 archived in data/topics/decision-theory/archive.
- v1 → v2: novelty checks at 1.0 13 → 0 (median 0.45 → 0.55, all 72 assessed); outcomes 27 revision_required /
  9 misreading → 24 / 11 / 1 rebutted (first rebutted on this topic); Assessor first grade mean 2.08 → 2.26;
  after revision 2.65 → 2.69; needs work 2 → 0 (robustness 2 on all 18 after revision). Strongest lead now a
  Newcomb direction (Hoefer et al., diachronic psychological coherence and one-boxing), lead score 0.36 (v1's
  top was 0.52 on a saturated 1.0). Audit 0 problems; smoke + a11y 26/26; replay tests 18/18.

## 2026-10-04 12:58 — Stricter novelty checks and briefs; decision theory re-run; divine simplicity started (Claude)
- Human: decision-theory directions look weaker; who does the novelty checks? make it stricter like hiddenness;
  then run a topic on divine simplicity (forefront of the literature, its objections).
- Who: hiddenness novelty + briefs = Codex gpt-5.6-terra; decision theory = evroc gpt-oss-120b (bulk role).
- Probe (scratchpad rerank_probe.py; 12 DT objections, same candidates, no live search): gpt-oss mean 0.50,
  2 at 1.0, 68/102 'different' at exactly 0, unstable (five stored 1.0s came back 0.4-0.9); Kimi-K2.6 mean
  0.81, 5 at 1.0, 2 failed; Claude Sonnet mean 0.53, 0 at 1.0, 4/92 at 0. Decision: reranker (restate +
  rerank) = Claude Sonnet, effort medium; brief writer = Kimi-K2.6 (keeps the Assessor, Claude Opus, in
  another family). models.yaml `role_preference` (openai first, as on hiddenness, when Codex is back).
- Briefs: if the writer fails validation, one fallback (Referee's family, GLM), then no brief (was: a
  placeholder brief that would have been listed).
- Decision theory v1 (gpt-oss judging) archived by git mv to data/topics/decision-theory/archive/
  v1-gpt-oss-reranker; re-run with cached generators (same objections), new prior-art checks, trials,
  briefs, Assessor + revision. No new live OpenAlex searches for the re-run (OPENALEX_LIVE_CAP=68, quota
  kept for divine simplicity). E1 for decision theory stays the v1 measurement (gpt-oss reranker; noted).
- OpenAlex had 76 requests left at 12:55 (the keyless allowance refills); divine simplicity corpus uses ~9.
- docs/SITE-FEATURES-AND-PROCESSES.md appeared untracked at 12:52 (not written by this session); left
  uncommitted for the human to decide.

## 2026-10-04 12:50 — Polish loop after the second topic (Claude)
- Clean clone of the public repo: `npm ci` + build pass, both topics in dist (9.9 MB).
- A11y now covers the second topic (home, brief, a replay at its end, trial, results): found a real contrast
  failure (misreading-grey objection dots in the argument map once outcomes are coloured); dots now use the
  darker outcome text shades. Default topic's lab check also runs at the end of the replay. 26/26 smoke+a11y.
- Live mode e2e (FastAPI SSE) passes with the new event fields. Replay integration test covers every topic's
  runs (6 decision-theory runs replay faithfully).
- Read the decision-theory lead brief and two GLM-5.2 misreading rulings: grounded and sensible.
- Copy: lead card explains novelty 1.00; Start page lists evroc, the assess/revise steps and what the second
  topic's run took; README intro + generated second-topic paragraph; demo script topics step and closing
  line generated from topics.json; smaller lead heading on phones.
- Not run: the fine-tuning topic (human chose "build it, no new run" for it).

## 2026-10-04 12:40 — Decision-theory topic: results (Claude)
- Runs 12:09–12:28 on evroc + Claude (8 families): 6 papers, 72 objections, 36 trials (27 revision_required,
  9 misreading, 0 failed, 0 half-labelled), 18 briefs. One novelty check hit the reranker-failure path
  (stored 1.0; run-oa-W4220703499, objection o525bda): it took a trial slot at Director step 0 (the fake 1.0
  put it first), ended misreading, no brief; the export now shows it as not assessed.
- Novelty calibration: gpt-oss-120b (reranker) gives 52% of 'different' passages similarity 0, so 12/71
  assessed checks are exactly 1.0 (hiddenness/Codex: 4% at 0, none at 1.0). Valid under the formula, but
  it means novelty saturates on this topic and quality does most of the ordering. Data-derived note on About.
- Assessor (Claude Opus): all 18 not yet defensible (1.25–2.5); it caught a real mathematical error in a
  novelty-1.0 lead (claimed 0.75·ω = ω in the surreals; false, surreals are an ordered field). Revision
  round: 2/18 up to needs work (Bishop doxastic venture 3.5; Nyman Pascal 3.25), 14 up, 4 unchanged, 0 down.
- Strongest lead: brief-W4394980009.arg1.o6ef874 (Pascal's wager, certainty and hope for apologetic use):
  0.8 × 1.0 × 3.25/5 = 0.52. E1 replicated: claims 78% vs BM25 28% (pipeline 78%, no gain over plain claim
  embeddings here). Audit: 0 problems after folding accents in the name check ('H´ajek' in PDF text).
- Spend: evroc $4.70 for the whole topic (map, runs, E1); ~120 Claude calls on the subscription.

## 2026-10-04 12:27 — Repair: failure states made explicit (Claude; bug report from the human's friend, by Codex)
- Report (~/Downloads/AGENT-REPAIR-BRIEF.md) claimed two failure-handling bugs. Both confirmed in the code:
  A) novelty.check returned 1.0 when retrieval left no candidates, and 1 - 0 = 1.0 when the reranker gave no
  valid judgment after retries: a missing assessment became the maximal novelty score (feeds the Director and
  the lead score). B) gauntlet accepted a trial with a Referee label for only one defender as ok, with a
  combined outcome, although the outcome must survive *both* defenders.
- Fix A: NoveltyResult.novelty is nullable with status assessed | no_candidates | rerank_failed |
  retrieval_failed and a reason; local retrieval errors are caught (budget errors still propagate); live
  OpenAlex being unavailable does not invalidate a local assessment; all-"different" stays a valid score.
  Director: novelty None = not eligible (never the 0.5 default); run stop reason names left-out objections.
  Briefs only from complete trials with assessed novelty; brief Markdown says "not assessed"; E3 counts
  novelty_assessed / novelty_unavailable and uses completed checks as the denominator (None if none).
- Fix B: both defender_a and defender_b need a label; otherwise status failed, outcome and revised premise
  unset, `missing_labels`, error "incomplete defender assessment: missing defender_b"; rounds, labels and
  verified citations kept; trial_end event says failed. Pre-screen misreading exits unchanged.
  `schema.trial_complete()` is the one test; run.py (outcomes, revision spawning), E2 (trials_completed per
  set), E3 and export counters use it.
- Legacy records: export now runs `normalize_run` on every stored run (records + replay events): a stored
  1.0 with nothing reranked or no judgments becomes not assessed (number kept as legacy_novelty); a trial
  saved ok without both labels becomes failed (legacy_outcome kept). Briefs from such items are not ranked
  and are listed in About's method notes. Divine hiddenness export: 55/55 checks assessed, 30/30 trials
  complete, ranking unchanged (matches the report's own audit). The decision-theory runs in progress use
  the old code; their export goes through the same screen.
- Site: "Not assessed" + reason (no bar, no 0.00/1.00/NaN); trial pages say "Trial incomplete: the referee
  assessment for Defender B is unavailable" and still show the discussion; replay never keeps an outcome for
  a failed trial. Tests: tests/test_failure_states.py (18), replay.test.ts (+3). make check, build, smoke, a11y pass.

## 2026-10-04 12:07 — Ranking by lead score; strongest lead featured (Claude, human's request)
- Human: the de se / contrastive-responsibility direction "clearly has the best play-off between academic
  quality and novelty" and should lead; "make sure the best research directions get the most light".
- Was: round-robin by survival × novelty across papers, with every "not yet defensible" direction after the
  rest. With 12/14 graded not yet defensible, two low-novelty "needs work" directions (novelty 0.32, 0.45)
  led and the best-balanced ones sat 3rd-4th.
- Now: lead score = survival × novelty × quality, quality = the Assessor's latest overall score / 5 (after
  revision if any; ungraded counts 3/5). Plain sort, no round-robin; `tier` = rank within its paper.
  Hiddenness top: brief-W7203485685.arg1.ofd28a0 (0.8 × 0.88 × 3.0/5 = 0.422), then divine simplicity as
  parthood (0.405). Home page: a "strongest lead" card shows the #1 direction (revised question + revised
  paper direction, Assessor verdict, the four numbers); label definitions moved below the list.
  README, /briefs, guide text and About method notes say the same. Tests: tests/test_export_ranking.py.

## 2026-10-04 12:00 — Second topic run: decision theory in philosophy of religion (Claude, human's request)
- Human asked to run "decision theory in religious philosophy, potentially exploring Newcomb's problem, God's
  own decision problem, etc." on the new evroc + Claude setup. Topic file: `config/topics/decision-theory.yaml`.
- evroc: 4 keys in .env (EVROC_API_KEY used); `make providers` resolved 11 models, 8 families (anthropic,
  kimi, glm, mistral, qwen, llama, gpt-oss, gemma). Roles: Defender A claude:sonnet, Defender B Kimi-K2.6,
  Referee GLM-5.2, extractor/reranker gpt-oss-120b, generators one per family. Fixes needed: reasoning models
  return empty text at tiny max_tokens (probe 400, evroc floor 8192), evroc ids use dashes for dots.
- Hiddenness results keep their own model snapshot (`data/resolved_models.json`, the Codex + Claude
  assignment they ran with); each topic's `make runs` now writes its snapshot, and export reads it.
- OpenAlex: keyless allowance had 26 requests left today (resets ~02:00). Topic uses one page per search
  (`max_per_query: 200`): 8 classic + 3 fresh = 11 requests; live prior-art searches capped at 10 more
  (`OPENALEX_LIVE_CAP=55`, 45 already used in the last 24 h).
- Corpus: 549 classic + 99 fresh records after `fresh_relevant` (the fresh "decision theory" search also
  returned ecology and engineering: a fresh paper must now mention religion), 50 full texts (34 classic).
- Targets: no fresh open-access paper scored >= 2/3 on topic, so all six are classics. `spread: true` takes
  the best paper from each search in turn (otherwise five were Pascal's-wager papers); journal articles
  break ties over preprints. Six: Hoefer, Viger & Viger on Newcomb (THEORIA 2019, one-boxing from
  psychological coherence), Chen & Rubio "Surreal decisions" (2018, infinite utilities in the wager), Nyman
  "Pascal's Wager and Its Postmodern Counterpart" (2024), Bishop "Faith as doxastic venture" (2002), Page
  "A Theological Argument for an Everett Multiverse" (2012, God's choice of world), Rogers "Saving
  Eternity" (2022, divine foreknowledge and free will). No fresh target: the "cannot have read replies"
  guarantee does not hold for this topic, and the site says so per paper.

## 2026-10-04 11:40 — evroc Think provider wired in (no key yet) (Claude)
- Human asked whether evroc Think can power the debates. Yes: OpenAI-compatible API at
  https://models.think.evroc.com/v1 (API key from the evroc console/CLI), EU-hosted open models
  (Llama 3.3, Qwen3, Mistral/Magistral, gpt-oss-120B, Kimi, Gemma, Phi). Added `EvrocProvider`
  (providers.py), `EVROC_API_KEY`, evroc patterns per family in models.yaml (+ `evroc_ids` fallback if
  /v1/models is unavailable), families mistral/kimi, bulk_family preference [openai, gpt-oss, llama, qwen].
- Simulated assignment with evroc + Claude: Defender A anthropic:sonnet, Defender B llama-3.3-70b,
  Referee qwen3, extraction/reranking on gpt-oss-120b — three-family gauntlet restored, bulk work off the
  Claude plan. Not probed: no key. To use: put EVROC_API_KEY in .env, `make providers`, then re-run
  (`make runs eval assess revise export docs`) — that replaces the current results with new model calls.

## 2026-10-04 11:20 — revision round run (Claude, human said "yes run it")
- `make revise` (crux_lab/lab/assess.py main_revise, prompts/reviser.md): a Reviser rewrites each direction
  to answer the Assessor's strongest objection (narrowing if decisive; may only name works/philosophers that
  appear in its inputs), then the Assessor re-grades it in a fresh read that does not see its own earlier
  critique. Both grades are kept in the brief (`assessment` and `revision.assessment`).
- Models: Reviser claude:sonnet, Assessor claude:opus (same family: Codex is capped) — 28 calls, ~3 min.
- Result: 2/14 moved up to "needs work" (3.5/5): the many-goods direction (W2575351351.oc4a9a4: adds a
  counterfactual distinctiveness test; re-assessor now raises an individuation dilemma) and the
  vulnerable-love direction (W2072673546.o607d86); 12 stayed "not yet defensible"; overall score up for 9,
  down for 1. Site: revision panel with before → after grade; list shows the latest grade and revised
  question; ranking uses the latest grade. Audit extended to revision prose (0 problems).
- Note: the Assessor's critiques name philosophers from model knowledge (e.g. Perry, Cappelen–Dever); the
  panel says these are not checked against the corpus.

## 2026-10-04 13:05 — Assessor agent grades every research direction (Claude, at the human's request)
- `crux_lab/lab/assess.py` + prompts/assessor.md (`make assess`): a journal-referee read of each brief
  (never sees model names). Scores 1-5: coherence, robustness (states the strongest objection and judges
  whether the direction answers it), significance, specificity; plus what the paper needs. Grade computed
  in code: promising = coherence & robustness >= 4 and mean >= 3.75; not yet defensible = coherence or
  robustness <= 2; else needs work. Model: Claude Opus via claude -p (different family from the brief
  writer, gpt-5.6-terra): 14 calls on the human's Claude plan.
- Result: all 14 directions "not yet defensible" (robustness 2 everywhere; overall 2.25-3.0). I read the
  critiques: they are specific and competent (e.g. modal premise misread; Perry/Castañeda essential-
  indexical reply unanswered; begs the question against constituent ontology). Read as "the brief does
  not yet answer the obvious objection", with the fix stated, not as "no idea here".
- Site: grade chip + assessor verdict on every direction; "Academic quality check" panel on each brief;
  directions graded not yet defensible sort last (all are, so order unchanged). README tallies grades.
- Possible next step (model spend): a revision loop where the brief writer answers the assessor's
  strongest objection and the assessor re-grades.

## 2026-10-04 12:45 — topics: any subject, not just hiddenness (Claude, at the human's request)
- Human chose "build it, no new run". A topic is now config/topics/<slug>.yaml (queries, on-topic filter,
  screening scale, tradition lenses, optional E2 fixture). `make <step> TOPIC=<slug>` /
  `python -m crux_lab.cli --topic <slug>` select it; the default topic (divine-hiddenness) keeps the
  original paths, others live under data|results|cache/index|web/public/data/topics/<slug>/.
- Example second topic: config/topics/fine-tuning.yaml (configured, NOT run: no model spend).
- export writes web/public/data/topics.json (all topics, status, counts, commands, full config).
- Site: "Topics" in the nav + "topic: <name>" next to the logo; /topics (explore a run topic, or see how
  to run one), /start (writes a topic file in the browser from scratch or from a template, with the exact
  steps). Topic switching reads ?topic=<slug> and remembers it for the session; data loads from the
  topic's folder (verified with a temporary test topic, then removed). Landing + guide link to both.
- Screening prompt is now topic-generic (field topic_relevance): re-screening the hiddenness targets
  would need new model calls. Tests: 55 Python (topic config/paths/env switching), 9 web, 10 smoke +
  10 axe (incl. /topics and /start).

## 2026-10-04 11:25 — PhilPapers API key tried: does not unlock PhilArchive OAI (Claude)
- The human supplied a PhilPapers API key (stored in .env only; not printed, not committed — consider
  regenerating it after the hackathon since it was pasted in chat).
- Result: with apiId/apiKey (the documented names) api.philpapers.org accepts the key but returns "Not
  found" for OAI-PMH verbs; without a key it says a key is required. philarchive.org/oai.pl — which
  PhilPapers' terms §9 name as the OAI channel — still returns a Cloudflare 403 to our client.
- PhilPapers docs: the key serves the JSON category feed; article feeds need written agreement ("Contact
  us"). Terms §8: "Mass-querying of the site using scripts is considered a form of abuse." So no browser
  workaround. Next step if wanted: email PhilPapers to allow the harvester. P1.2 stays [!].
- The key is no longer added to OAI requests (code comment explains); home page text updated.

## 2026-10-04 10:55 — home page explains itself (Claude, at the human's request)
- Landing now has: a "How it works ↓" hero button; the outcome legend replaced by plain-language
  definitions (what each label means + what it means for a researcher, with survival S); a paper filter
  above the research directions (all / one paper; picking a paper shows all its directions); and a
  "How the lab works, and how to explore it" section: one experiment = one paper (7 steps), the five
  papers with "its research directions" + "replay its run", how to look into something else (filter,
  Atlas search, running the lab on a new argument locally via data/manual_targets — honest that the
  public site is a replay), and where the papers come from incl. why PhilArchive was unavailable.
- Backend: manual targets get filename-safe ids `manual-<name>`; `make targets` / `python -m crux_lab.cli
  targets` re-selects targets incl. manual ones; the PhilArchive harvester accepts PHILPAPERS_API_ID /
  PHILPAPERS_API_KEY from .env (untested: no key). Manual-target runs were not exercised in this build.
- Verified: desktop + mobile in the browser pane, filter + scroll behaviour, 50 Python + 9 web tests,
  10 smoke + 8 axe checks.

## 2026-10-04 10:30 — LIVE: https://univerdread.github.io/crux-lab/ (repo now public) (Claude)
- At the human's request: repo `univerdread/crux-lab` made **public** (full history scanned first: no
  secrets, no .env ever committed; commit author email from git config is now visible, as on any public
  repo) and deployed to **GitHub Pages** via `.github/workflows/pages.yml` (Actions source; builds `web/`
  with `VITE_BASE=/crux-lab/`; redeploys on every push to main touching `web/`). Verified live: landing,
  /results and /lab deep links render; all assets and data return 200 (deep links come back with HTTP 404
  + the app via 404.html, which is how SPA fallback works on Pages).
- `vite.config.ts` base is now `process.env.VITE_BASE || "/"` (local/Vercel/Netlify unchanged).
- docs/SUBMISSION.md now carries the live and repo links.

## ☀️ MORNING SUMMARY — read this first (written 07:40 by Claude)
**State:** everything in PROGRESS.md is done except P1.2 (PhilArchive OAI blocked: API key / Cloudflare 403,
re-checked hourly, still 403). Gates A/B/C were met by ~03:45; since then only polish, fixes and docs.

**Numbers (all read from web/public/data):** corpus 1212 OpenAlex records = 962 distinct works,
75 open-access full texts; 5 target papers → 55 objections → 30 trials
(revision_required 18, misreading 11, known_answer 1) → 14 research briefs.
E1 prior-art recall@5: 86% (full pipeline) vs 16% (BM25), n=50.
E2: 10/10 misreadings caught; gold reply cited by a defender 7/10,
labelled known_answer only 1/10 (Referee is conservative). E3: constrained roles ≈ double the spread
of objections; its survival column is n/a (see below). Grounding audit (docs/AUDIT.md): 0 problems.

**⚠️ Needs you:** Codex hit your ChatGPT workspace **spend cap** at ~03:58 → check that workspace's billing.
I set `DISABLE_PROVIDERS=codex_cli` in `.env`; remove the line to re-enable Codex.

**To submit (deadline 15:00 Stockholm):**
1. `make demo` (or `cd web && npm install && npm run build && npm run preview`) → http://localhost:4680; click
   / → top research direction → its run (/lab, press Replay) → a trial → /results → /about.
2. Read one brief + its trial yourself (top: /brief/brief-W7212186029.arg1.o10f4f4).
3. Deploy the `web/` folder as a static site: Vercel (root directory `web`, preset Vite) or Netlify (base
   directory `web`; `web/netlify.toml` sets build + publish). Deep links are handled by both configs.
   GitHub Pages (subpath, e.g. /crux-lab/; needs a public repo or a paid plan): in `web/` run
   `npx tsc -b && npx vite build --base=/crux-lab/ && cp dist/index.html dist/404.html` and publish `dist/`
   (tested: routing and data loading work under the subpath; 404.html gives deep links).
4. Record the 2-minute video from `docs/DEMO.md` (a silent 55 s walkthrough is in `docs/demo.webm`).
5. Paste from `docs/SUBMISSION.md` (draft text with real numbers); repo is private → make public if required.

**Checks you can run:** `make check` (50 Python + 9 web tests + typecheck), `make smoke` (10 page smoke + 8 axe
accessibility), `make live-test` (FastAPI SSE live mode), `PYTHONPATH=. .venv/bin/python scripts/audit.py`.
Playwright needs its Chromium: `cd web && npx playwright install chromium`, or reuse the one on this Mac with
`PW_CHROMIUM=$HOME/Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell make smoke`.

## 2026-10-04 07:00 — duplicate-records follow-ups closed (Claude)
- Novelty now excludes every record of the target work; the gauntlet treats claims from another record
  of the target work as the argument's own (never literature for known_answer); E2 scores gold replies
  per work. None of the 5 targets has a duplicate record and a post-hoc check shows no E2 item changes,
  so no published number moved; these protect future runs. Tests: 50 Python, 9 web.

## 2026-10-04 06:35 — "Has this move been made?" returns distinct works (Claude)
- 563 of 2940 exported claims come from duplicate records of a paper. claims.json now carries `work`
  (canonical id); /atlas local BM25, the live API (/api/prior-art) and its UI show at most one hit per
  work. Verified with smoke, a11y and live tests.

## 2026-10-04 06:25 — briefs' nearest matches deduplicated by work (Claude)
- 7/14 briefs (and 27/55 objection novelty panels) listed the same work twice among their 3 nearest
  matches (claim + abstract of one paper, or two version records). Nearest is now the 3 nearest
  *distinct works*: `novelty.check` does it for new runs; `scripts/dedupe_nearest.py` rebuilt the derived
  fields of existing runs/briefs from their stored match lists (no model calls; novelty scores unchanged,
  they are computed over all matches). Brief prose was written seeing the raw top 3; references are
  system-rendered, so only the reference list changed. 0 briefs now repeat a work; audit 0 problems.
- Note: re-running `make runs` from cache would now need new model calls for the 7 brief prompts that
  included a duplicate (their prompt text changes). Not needed for the submission.

## 2026-10-04 06:12 — duplicate records found; E1 rescored per work (Claude)
- The OpenAlex corpus lists many papers more than once (Zenodo/figshare versions, preprint + article):
  194 duplicate groups, 250 extra copies → 962 distinct works among 1212 records (key = normalised
  title + first-author surname; different papers that merely share a title stay distinct).
- 22/50 E1 items had a duplicate, so a method retrieving the *same work* under another id was scored as a
  miss. E1 now ranks distinct works (`crux_lab/corpus/dedup.py`) and keeps the strict record-level score:
  work-level BM25 16%, emb. abstracts 24%, emb. claims 64%, full pipeline 86% (strict: 12/20/58/86).
  Regenerated from cache (no model calls). previous_runs entries are labelled with their unit.
- README/site/about report distinct works next to records. Not changed: novelty scores (a duplicate of a
  prior-art record is still prior art) and the claim index (re-mapping would need new model calls).

## 2026-10-04 05:40 — E1 run-to-run variance found and recorded (Claude)
- Regenerating E1 from cache (to clarify its limits) changed the two embedding-only methods:
  embeddings-over-abstracts 18% → 20%, embeddings-over-claims 54% → 58%; BM25 (12%) and the full
  pipeline (86%) identical. Same 50 items, same cached rewordings, index files unchanged since 03:15 →
  the local embedding model on Apple MPS is not bit-reproducible and near-ties flip in the top 5.
- Decision: report the latest run and keep earlier runs in `results/e1.json → previous_runs`; the E1
  limits say so. The headline (86%) is unaffected. I did not switch embeddings to CPU now, because that
  would change cached retrieval candidates and force new model calls (Codex is disabled).

## 2026-10-04 05:20 — polish log since 04:12 (Claude)
- Fix (real bug): in a fresh clone `make demo` ran `export`, which overwrote the committed site data with
  an empty claim set (the claim store is gitignored). Export now refuses on an empty store; `make demo`
  serves the committed export. Verified in a fresh clone. README explains the no-keys viewing path.
- Brief print layout checked (4 clean A4 pages); stray separators fixed.
- Demo video re-recorded on the final build. Screens regenerated by every `make smoke`.
- Audit: capitalised names in brief prose must occur in the paper or trial (13/13; the only non-paper
  names are thought-experiment characters). docs/AUDIT.md: 0 problems.
- Perf: /atlas loads titles.json (150 KB) instead of records.json (1.8 MB).
- Security: only .env.example is tracked; no tokens; your email is nowhere in the repo.
- Still no model calls since the Codex spend cap; DISABLE_PROVIDERS=codex_cli remains in .env.

## 2026-10-04 04:12 — loop iteration: live mode verified; corrections (Claude)
- Correction: final outcome counts are revision_required 18, misreading 11, known_answer 1 (30 trials).
  The "20 / 9" in the 03:36 entry was from target 1's first attempt, before the final cached re-run.
  The README limits now compute this distribution from the runs and say no trial ended rebutted/standing.
- Live mode tested end to end (`make live-test`): Playwright starts the FastAPI server and a build with
  VITE_API_URL; /lab streams a cached run over SSE, /atlas searches via /api/prior-art. No model calls.
- P1.2 revisited: philarchive.org/oai.pl still answers our client with 403 → stays [!].

## 2026-10-04 04:05 — ⚠️ Codex hit the ChatGPT workspace spend cap; Codex disabled (Claude)
- At ~03:58, while adding full trials to E3 (share_surviving), every `codex exec` call started failing:
  "You hit your spend cap set by the owner of your workspace." **Human: check the ChatGPT workspace
  billing/spend cap** — usage past the plan allowance may have drawn on paid credits up to the cap.
  Ledger (cache/spend.jsonl): 1,171 successful Codex calls + 240 Claude calls tonight (notional API-price
  estimate ≈ $12 Codex, ≈ $4 Claude; each Codex call also carries ~14k tokens of CLI overhead not in that estimate).
- I set `DISABLE_PROVIDERS=codex_cli` in `.env` (new switch; documented in .env.example). Cached calls still
  replay, so every run, brief, export and eval regenerates without calling Codex. Any *new* LLM work would
  need `make providers` (Claude only) or the cap raised. Remove the line from .env to re-enable Codex.
- E3: all earlier metrics unchanged; share_surviving reported n/a because only 3–4/20 trials per condition
  completed; the limits text says exactly that. No other results were affected (runs, E1, E2 finished
  before the cap).
- Polish since 03:47: axe accessibility pass clean on 8 pages, grounding audit 0 problems (docs/AUDIT.md),
  45 tests, docs/SUBMISSION.md draft, lab screenshot at viewport size; `make docs` regenerates all docs.

## 2026-10-04 03:47 — GATES B and C met; everything in PROGRESS ticked except P1.2 (Claude)
- Website built by a subagent against `web/src/types.ts`, verified on the real export: typecheck +
  build pass, 10/10 Playwright smoke tests, screenshots in docs/screens/, 53 s walkthrough in
  docs/demo.webm. Run tests with `make smoke` (needs a Chromium matching Playwright; set
  `PW_CHROMIUM=$HOME/Library/Caches/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-mac-arm64/chrome-headless-shell`
  to reuse the one on this Mac).
- Turn events now carry trial_id (cached re-run; outcomes identical).
- README results/limits and docs/DEMO.md are generated from the export (`make docs`). The site and
  README rank research directions round-robin across targets (best per paper first).
- Human, morning checklist: (1) `make demo` and click /, a brief, /lab, a trial, /results;
  (2) read one brief + its trial (`/brief/brief-W7212186029.arg1.o10f4f4` is top); the one
  known_answer is in run-oa-W2072673546 (cites W7168366306.a3 — I checked the quote);
  (3) deploy `web/dist` (static; SPA fallback needed for deep links); (4) optional: Databricks
  token + warehouse → `make providers && make databricks`, which would raise family diversity.

## 2026-10-04 03:36 — all targets run; E1 done; E2 rebuilt (Claude)
- 5 runs / 55 objections / 30 trials / 14 briefs. Outcomes: revision_required 20, misreading 9,
  known_answer 1, rebutted 0, standing 0. I read the revision_required labels: they are genuine
  premise changes (narrowing/strengthening), not mere clarifications, so the Referee prompt stays.
  The one known_answer (W2072673546) cites W7168366306.a3, whose verbatim quote does say what the
  trial claims. Limits mention that this gauntlet produced no rebutted/standing outcomes.
- E1 (n=50) recall@5: BM25 abstracts 12%, embeddings abstracts 18%, embeddings claims 54%,
  claims + 3-way restatement + rerank 86%.
- **E2 v1 discarded (construction bug, kept as results/e2_v1_discarded.json):** the item builder
  restated each theist paper's own response as the objection and then counted that same paper as
  the "published reply", so known_answer-with-correct-citation was 0/10 by construction.
  Misreadings were 10/10. v2 pairs an objection from paper A with replies from other papers B,
  found by retrieval and confirmed by an LLM judge; re-running now (misreading half is cached).
- Product: briefs ranked by survival × novelty lead the site ("Research directions").

## 2026-10-04 03:21 — P2 done, lab running on all targets (Claude)
- Map: 5/5 targets → 1 argument each (3–6 premises), all invalid as stated, each with a truth-table-
  checked missing premise; claims: 303 full-text (drop 5%) + 2615 abstract (drop 1%). Index:
  2918 claims + 1212 abstracts, bge-small-en-v1.5 local + BM25 (RRF). Retrieval check passes 5/5.
- First trials on target 1 (randomness vs divine control): both → revision_required (defenders
  conceded the hidden "explanatory parity ⇒ evidential parity" premise and narrowed it). Philosophy
  quality looks right: likelihood-ratio/predictive-asymmetry cases, Molinist + Reformed lenses.
- Fixes found while watching: (1) blind generators converged on the same hidden premise → each
  blind generator now gets a different stated premise (coverage; Director still ranks); (2) live
  OpenAlex 400s (commas broke filter syntax) → keyword `search=` param; daily cap 45 live searches;
  (3) defenders citing the argument's own claim ids got struck → own-paper ids verify but never
  count toward known_answer. Runs restarted (LLM cache makes restarts cheap).
- Databricks: `crux_lab/databricks_sync.py` (claims Delta table via SQL warehouse + AI Search
  Delta Sync index with managed gte-large embeddings) and `app.yaml` are wired; they print
  "not configured" and skip without DATABRICKS_HOST/TOKEN/WAREHOUSE_ID. MLflow traces locally.
- Frontend is being built by a subagent against `web/src/types.ts` (the export contract).

## 2026-10-04 03:06 — product direction from the human (awake at kickoff)
- "The tool is made for philosophers or philosophy students who want help with their research and
  to find some novelty in academia — finding what they should research and write about next."
- Usability consequences (apply to every page): lead with *research directions* (the brief's
  research question + "A paper here would argue…"), ranked by survival × novelty; plain-language
  summaries before agent transcripts; every claim traceable to a quote and a corpus record;
  printable / Markdown-exportable briefs; honest uncertainty ("Further human review required",
  records searched, nearest matches) so a student knows how far to trust a lead.

## 2026-10-04 03:04 — P1 corpus + targets (Claude)
- Human logged `claude -p` back in at ~02:58 → `make providers` now finds **2 families**
  (anthropic: sonnet/opus/haiku via claude_cli; openai: gpt-5.6-terra/sol/luna via codex_cli).
  Roles: Defender A = anthropic:sonnet, Defender B = openai:terra, Referee = openai:sol,
  generators = sonnet, opus, terra, sol; naive questioner = haiku. Still "diversity degraded:
  2 families" (no third family without Databricks/OpenRouter keys). Decision: bulk roles
  (extractor, reranker) run on Codex (`bulk_family: openai` in models.yaml) so the lab does not
  drain the Claude plan that also runs this build session.
- **PhilArchive OAI is blocked** (P1.2 [!]): api.philpapers.org requires an API key now;
  philarchive.org/oai.pl answers curl but returns a Cloudflare 403 page to our Python client.
  That is bot detection, so I did not work around it. Fresh targets come from OpenAlex with
  `from_publication_date ≥ 2026-08-01` (OpenAlex's `from_created_date` is premium-only).
- **OpenAlex without a key = ~$0.10/day ≈ 100 list requests.** Used ~25 so far. Don't waste them:
  `make corpus` re-harvests; the corpus is committed in `data/corpus.jsonl`.
- Corpus: 1212 records with abstracts (577 classic hiddenness, 635 fresh since 2026-08-01),
  75 OA full texts (50 fresh, 25 classic; many publisher PDFs 403 or OJS HTML viewers → skipped).
- Targets (data/targets.json): no fresh full-text paper on hiddenness itself exists in what we can
  reach, so fresh targets fall back to philosophy of religion: W7203761940 (randomness vs visible
  divine control, hiddenness-relevance 2/3), W7203485685 (de se knowledge and omniscience, Sophia),
  W7212186029 (divine simplicity as symmetric parthood, Religious Studies); classic fallbacks
  W2072673546 (critical reflections on the hiddenness argument), W2575351351 (hiddenness, greater
  goods, accommodation). A Russian full text slipped past the LLM screen → added a code check.

## 2026-10-04 02:47 — P0.1–P0.4 scaffold + LLM layer (Claude)
- Setup done by Claude at the human's request (START-HERE steps): repo at `~/crux-lab`, private
  GitHub repo `univerdread/crux-lab` created and pushed; Crux copied to `reference/crux/` (gitignored,
  rsync with the START-HERE excludes; Crux had no `.env`).
- **Providers — human action wanted:** no API keys exist on this machine (`.env` copied from the
  example, all keys blank). Decision: added two subscription-CLI providers after the API chain:
  `codex_cli` (Codex CLI bundled in ChatGPT.app, ChatGPT plan, OpenAI family) and `claude_cli`
  (`claude -p`, Claude plan, Anthropic family). Both run as isolated completions (no tools, no
  shell, no web, no user config). **`claude -p` fails: "OAuth session expired"** → run `claude`
  in a terminal and `/login` to add the Anthropic family; then `make providers`. Adding
  `DATABRICKS_HOST/TOKEN` to `.env` (sponsor, free edition) would add llama/qwen/gpt-oss/gemma.
- Current: **diversity degraded: 1 family** (openai: gpt-5.6-terra, -sol, -luna). Defender A =
  terra, Defender B = sol, Referee = sol. Shown on /about.
- Budget decision: API providers count estimated USD against `LLM_BUDGET_USD` ($20). CLI providers
  spend no money, so they count calls against `CLI_CALL_BUDGET` (default 4000); notional USD still
  logged in `cache/spend.jsonl`. CLI providers ignore temperature (recorded in cache key anyway).
- `CONTACT_EMAIL` left blank on purpose (not sending the human's address anywhere unasked):
  User-Agent says `mailto:unset`. Human: fill it in `.env` for OpenAlex's polite pool.
- Verified: `make check` 8 passed; MLflow trace recorded locally (sqlite in `mlruns/`); repeat call
  is a cache hit costing $0.

## 2026-10-04 02:30 — kickoff (human)
- Starter kit committed: CLAUDE.md (rules + spec), PROGRESS.md (tasks), .claude/loop.md (loop prompt).
- Human is asleep until ~09:00. Gates: A 05:30, B 06:30, C 08:30. Submission 15:00 Stockholm.
