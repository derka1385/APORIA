import type { NearestMatch, Objection, Outcome, QueueRow, Run, RunEvent, Turn } from "../types";
import { assessedNovelty, NOT_ASSESSED, notAssessedReason, trialFailure } from "./assessment";
import { agentLabel, PHASE_LABEL, shortId, speakerLabel } from "./format";

export interface TrialState {
  trial_id: string;
  objection_id: string;
  turns: Turn[];
  outcome: Outcome | null;
  status: string | null;
  error?: string | null;
  missing_labels?: string[];
  ended: boolean;
}

/** One objection's prior-art check as the replay knows it; novelty null = not assessed. */
export interface NoveltyState {
  novelty: number | null;
  status?: string;
  reason?: string;
  records_searched: number;
  nearest: NearestMatch[];
}

export interface ReplayState {
  cursor: number;
  objections: Objection[];
  novelty: Record<string, NoveltyState>;
  queue: { step: number; queue: QueueRow[]; picked: string[] } | null;
  pickedEver: Set<string>;
  trials: TrialState[];
  outcomes: Record<string, Outcome | "failed">;
  active: Set<string>;
  revised: { id: string; text: string; from_trial: string }[];
  briefs: { brief_id: string; objection_id: string }[];
  naive: { question: string; sharpened: boolean }[];
  ended: string | null;
  lastTrialId: string | null;
  lastEvent: RunEvent | null;
  errors: string[];
}

type LooseEvent = RunEvent | { t?: number; type: "error"; error: string };

const turnKey = (t: Pick<Turn, "speaker" | "phase" | "exchange" | "content">) =>
  `${t.speaker}|${t.phase}|${t.exchange}|${t.content}`;

/**
 * Defender and objector turn events are emitted without a trial id (only pre-screen and label turns
 * carry one), and parallel trials interleave. Attribute each turn event to its trial by matching it
 * against the trials' stored rounds, which also hold the verified / struck citation lists.
 */
export function attributeTurns(run: Pick<Run, "events" | "trials">): ({ trialId: string; turn: Turn } | null)[] {
  const pool = new Map<string, { trialId: string; turn: Turn; used: boolean }[]>();
  for (const tr of run.trials ?? []) {
    for (const turn of tr.rounds ?? []) {
      const k = turnKey(turn);
      const list = pool.get(k) ?? [];
      list.push({ trialId: tr.id, turn, used: false });
      pool.set(k, list);
    }
  }
  return (run.events ?? []).map((ev) => {
    if (ev.type !== "turn") return null;
    const list = pool.get(turnKey(ev.turn)) ?? [];
    const preferred = ev.trial_id ? list.find((x) => !x.used && x.trialId === ev.trial_id) : undefined;
    const hit = preferred ?? list.find((x) => !x.used);
    if (hit) {
      hit.used = true;
      return { trialId: hit.trialId, turn: hit.turn };
    }
    return ev.trial_id ? { trialId: ev.trial_id, turn: ev.turn } : null;
  });
}

export function emptyState(): ReplayState {
  return {
    cursor: 0,
    objections: [],
    novelty: {},
    queue: null,
    pickedEver: new Set(),
    trials: [],
    outcomes: {},
    active: new Set(),
    revised: [],
    briefs: [],
    naive: [],
    ended: null,
    lastTrialId: null,
    lastEvent: null,
    errors: [],
  };
}

export function replay(
  events: LooseEvent[],
  upto: number,
  attribution: ({ trialId: string; turn: Turn } | null)[] = [],
): ReplayState {
  const s = emptyState();
  const byTrial = new Map<string, TrialState>();
  const ensureTrial = (trial_id: string, objection_id: string) => {
    let tr = byTrial.get(trial_id);
    if (!tr) {
      tr = { trial_id, objection_id, turns: [], outcome: null, status: null, ended: false };
      byTrial.set(trial_id, tr);
      s.trials.push(tr);
    }
    return tr;
  };
  const n = Math.min(upto, events.length);
  for (let i = 0; i < n; i++) {
    const ev = events[i];
    s.lastTrialId = null;
    switch (ev.type) {
      case "objection":
        if (!s.objections.some((o) => o.id === ev.objection.id)) s.objections.push(ev.objection);
        break;
      case "naive_question":
        s.naive.push({ question: ev.question, sharpened: ev.sharpened });
        break;
      case "novelty":
        s.novelty[ev.objection_id] = {
          novelty: assessedNovelty(ev),
          status: ev.status,
          reason: ev.reason,
          records_searched: ev.records_searched,
          nearest: ev.nearest ?? [],
        };
        break;
      case "queue":
        s.queue = { step: ev.step, queue: ev.queue ?? [], picked: ev.picked ?? [] };
        for (const p of ev.picked ?? []) s.pickedEver.add(p);
        break;
      case "trial_start": {
        ensureTrial(ev.trial_id, ev.objection_id);
        s.active.add(ev.objection_id);
        s.lastTrialId = ev.trial_id;
        break;
      }
      case "turn": {
        const a = attribution[i];
        let trialId = a?.trialId ?? ev.trial_id ?? null;
        if (!trialId) {
          const open = s.trials.filter((t) => !t.ended);
          trialId = open.length ? open[open.length - 1].trial_id : null;
        }
        if (trialId) {
          const tr = ensureTrial(trialId, ev.objection_id ?? trialId.replace(/^trial-/, ""));
          tr.turns.push(a?.turn ?? ev.turn);
          s.lastTrialId = trialId;
        }
        break;
      }
      case "trial_end": {
        const tr = ensureTrial(ev.trial_id, ev.objection_id);
        tr.ended = true;
        const failed = ev.status === "failed";
        tr.outcome = failed ? null : ev.outcome ?? null;     // a failed trial has no outcome, whatever it carries
        tr.status = ev.status ?? null;
        tr.error = ev.error ?? null;
        tr.missing_labels = ev.missing_labels ?? [];
        s.outcomes[ev.objection_id] = failed ? "failed" : ev.outcome ?? "failed";
        s.active.delete(ev.objection_id);
        s.lastTrialId = ev.trial_id;
        break;
      }
      case "revised_premise":
        s.revised.push({ id: ev.id, text: ev.text, from_trial: ev.from_trial });
        break;
      case "brief":
        s.briefs.push({ brief_id: ev.brief_id, objection_id: ev.objection_id });
        break;
      case "run_end":
        s.ended = ev.stop_reason;
        break;
      case "error":
        s.errors.push(ev.error);
        break;
      default:
        break;
    }
    s.lastEvent = ev.type === "error" ? s.lastEvent : ev;
  }
  s.cursor = n;
  return s;
}

/** Milliseconds to dwell on an event at 1x speed (turns get reading time). */
export function dwell(ev: LooseEvent | undefined): number {
  if (!ev) return 600;
  switch (ev.type) {
    case "turn":
      return 1500;
    case "queue":
      return 1100;
    case "objection":
      return 700;
    case "trial_start":
    case "trial_end":
    case "revised_premise":
    case "brief":
      return 900;
    default:
      return 450;
  }
}

export function describeEvent(ev: LooseEvent | null | undefined, premiseLabel?: (id: string) => string): string {
  if (!ev) return "Ready. Press play to replay the run.";
  const p = (id: string) => (premiseLabel ? premiseLabel(id) : shortId(id));
  switch (ev.type) {
    case "run_start":
      return `Run started on argument ${shortId(ev.argument_id)}.`;
    case "objection":
      return `${agentLabel(ev.objection.agent)} (${ev.objection.family}) drafted an objection to ${p(ev.objection.target_premise_id)}.`;
    case "naive_question":
      return `The Naive Questioner asked a question${ev.sharpened ? "; another agent sharpened it into an objection" : "; it was not sharpened into an objection"}.`;
    case "novelty":
      {
        const n = assessedNovelty(ev);
        return n === null
          ? `Prior-art check on ${shortId(ev.objection_id)}: ${NOT_ASSESSED.toLowerCase()}. ${notAssessedReason(ev)}`
          : `Prior-art check on ${shortId(ev.objection_id)}: novelty ${n.toFixed(2)} across ${ev.records_searched} records searched.`;
      }
    case "queue":
      return `Director step ${ev.step}: ranked ${ev.queue.length} untried objection${ev.queue.length === 1 ? "" : "s"}, picked ${ev.picked.length} for trial.`;
    case "trial_start":
      return `Trial opened for objection ${shortId(ev.objection_id)}.`;
    case "turn":
      return `${speakerLabel(ev.turn.speaker)}, ${PHASE_LABEL[ev.turn.phase] ?? ev.turn.phase} (${ev.turn.family} · ${ev.turn.model}).`;
    case "trial_end":
      return ev.status === "failed"
        ? `${shortId(ev.objection_id)}: ${trialFailure(ev)}`
        : `Trial ${shortId(ev.objection_id)} closed: ${ev.outcome ?? "no outcome"}.`;
    case "revised_premise":
      return `Revised premise ${shortId(ev.id)} adopted; the Director may now attack it.`;
    case "brief":
      return `Research brief written for objection ${shortId(ev.objection_id)}.`;
    case "run_end":
      return `Run ended: ${ev.stop_reason}.`;
    case "error":
      return `Live run error: ${ev.error}`;
    default:
      return "";
  }
}

export type { LooseEvent };
