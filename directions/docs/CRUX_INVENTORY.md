# Crux inventory (P0.5)

Every file in `reference/crux/` (read-only copy of Univer's earlier project Crux), classified once.
ADAPT = copied into `crux_lab/` and rewritten (origin header on top). REFERENCE = read for ideas,
nothing copied. IGNORE = out of scope per CLAUDE.md "Reusing Crux".

| File | Class | Note |
| --- | --- | --- |
| `.DS_Store` | IGNORE | project config, lockfiles, assets, OS files |
| `.gitignore` | IGNORE | project config, lockfiles, assets, OS files |
| `.python-version` | IGNORE | project config, lockfiles, assets, OS files |
| `README.md` | IGNORE | Crux README/branding |
| `backend/__init__.py` | IGNORE | package marker |
| `backend/__pycache__/__init__.cpython-310.pyc` | IGNORE | compiled bytecode |
| `backend/__pycache__/cartographer.cpython-310.pyc` | IGNORE | compiled bytecode |
| `backend/__pycache__/claude_cli.cpython-310.pyc` | IGNORE | compiled bytecode |
| `backend/__pycache__/config.cpython-310.pyc` | IGNORE | compiled bytecode |
| `backend/__pycache__/council.cpython-310.pyc` | IGNORE | compiled bytecode |
| `backend/__pycache__/debate.cpython-310.pyc` | IGNORE | compiled bytecode |
| `backend/__pycache__/factcheck.cpython-310.pyc` | IGNORE | compiled bytecode |
| `backend/__pycache__/main.cpython-310.pyc` | IGNORE | compiled bytecode |
| `backend/__pycache__/pipeline.cpython-310.pyc` | IGNORE | compiled bytecode |
| `backend/__pycache__/prompts.cpython-310.pyc` | IGNORE | compiled bytecode |
| `backend/__pycache__/provider.cpython-310.pyc` | IGNORE | compiled bytecode |
| `backend/__pycache__/storage.cpython-310.pyc` | IGNORE | compiled bytecode |
| `backend/cartographer.py` | IGNORE | cartographer / crux map end product is out of scope |
| `backend/claude_cli.py` | REFERENCE | subprocess pattern for `claude -p`; Crux Lab's providers.py was written fresh (codex + claude CLIs, isolation flags) |
| `backend/config.py` | IGNORE | Crux config/ports/models |
| `backend/council.py` | IGNORE | LLM Council leftovers (peer ranking, chairman synthesis) |
| `backend/debate.py` | ADAPT | multi-round exchange loop: sequential turn order, transcript rendering between turns, turn_start/turn_end events, hard turn cap → crux_lab/lab/debate.py (asymmetric defender/attacker, fixed 3-turn exchange, structured concession detection instead of a convergence judge) |
| `backend/factcheck.py` | IGNORE | fact-check pass is out of scope |
| `backend/main.py` | REFERENCE | FastAPI SSE endpoint shape; Crux Lab's api/server.py written fresh with sse-starlette |
| `backend/openrouter.py` | REFERENCE | OpenRouter client; Crux Lab uses the openai SDK against OpenRouter instead |
| `backend/pipeline.py` | REFERENCE | run registry + stop events for streaming; not copied |
| `backend/prompts.py` | ADAPT | steelman wording only (strongest honest version, concede in good faith, engage the actual point) → rewritten into crux_lab/agents/prompts/defender.md; framing/cartographer/fact-check/persona prompts not used |
| `backend/provider.py` | REFERENCE | provider swap point; Crux Lab has its own provider chain |
| `backend/storage.py` | IGNORE | conversation storage (LLM Council leftover) |
| `docs/studio/comment-court-brief.md` | IGNORE | Crux Studio docs |
| `docs/studio/vision-and-thought-process.md` | IGNORE | Crux Studio docs |
| `frontend/.DS_Store` | IGNORE | Crux Vite/JS config, branding, README |
| `frontend/.gitignore` | IGNORE | Crux Vite/JS config, branding, README |
| `frontend/README.md` | IGNORE | Crux Vite/JS config, branding, README |
| `frontend/eslint.config.js` | IGNORE | Crux Vite/JS config, branding, README |
| `frontend/index.html` | IGNORE | Crux Vite/JS config, branding, README |
| `frontend/package-lock.json` | IGNORE | Crux Vite/JS config, branding, README |
| `frontend/package.json` | IGNORE | Crux Vite/JS config, branding, README |
| `frontend/public/vite.svg` | IGNORE | Crux Vite/JS config, branding, README |
| `frontend/src/App.css` | IGNORE | Crux app shell, styles, export |
| `frontend/src/App.jsx` | IGNORE | Crux app shell, styles, export |
| `frontend/src/api.js` | REFERENCE | SSE client pattern; Crux Lab writes its own typed client |
| `frontend/src/assets/react.svg` | IGNORE | Crux app shell, styles, export |
| `frontend/src/components/CartographerChat.jsx` | IGNORE | Crux UI (cartographer chat, crux map, studio, settings, sidebar, fact report, deck editor) |
| `frontend/src/components/ChatInterface.css` | IGNORE | Crux UI (cartographer chat, crux map, studio, settings, sidebar, fact report, deck editor) |
| `frontend/src/components/ChatInterface.jsx` | IGNORE | Crux UI (cartographer chat, crux map, studio, settings, sidebar, fact report, deck editor) |
| `frontend/src/components/CruxGraph.jsx` | REFERENCE | graph rendering idea; Crux Lab uses @xyflow/react |
| `frontend/src/components/CruxMap.jsx` | IGNORE | Crux UI (cartographer chat, crux map, studio, settings, sidebar, fact report, deck editor) |
| `frontend/src/components/CruxMessage.jsx` | REFERENCE | turn bubble layout idea; not copied |
| `frontend/src/components/CruxPosition.jsx` | IGNORE | Crux UI (cartographer chat, crux map, studio, settings, sidebar, fact report, deck editor) |
| `frontend/src/components/CruxProgress.jsx` | IGNORE | Crux UI (cartographer chat, crux map, studio, settings, sidebar, fact report, deck editor) |
| `frontend/src/components/DebateView.jsx` | IGNORE | Crux UI (cartographer chat, crux map, studio, settings, sidebar, fact report, deck editor) |
| `frontend/src/components/DeckEditor.jsx` | IGNORE | Crux UI (cartographer chat, crux map, studio, settings, sidebar, fact report, deck editor) |
| `frontend/src/components/FactReport.jsx` | IGNORE | Crux UI (cartographer chat, crux map, studio, settings, sidebar, fact report, deck editor) |
| `frontend/src/components/Framing.jsx` | IGNORE | Crux UI (cartographer chat, crux map, studio, settings, sidebar, fact report, deck editor) |
| `frontend/src/components/LiveDebate.jsx` | REFERENCE | live transcript streaming UI; Crux Lab's TrialFeed is written fresh in TS to the notebook design |
| `frontend/src/components/Settings.jsx` | IGNORE | Crux UI (cartographer chat, crux map, studio, settings, sidebar, fact report, deck editor) |
| `frontend/src/components/Sidebar.css` | IGNORE | Crux UI (cartographer chat, crux map, studio, settings, sidebar, fact report, deck editor) |
| `frontend/src/components/Sidebar.jsx` | IGNORE | Crux UI (cartographer chat, crux map, studio, settings, sidebar, fact report, deck editor) |
| `frontend/src/components/Studio.css` | IGNORE | Crux UI (cartographer chat, crux map, studio, settings, sidebar, fact report, deck editor) |
| `frontend/src/components/Studio.jsx` | IGNORE | Crux UI (cartographer chat, crux map, studio, settings, sidebar, fact report, deck editor) |
| `frontend/src/components/crux.css` | IGNORE | Crux UI (cartographer chat, crux map, studio, settings, sidebar, fact report, deck editor) |
| `frontend/src/export.js` | IGNORE | Crux app shell, styles, export |
| `frontend/src/index.css` | IGNORE | Crux app shell, styles, export |
| `frontend/src/main.jsx` | IGNORE | Crux app shell, styles, export |
| `frontend/vite.config.js` | IGNORE | Crux Vite/JS config, branding, README |
| `header.jpg` | IGNORE | project config, lockfiles, assets, OS files |
| `main.py` | IGNORE | project config, lockfiles, assets, OS files |
| `pyproject.toml` | IGNORE | project config, lockfiles, assets, OS files |
| `scripts/cartograph.py` | IGNORE | Crux smoke/factcheck/cartograph scripts |
| `scripts/factcheck.py` | IGNORE | Crux smoke/factcheck/cartograph scripts |
| `scripts/run_debate.py` | REFERENCE | CLI driver for a debate; not copied |
| `scripts/smoke_phase0.py` | IGNORE | Crux smoke/factcheck/cartograph scripts |
| `start.sh` | IGNORE | project config, lockfiles, assets, OS files |
| `state.md` | IGNORE | Crux build state |
| `studio/.DS_Store` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/__init__.py` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/__pycache__/__init__.cpython-310.pyc` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/__pycache__/api.cpython-310.pyc` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/__pycache__/broadcast.cpython-310.pyc` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/__pycache__/export.cpython-310.pyc` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/__pycache__/intake.cpython-310.pyc` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/__pycache__/personas.cpython-310.pyc` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/__pycache__/pipeline.cpython-310.pyc` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/__pycache__/render.cpython-310.pyc` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/__pycache__/store.cpython-310.pyc` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/__pycache__/templates.cpython-310.pyc` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/api.py` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/broadcast.py` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/export.py` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/fixtures/__pycache__/make_mock.cpython-310.pyc` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/fixtures/_blur_test.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/fixtures/_overflow_test.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/fixtures/god_universe.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/fixtures/make_mock.py` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/fixtures/mock_evil.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/fixtures/mock_evil_partial.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/intake.py` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/.DS_Store` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_blur-test/01_case.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_blur-test/02_docket.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_blur-test/manifest.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_fixbatch/01_case.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_fixbatch/02_docket.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_fixbatch/03_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_fixbatch/04_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_fixbatch/05_factcheck.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_fixbatch/06_verdict.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_fixbatch/07_cta.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_fixbatch/deck.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_fixbatch/manifest.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_layout/01_case.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_layout/02_docket.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_layout/03_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_layout/04_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_layout/05_factcheck.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_layout/06_verdict.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_layout/07_cta.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_layout/deck.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_layout/manifest.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_overflow-test/01_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_overflow-test/02_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_overflow-test/03_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_overflow-test/manifest.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_smoke.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_smoke/01_title.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_smoke/02_case.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_smoke/03_docket.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_smoke/04_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_smoke/05_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_smoke/06_factcheck.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_smoke/07_verdict.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_smoke/08_cta.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_smoke/deck.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/_smoke/manifest.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/black-hole-singularity-size-389b78/01_title.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/black-hole-singularity-size-389b78/02_case.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/black-hole-singularity-size-389b78/03_docket.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/black-hole-singularity-size-389b78/04_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/black-hole-singularity-size-389b78/05_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/black-hole-singularity-size-389b78/06_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/black-hole-singularity-size-389b78/07_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/black-hole-singularity-size-389b78/08_factcheck.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/black-hole-singularity-size-389b78/09_verdict.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/black-hole-singularity-size-389b78/10_cta.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/black-hole-singularity-size-389b78/deck.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/black-hole-singularity-size-389b78/manifest.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-universe-001/01_title.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-universe-001/02_case.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-universe-001/03_docket.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-universe-001/04_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-universe-001/05_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-universe-001/06_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-universe-001/07_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-universe-001/08_factcheck.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-universe-001/09_verdict.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-universe-001/10_cta.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-universe-001/manifest.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-vs-eternal-universe-59a7ca/01_case.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-vs-eternal-universe-59a7ca/02_docket.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-vs-eternal-universe-59a7ca/03_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-vs-eternal-universe-59a7ca/04_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-vs-eternal-universe-59a7ca/05_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-vs-eternal-universe-59a7ca/06_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-vs-eternal-universe-59a7ca/07_factcheck.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-vs-eternal-universe-59a7ca/08_verdict.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-vs-eternal-universe-59a7ca/09_cta.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-vs-eternal-universe-59a7ca/deck.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-vs-eternal-universe-59a7ca/manifest.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-vs-science-c52587/01_case.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-vs-science-c52587/02_docket.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-vs-science-c52587/03_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-vs-science-c52587/04_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-vs-science-c52587/05_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-vs-science-c52587/06_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-vs-science-c52587/07_factcheck.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-vs-science-c52587/08_verdict.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-vs-science-c52587/09_cta.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-vs-science-c52587/deck.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/god-vs-science-c52587/manifest.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy-883925/01_case.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy-883925/01_title.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy-883925/02_case.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy-883925/02_docket.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy-883925/03_docket.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy-883925/03_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy-883925/04_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy-883925/05_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy-883925/06_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy-883925/07_factcheck.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy-883925/07_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy-883925/08_factcheck.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy-883925/08_verdict.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy-883925/09_cta.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy-883925/09_verdict.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy-883925/10_cta.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy-883925/deck.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy-883925/manifest.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy/01_title.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy/02_case.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy/03_docket.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy/04_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy/05_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy/06_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy/07_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy/08_factcheck.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy/09_verdict.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy/10_cta.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy/deck.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/problem-of-evil-theodicy/manifest.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/religion-vs-fiction-biblical-miracles-d3d26e/01_case.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/religion-vs-fiction-biblical-miracles-d3d26e/02_docket.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/religion-vs-fiction-biblical-miracles-d3d26e/03_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/religion-vs-fiction-biblical-miracles-d3d26e/04_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/religion-vs-fiction-biblical-miracles-d3d26e/05_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/religion-vs-fiction-biblical-miracles-d3d26e/06_hearing.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/religion-vs-fiction-biblical-miracles-d3d26e/07_factcheck.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/religion-vs-fiction-biblical-miracles-d3d26e/08_verdict.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/religion-vs-fiction-biblical-miracles-d3d26e/09_cta.png` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/religion-vs-fiction-biblical-miracles-d3d26e/deck.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/out/religion-vs-fiction-biblical-miracles-d3d26e/manifest.json` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/personas.py` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/pipeline.py` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/render.py` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/store.py` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `studio/templates.py` | IGNORE | TikTok/Studio/slideshow code and its outputs |
| `uv.lock` | IGNORE | project config, lockfiles, assets, OS files |

Totals: ADAPT 2, IGNORE 215, REFERENCE 10 (227 files).
