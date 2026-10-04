import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import type { Run, Turn } from "../../types";
import { attributeTurns, describeEvent, replay } from "../replay";
import { assessedNovelty, trialFailure } from "../assessment";

const turn = (speaker: Turn["speaker"], phase: Turn["phase"], exchange: number, content: string): Turn => ({
  exchange, speaker, phase, content, model: "m", family: "f", cited_claim_ids: [], struck_claim_ids: [],
  concedes: false, revised_premise: null,
});

describe("attributeTurns", () => {
  it("assigns interleaved turns of parallel trials to the right trial", () => {
    const a = turn("defender_a", "reply", 1, "same words");
    const b = turn("defender_a", "reply", 1, "same words");
    const run = {
      trials: [{ id: "trial-1", rounds: [a] }, { id: "trial-2", rounds: [b] }],
      events: [
        { t: 1, type: "turn", turn: b, trial_id: "trial-2" },
        { t: 2, type: "turn", turn: a, trial_id: "trial-1" },
      ],
    } as unknown as Pick<Run, "events" | "trials">;
    const out = attributeTurns(run);
    expect(out.map((x) => x?.trialId)).toEqual(["trial-2", "trial-1"]);
  });
});

// Integration: every exported run replays to the end with every turn attributed and the
// final outcomes equal to the trials stored in the run file.
const DATA = path.resolve(__dirname, "../../../public/data");
const runDirs = [path.join(DATA, "runs")].concat(
  fs.existsSync(path.join(DATA, "topics"))
    ? fs.readdirSync(path.join(DATA, "topics")).map((t) => path.join(DATA, "topics", t, "runs"))
    : [],
);
const files = runDirs
  .filter((d) => fs.existsSync(d))
  .flatMap((d) => fs.readdirSync(d).filter((f) => f.endsWith(".json")).map((f) => path.join(d, f)));

describe.skipIf(!files.length)("exported runs replay faithfully", () => {
  for (const f of files) {
    it(path.relative(DATA, f), () => {
      const run = JSON.parse(fs.readFileSync(f, "utf8")) as Run;
      const attribution = attributeTurns(run);
      run.events.forEach((ev, i) => {
        if (ev.type === "turn") expect(attribution[i], `turn event ${i} unattributed`).not.toBeNull();
      });
      const s = replay(run.events, run.events.length, attribution);
      for (const t of run.trials)
        expect(s.outcomes[t.objection_id]).toBe(t.status === "failed" ? "failed" : t.outcome ?? "failed");
      expect(s.briefs.map((b) => b.brief_id).sort()).toEqual([...run.briefs].sort());
      expect(s.ended).toBe(run.stop_reason);
      expect(replay(run.events, 0, attribution).trials).toEqual([]);
    });
  }
});

describe("failure states", () => {
  const ev = (e: object) => e as unknown as Run["events"][number];

  it("an unassessed novelty check stays null and is described in words", () => {
    const n = ev({ t: 1, type: "novelty", objection_id: "o1", novelty: null, status: "rerank_failed",
      reason: "The literature assessment could not be completed. Retry the check.", records_searched: 900, nearest: [] });
    const s = replay([n], 1);
    expect(s.novelty.o1.novelty).toBeNull();
    const text = describeEvent(n);
    expect(text).toContain("not assessed");
    expect(text).not.toMatch(/NaN|1\.00|0\.00/);
  });

  it("a number with a failure status is not a score", () => {
    expect(assessedNovelty({ novelty: 1, status: "no_candidates" })).toBeNull();
    expect(assessedNovelty({ novelty: 0.42, status: "assessed" })).toBe(0.42);
    expect(assessedNovelty({ novelty: 0.42 })).toBe(0.42); // old exports: screened when exported
  });

  it("a failed trial never keeps an outcome, even a stale one", () => {
    const end = ev({ t: 2, type: "trial_end", trial_id: "trial-o1", objection_id: "o1", outcome: "standing",
      status: "failed", error: "incomplete defender assessment: missing defender_b", missing_labels: ["defender_b"] });
    const s = replay([end], 1);
    expect(s.outcomes.o1).toBe("failed");
    expect(s.trials[0].outcome).toBeNull();
    expect(describeEvent(end)).toContain("the referee assessment for Defender B is unavailable");
    expect(trialFailure({ missing_labels: ["defender_a", "defender_b"] })).toContain("assessments for Defender A and Defender B are");
  });
});
