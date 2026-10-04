import { expect, test } from "@playwright/test";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

// Walkthrough recorded as video: landing -> first research direction (+ its referee assessment and revision) ->
// its run, autoplaying -> a trial -> results -> topics -> start a topic.
// The finished recording is copied to <repo>/docs/demo.webm.
const OUT = fileURLToPath(new URL("../../docs/demo.webm", import.meta.url));

test("demo walkthrough", async ({ page, request }) => {
  test.setTimeout(180_000);
  const briefs = (await (await request.get("/data/briefs.json")).json()) as { id: string; run_id: string | null }[];
  const index = (await (await request.get("/data/index.json")).json()) as { runs: { run_id: string }[] };

  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.waitForTimeout(2500);

  // the research directions are the point of the site
  await page.locator("#directions").scrollIntoViewIfNeeded();
  await page.waitForTimeout(2500);

  let runId = index.runs?.[0]?.run_id ?? null;
  if (briefs.length) {
    // the strongest lead: the card above the list
    const lead = page.locator("#lead-h a");
    await ((await lead.count()) ? lead.first() : page.locator("#directions ol li h3 a").first()).click();
    await expect(page.getByText("Further human review required.").first()).toBeVisible();
    await page.waitForTimeout(3000);
    await page.mouse.wheel(0, 700);
    await page.waitForTimeout(2500);
    // the referee's assessment and the revision round, at the bottom of the brief
    const toQuality = page.getByRole("link", { name: /Referee.s assessment/ });
    if (await toQuality.count()) {
      await toQuality.first().click();
      await page.waitForTimeout(3500);
      await page.mouse.wheel(0, 800);
      await page.waitForTimeout(3000);
      await page.mouse.wheel(0, 800);
      await page.waitForTimeout(2500);
    }
    runId = briefs[0].run_id ?? runId;
  }
  test.skip(!runId, "no run exported");

  // the run, replayed with autoplay for about twenty seconds
  await page.goto(`/runs/${encodeURIComponent(runId!)}?speed=2`);
  await expect(page.getByText("Director queue")).toBeVisible();
  await page.waitForTimeout(1500);
  await page.locator("#pane-map").scrollIntoViewIfNeeded();
  await page.waitForTimeout(20_000);

  // the first trial, in full
  const run = await (await request.get(`/data/runs/${runId}.json`)).json();
  const trialId: string | undefined = (run.trials ?? []).find((t: { rounds: unknown[] }) => t.rounds.length > 1)?.id ?? run.trials?.[0]?.id;
  if (trialId) {
    await page.goto(`/trial/${encodeURIComponent(trialId)}`);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await page.waitForTimeout(3000);
    for (let i = 0; i < 4; i++) {
      await page.mouse.wheel(0, 650);
      await page.waitForTimeout(1600);
    }
  }

  await page.goto("/results");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.waitForTimeout(3500);
  await page.mouse.wheel(0, 700);
  await page.waitForTimeout(2500);

  // other topics: what has been run, what is set up, and how a student starts their own
  await page.goto("/topics");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.waitForTimeout(3000);
  await page.mouse.wheel(0, 600);
  await page.waitForTimeout(2500);
  // a second topic, run on other model families: its home page and strongest lead
  const explore = page.getByRole("button", { name: "Explore this topic →" });
  if (await explore.count()) {
    await explore.first().click();
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await page.waitForTimeout(2000);
    await page.locator("#directions").scrollIntoViewIfNeeded();
    await page.waitForTimeout(3500);
  }
  await page.goto("/start?from=fine-tuning");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.waitForTimeout(3500);

  const video = page.video();
  await page.close();
  if (video) {
    fs.mkdirSync(fileURLToPath(new URL("../../docs/", import.meta.url)), { recursive: true });
    await video.saveAs(OUT);
  }
});
