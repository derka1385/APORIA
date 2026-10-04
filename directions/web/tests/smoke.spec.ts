import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

// Screenshots land in <repo>/docs/screens/<page>.png
const SHOTS = fileURLToPath(new URL("../../docs/screens/", import.meta.url));
fs.mkdirSync(SHOTS, { recursive: true });

// Network noise that says nothing about the site itself (web fonts offline, favicon probes).
const IGNORE = [/fonts\.(googleapis|gstatic)\.com/, /favicon/];

function watchConsole(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (msg) => {
    if (msg.type() !== "error") return;
    const text = `${msg.text()} ${msg.location()?.url ?? ""}`;
    if (!IGNORE.some((r) => r.test(text))) errors.push(text);
  });
  page.on("pageerror", (err) => errors.push(`pageerror: ${err.message}`));
  return errors;
}

// The lab's panes are sized in viewport units, so a full-page capture would stretch them: shoot the viewport.
async function visit(page: Page, url: string, shot: string, fullPage = true) {
  const errors = watchConsole(page);
  await page.goto(url);
  const h1 = page.getByRole("heading", { level: 1 }).first();
  await expect(h1).toBeVisible({ timeout: 20_000 });
  await expect(h1).not.toHaveText("");
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(600); // let the argument map fit its view
  await page.screenshot({ path: `${SHOTS}${shot}.png`, fullPage });
  expect(errors, `console errors on ${url}`).toEqual([]);
}

interface IndexFile {
  runs: { run_id: string }[];
}
interface BriefRow {
  id: string;
}

test.describe("Crux Lab smoke", () => {
  let runId: string | null = null;
  let briefId: string | null = null;

  test.beforeAll(async ({ request }) => {
    const ix = await request.get("/data/index.json");
    if (ix.ok()) runId = ((await ix.json()) as IndexFile).runs?.[0]?.run_id ?? null;
    const b = await request.get("/data/briefs.json");
    if (b.ok()) briefId = ((await b.json()) as BriefRow[])[0]?.id ?? null;
  });

  test("landing", async ({ page }) => {
    await visit(page, "/", "landing");
    await expect(page.getByRole("heading", { name: "Research directions" })).toBeVisible();
  });

  test("briefs", async ({ page }) => {
    await visit(page, "/briefs", "briefs");
  });

  test("first brief", async ({ page }) => {
    test.skip(!briefId, "no brief exported");
    await visit(page, `/brief/${encodeURIComponent(briefId!)}`, "brief");
    await expect(page.getByText("Further human review required.").first()).toBeVisible();
  });

  test("first run, lab", async ({ page }) => {
    test.skip(!runId, "no run exported");
    await visit(page, `/runs/${encodeURIComponent(runId!)}?at=end`, "lab", false);
    await expect(page.getByText("Director queue")).toBeVisible();
  });

  test("first trial", async ({ page, request }) => {
    test.skip(!runId, "no run exported");
    const run = await (await request.get(`/data/runs/${runId}.json`)).json();
    const trialId: string | undefined = run.trials?.[0]?.id;
    test.skip(!trialId, "run has no trials");
    await visit(page, `/trial/${encodeURIComponent(trialId!)}`, "trial");
  });

  test("atlas", async ({ page }) => {
    await visit(page, "/atlas", "atlas");
    await page.getByLabel("Describe the move").fill("God would make himself known to anyone open to a relationship");
    await page.getByRole("button", { name: "Search the corpus" }).click();
    await expect(page.getByText(/claims searched/).first()).toBeVisible();
    await page.screenshot({ path: `${SHOTS}atlas-search.png`, fullPage: false });
  });

  test("results", async ({ page }) => {
    await visit(page, "/results", "results");
  });

  test("about", async ({ page }) => {
    await visit(page, "/about", "about");
  });

  test("second topic", async ({ page, request }) => {
    const topics = (await (await request.get("/data/topics.json")).json()) as {
      topics: { slug: string; name: string; status: string; default: boolean; data: string }[];
    };
    const other = topics.topics.find((t) => !t.default && t.status === "ready");
    test.skip(!other, "only one topic has been run");
    await visit(page, `/?topic=${other!.slug}`, "landing-topic2");
    await expect(page.getByText(`Topic: ${other!.name}`).first()).toBeVisible();
    await expect(page.getByText("strongest lead", { exact: true }).first()).toBeVisible();
    // a novelty check that could not be completed is shown as not assessed, never as a score
    const ix = (await (await request.get(`/data/${other!.data}index.json`)).json()) as IndexFile;
    for (const r of ix.runs) {
      const run = await (await request.get(`/data/${other!.data}runs/${r.run_id}.json`)).json();
      const na = Object.values(run.novelty as Record<string, { status?: string }>).some((n) => n.status && n.status !== "assessed");
      if (!na) continue;
      await page.goto(`/runs/${encodeURIComponent(r.run_id)}?topic=${other!.slug}&at=end`);
      await expect(page.getByText(/not assessed: /).first()).toBeVisible({ timeout: 20_000 });
      break;
    }
  });

  test("mobile landing", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await visit(page, "/", "landing-mobile");
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow, "no horizontal scroll on phones").toBeLessThanOrEqual(1);
  });

  test("mobile lab", async ({ page }) => {
    test.skip(!runId, "no run exported");
    await page.setViewportSize({ width: 390, height: 844 });
    await visit(page, `/runs/${encodeURIComponent(runId!)}?at=end`, "lab-mobile");
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(overflow, "no horizontal scroll on phones").toBeLessThanOrEqual(1);
  });
});
