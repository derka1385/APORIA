# Start here (about 15 minutes, then sleep)

Full plan for humans: https://claude.ai/code/artifact/324c2805-ba35-409d-a71e-4e270ef2d6b7

## Tonight

1. `claude update` (the /loop command needs Claude Code v2.1.72 or later).
2. Create a **private** GitHub repo, clone it, copy everything in this folder into it
   (including the hidden `.claude/` folder, `.env.example` and `.gitignore`), then:
   `git add -A && git commit -m "starter kit" && git push`
   The remote must exist before Claude starts so its pushes are trusted.
   Then copy Crux in as a read-only reference (gitignored, never committed). From the repo root:

   macOS/Linux/WSL:
   `rsync -a --exclude .git --exclude node_modules --exclude .venv --exclude 'CLAUDE.md' --exclude '.claude' --exclude 'AGENTS.md' --exclude '.env*' --exclude data --exclude storage /path/to/crux/ reference/crux/`

   Windows without rsync: copy the Crux folder to `reference\crux\`, then delete from the copy
   `.git`, `node_modules`, `.venv`, every `.env` file, every `CLAUDE.md` and `.claude` folder.

   The excludes matter: Crux's `.env` holds your API key, and Crux's own CLAUDE.md would give
   Claude instructions for the wrong project. The copy has to sit inside this repo, because a
   read outside the working folder triggers a permission prompt that would stall the night.
3. `cp .env.example .env` and fill in at least one LLM provider. Databricks Free Edition is
   free and is the sponsor: create a workspace, then User settings > Developer > Access tokens.
   Set `LLM_BUDGET_USD` to what you are willing to spend, and `CONTACT_EMAIL`.
4. Plug in the laptop, keep the lid open, stop it sleeping:
   macOS: run `caffeinate -dims` in a second terminal. Windows: Settings > Power > Sleep: Never
   (and run Claude Code inside WSL2 so `make` works).
5. In the repo folder: `claude --permission-mode auto`, choose the strongest model, then type:

   /loop 2m

   With an interval and no prompt, /loop runs `.claude/loop.md` every 2 minutes. A fire waits
   until Claude is idle, so iterations run back to back.
6. Watch the first iteration finish (about 10 minutes). If it reports no working provider,
   fix `.env` and say "keys fixed, continue". Then sleep.

Optional: to run the lab on your own argument, put it in `data/manual_targets/<name>.md`
(premises and conclusion in plain English). It becomes an extra target. If it should stay
private, write "keep manual_targets private" in NOTES.md before starting.

## Morning

1. Read the top of `NOTES.md` and `PROGRESS.md`; skim `git log`.
2. Stop the loop: press Esc, or ask Claude to cancel its scheduled tasks.
3. `make demo`, then click through /lab, /trial, /brief, /results.
4. Read one brief yourself. Is the objection real philosophy? Does the cited reply say what
   the trial claims?
5. Decide with the team what gets submitted (Dew or Crux Lab) and check Hack-Nation's rule on
   projects per team.
6. Deploy `web/dist` (Vercel or Netlify), record the 2-minute video from `docs/DEMO.md`,
   make the repo public if the form requires it.
7. Submit by 14:30. The form closes at 15:00 Stockholm (09:00 ET).
