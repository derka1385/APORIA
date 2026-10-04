import { defineConfig } from "@playwright/test";

// Smoke tests and the demo recording run against the production build served by `vite preview`.
// Build first (`npm run build`) so dist/ carries the current web/public/data export.
export default defineConfig({
  testDir: "./tests",
  timeout: 120_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  outputDir: "./test-results",
  use: {
    baseURL: "http://localhost:4680",
    viewport: { width: 1440, height: 900 },
    colorScheme: "light",
    // Optional: point at an already-installed Chromium instead of `npx playwright install chromium`.
    launchOptions: process.env.PW_CHROMIUM ? { executablePath: process.env.PW_CHROMIUM } : {},
  },
  webServer: {
    command: "npm run preview",
    url: "http://localhost:4680",
    reuseExistingServer: true,
    timeout: 120_000,
  },
  projects: [
    { name: "smoke", testMatch: /smoke\.spec\.ts/ },
    { name: "a11y", testMatch: /a11y\.spec\.ts/ },
    {
      name: "demo",
      testMatch: /demo\.spec\.ts/,
      use: { video: { mode: "on", size: { width: 1440, height: 900 } } },
    },
  ],
});
