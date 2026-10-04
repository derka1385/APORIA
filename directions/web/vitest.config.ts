import { defineConfig } from "vitest/config";

// Unit + data-integration tests live next to the code; Playwright specs in tests/ run separately.
export default defineConfig({
  test: { include: ["src/**/*.test.ts"] },
});
