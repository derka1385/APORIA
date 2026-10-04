import { expect, test } from "@playwright/test";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

const DATA = fileURLToPath(new URL("../public/data/", import.meta.url));
const index = JSON.parse(fs.readFileSync(`${DATA}index.json`, "utf8")) as { runs: { run_id: string }[] };

test("live: /lab streams a run over SSE from the API", async ({ page }) => {
  await page.goto(`/runs/${index.runs[0].run_id}`);
  await page.getByRole("button", { name: "Run live" }).click();
  // the replay button flips to "Back to replay (<status>)" while events arrive
  await expect(page.getByRole("button", { name: /Back to replay \((streaming|done)\)/ })).toBeVisible({ timeout: 60_000 });
});

test("live: /atlas prior-art search uses the API index", async ({ page }) => {
  await page.goto("/atlas");
  await page.getByRole("button", { name: "live index" }).click();
  await page.getByRole("textbox").first().fill("God would make himself known to anyone open to a relationship");
  const resp = page.waitForResponse((r) => r.url().includes("/api/prior-art") && r.status() === 200);
  await page.getByRole("button", { name: "Search the corpus" }).click();
  const r = await resp;
  const body = (await r.json()) as { hits: unknown[]; records_searched: number };
  expect(body.hits.length).toBeGreaterThan(0);
  expect(body.records_searched).toBeGreaterThan(1000);
});
