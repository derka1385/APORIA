# Crux Lab — website

Static Vite + React + TypeScript + Tailwind site. It reads only `public/data/*.json`, written by
`make export` (see `src/types.ts` for the contract). Replay is the default; set `VITE_API_URL` to the
FastAPI server (`make serve`) to enable live runs over SSE and live prior-art search.

```bash
npm install
npm run dev          # http://localhost:4680
npm run build && npm run preview
npm run typecheck
npx playwright test --project=smoke   # screenshots → ../docs/screens/
npx playwright test --project=demo    # walkthrough video → ../docs/demo.webm
```

Playwright needs a Chromium matching its version (`npx playwright install chromium`), or set
`PW_CHROMIUM=/path/to/chrome` to reuse a browser already on disk.
