import { defineConfig } from "@playwright/test";

// Live mode end to end: the real FastAPI server (crux_lab/api/server.py) + a build with VITE_API_URL set.
// The server replays cached runs over SSE (no model calls) and serves /api/prior-art from the local index.
// Run: npx playwright test -c playwright.live.config.ts
const API = "http://127.0.0.1:8765";

export default defineConfig({
  testDir: "./tests",
  testMatch: /live\.spec\.ts/,
  timeout: 180_000,
  workers: 1,
  reporter: [["list"]],
  outputDir: "./test-results",
  use: {
    baseURL: "http://localhost:4681",
    viewport: { width: 1440, height: 900 },
    launchOptions: process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {},
  },
  webServer: [
    {
      command: "cd .. && .venv/bin/python -m uvicorn crux_lab.api.server:app --host 127.0.0.1 --port 8765",
      url: `${API}/api/health`,
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: "npx vite build --outDir dist-live && npx vite preview --outDir dist-live --port 4681 --strictPort",
      url: "http://localhost:4681",
      env: { VITE_API_URL: API },
      reuseExistingServer: true,
      timeout: 180_000,
    },
  ],
});
