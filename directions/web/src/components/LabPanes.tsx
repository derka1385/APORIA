import { NOT_ASSESSED, notAssessedReason } from "../lib/assessment";
import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import type { Claim, Objection, Outcome, Run } from "../types";
import type { ReplayState, TrialState } from "../lib/replay";
import { agentLabel, excerpt, num, shortId } from "../lib/format";
import { ArgumentMap, missingPremiseText, type MapObjection } from "./ArgumentMap";
import { useDrawer } from "./drawer";
import { Meter } from "./NoveltyPanel";
import { ClaimRef } from "./text";
import { TurnView } from "./TurnView";
import { Empty, Label, ModelBadge, OutcomeChip } from "./ui";

export function objectionNumbers(state: ReplayState, run: Run): Record<string, number> {
  const out: Record<string, number> = {};
  let i = 1;
  for (const o of state.objections) out[o.id] = i++;
  for (const o of run.objections ?? []) if (!(o.id in out)) out[o.id] = i++;
  return out;
}

function premiseText(run: Run, id: string, state?: ReplayState): string {
  return run.claims?.[id]?.text ?? run.revised_premises?.[id] ?? state?.revised.find((r) => r.id === id)?.text ?? "";
}

function objectionStatus(state: ReplayState, id: string): Outcome | "failed" | "active" | "queued" | null {
  if (state.outcomes[id]) return state.outcomes[id];
  if (state.active.has(id)) return "active";
  if (state.pickedEver.has(id)) return "queued";
  return null;
}

function StatusTag({ status }: { status: ReturnType<typeof objectionStatus> }) {
  if (status === "active")
    return <span className="rounded-[2px] bg-ink px-1.5 py-[1px] font-mono text-[0.68rem] text-paper">in trial</span>;
  if (status === "queued")
    return <span className="rounded-[2px] border border-ink px-1.5 font-mono text-[0.68rem]">picked</span>;
  if (status === null) return <span className="font-mono text-[0.68rem] text-ink-faint">not tried</span>;
  return <OutcomeChip outcome={status} />;
}

/* ───────────────────────────── left: argument map ───────────────────────────── */

export function MapPane({ run, state, nums }: { run: Run; state: ReplayState; nums: Record<string, number> }) {
  const { openClaim } = useDrawer();
  const arg = run.argument;
  const claims: Record<string, Claim> = run.claims ?? {};
  const objs: MapObjection[] = state.objections.map((o) => {
    const st = objectionStatus(state, o.id);
    return {
      id: o.id,
      target_premise_id: o.target_premise_id,
      agent: o.agent,
      family: o.family,
      outcome: st === "active" || st === "queued" ? null : st,
      active: st === "active",
      index: nums[o.id],
    };
  });
  const revised = state.revised.map((r) => ({ id: r.id, text: r.text }));
  const scrollTo = (oid: string) => document.getElementById(`objection-${oid}`)?.scrollIntoView({ block: "center", behavior: "smooth" });

  return (
    <div className="space-y-6">
      <div>
        <Label className="mb-2">Argument map</Label>
        <ArgumentMap
          argument={arg}
          claims={claims}
          revised={revised}
          objections={objs}
          onSelectClaim={(id) => openClaim(id, claims[id])}
          onSelectObjection={scrollTo}
          height={520}
        />
        <p className="mt-1.5 font-mono text-[0.68rem] text-ink-faint">
          Premises above the conclusion; objections (O1, O2…) attack the premise they name. Dashed amber = the
          Formalizer’s hidden premise. Click a node to open its quote and record.
        </p>
      </div>

      <div className="space-y-2">
        <Label>Propositional skeleton</Label>
        <p className="break-words font-mono text-[0.82rem]">{arg.skeleton || "—"}</p>
        <p className="text-[0.92rem]">
          {arg.valid === true
            ? "Valid as formalized (truth-table check)."
            : arg.valid === false
              ? "Invalid as stated (truth-table check)."
              : "Validity not determined."}
          {arg.missing_premise ? " The Formalizer proposed a hidden premise that makes it valid on re-check:" : ""}
        </p>
        {arg.missing_premise ? (
          <p className="border border-dashed border-revision_required px-3 py-2 text-[0.95rem]">
            <span className="smallcaps mr-1 text-revision_required-text">hidden premise</span>
            {missingPremiseText(arg, claims)}
            {arg.missing_premise_id ? (
              <span className="ml-1 font-mono text-[0.7rem] text-ink-faint">{shortId(arg.missing_premise_id)}</span>
            ) : null}
          </p>
        ) : null}
        {Object.keys(arg.atoms ?? {}).length ? (
          <details>
            <summary className="cursor-pointer text-[0.9rem] text-ink-soft">Atoms</summary>
            <dl className="mt-2 grid grid-cols-[1.5rem_minmax(0,1fr)] gap-x-2 gap-y-1 text-[0.9rem]">
              {Object.entries(arg.atoms).map(([k, v]) => (
                <div key={k} className="contents">
                  <dt className="font-mono text-[0.8rem]">{k}</dt>
                  <dd>{v}</dd>
                </div>
              ))}
            </dl>
          </details>
        ) : null}
      </div>

      <div>
        <Label className="mb-1">Premises</Label>
        <ol className="space-y-2 text-[0.95rem]">
          {arg.premise_ids.map((id) => (
            <li key={id} className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-2">
              <ClaimRef id={id} local={claims} label={shortId(id)} />
              <span>{claims[id]?.text ?? ""}</span>
            </li>
          ))}
          <li className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-2 border-t border-rule pt-2">
            <ClaimRef id={arg.conclusion_id} local={claims} label={shortId(arg.conclusion_id)} />
            <span>
              <span className="smallcaps mr-1 text-ink-soft">therefore</span>
              {claims[arg.conclusion_id]?.text ?? ""}
            </span>
          </li>
        </ol>
      </div>

      <div>
        <Label className="mb-1">Objections drafted so far</Label>
        {state.objections.length ? (
          <ol className="space-y-3">
            {state.objections.map((o) => (
              <ObjectionRow key={o.id} o={o} n={nums[o.id]} run={run} state={state} />
            ))}
          </ol>
        ) : (
          <p className="text-[0.92rem] text-ink-soft">None yet at this point in the replay.</p>
        )}
      </div>
    </div>
  );
}

function ObjectionRow({ o, n, run, state }: { o: Objection; n: number; run: Run; state: ReplayState }) {
  const nov = state.novelty[o.id];
  const st = objectionStatus(state, o.id);
  const hasTrial = (run.trials ?? []).some((t) => t.objection_id === o.id);
  return (
    <li id={`objection-${o.id}`} className="scroll-mt-20 border-t border-rule pt-2.5">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <span className="font-serif text-[1rem] italic">O{n}</span>
        <span className="text-[0.95rem] font-medium">{agentLabel(o.agent)}</span>
        <ModelBadge family={o.family} model={o.model} />
        <StatusTag status={st} />
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-[0.85rem] text-ink-soft">
        <span>
          targets <span className="font-mono text-[0.78rem] text-ink">{shortId(o.target_premise_id)}</span>
          {o.depth ? <span className="font-mono text-[0.7rem]"> · depth {o.depth}</span> : null}
          {o.tradition ? <span> · {o.tradition}</span> : null}
        </span>
        {nov ? (
          <span className="inline-flex items-center gap-2">
            novelty{" "}
            {nov.novelty === null ? (
              <span className="font-mono text-[0.72rem]" title={notAssessedReason(nov)}>
                {NOT_ASSESSED.toLowerCase()}: {notAssessedReason(nov)}
              </span>
            ) : (
              <Meter value={nov.novelty} label="novelty" />
            )}
            <span className="font-mono text-[0.7rem]">{nov.records_searched} searched</span>
          </span>
        ) : (
          <span className="font-mono text-[0.7rem] text-ink-faint">prior-art check pending</span>
        )}
      </div>
      <details className="mt-1">
        <summary className="cursor-pointer text-[0.88rem] text-ink-soft">{excerpt(o.text, 110)}</summary>
        <p className="turn-body mt-1.5 whitespace-pre-line">{o.text}</p>
        {o.premise_fails_because ? (
          <p className="mt-1.5 text-[0.9rem]">
            <span className="smallcaps mr-1 text-ink-soft">why the premise fails</span>
            {o.premise_fails_because}
          </p>
        ) : null}
      </details>
      {hasTrial && st !== null && st !== "queued" && st !== "active" ? (
        <Link to={`/trial/${encodeURIComponent(`trial-${o.id}`)}`} className="link mt-1 inline-block text-[0.88rem]">
          Full trial →
        </Link>
      ) : null}
      <span className="sr-only">Target premise text: {premiseText(run, o.target_premise_id, state)}</span>
    </li>
  );
}

/* ───────────────────────────── center: trials ───────────────────────────── */

const EXCHANGE_LABEL: Record<number, string> = { 0: "Pre-screen", 1: "Defender A exchange", 2: "Defender B exchange" };

export function TrialsPane({
  run,
  state,
  nums,
  log,
  follow,
}: {
  run: Run;
  state: ReplayState;
  nums: Record<string, number>;
  log: string[];
  follow: boolean;
}) {
  const byId = new Map<string, Objection>((run.objections ?? []).map((o) => [o.id, o]));
  for (const o of state.objections) byId.set(o.id, o);
  return (
    <div className="space-y-6">
      <div>
        <Label className="mb-1.5">Lab notebook</Label>
        {log.length ? (
          <ol className="space-y-0.5 font-mono text-[0.74rem] leading-relaxed text-ink-soft" aria-label="Most recent events">
            {log.map((l, i) => (
              <li key={`${state.cursor}-${i}`} className={i === log.length - 1 ? "text-ink" : ""}>
                {l}
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-[0.92rem] text-ink-soft">Nothing has happened yet. Press play.</p>
        )}
      </div>
      <div>
        <Label className="mb-2">Trials, round by round</Label>
        {state.trials.length ? (
          <ol className="space-y-5">
            {state.trials.map((tr) => (
              <TrialCard
                key={tr.trial_id}
                tr={tr}
                o={byId.get(tr.objection_id)}
                n={nums[tr.objection_id]}
                run={run}
                hot={state.lastTrialId === tr.trial_id}
                follow={follow}
              />
            ))}
          </ol>
        ) : (
          <Empty>No trial has opened yet at this point in the replay. The Director opens trials after the prior-art checks.</Empty>
        )}
      </div>
    </div>
  );
}

function TrialCard({
  tr,
  o,
  n,
  run,
  hot,
  follow,
}: {
  tr: TrialState;
  o?: Objection;
  n?: number;
  run: Run;
  hot: boolean;
  follow: boolean;
}) {
  const [open, setOpen] = useState<boolean | null>(null);
  const expanded = open ?? (!tr.ended || hot);
  const lastRef = useRef<HTMLDivElement>(null);
  const full = (run.trials ?? []).find((t) => t.id === tr.trial_id);
  useEffect(() => {
    if (!hot || !follow || !expanded) return;
    if (!window.matchMedia("(min-width: 1280px)").matches) return;
    lastRef.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [hot, follow, expanded, tr.turns.length]);

  const groups = new Map<number, typeof tr.turns>();
  for (const t of tr.turns) {
    const g = groups.get(t.exchange) ?? [];
    g.push(t);
    groups.set(t.exchange, g);
  }
  const status = tr.ended ? (tr.status === "failed" ? "failed" : tr.outcome) : null;
  return (
    <li className={`border border-rule bg-[#1B1F23] ${hot ? "outline outline-1 outline-ink" : ""}`}>
      <div className="flex flex-wrap items-start justify-between gap-2 border-b border-rule px-3 py-2.5">
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-serif text-[1rem] italic">{n ? `O${n}` : shortId(tr.objection_id)}</span>
            {o ? <span className="text-[0.95rem] font-medium">{agentLabel(o.agent)}</span> : null}
            {o ? <ModelBadge family={o.family} model={o.model} /> : null}
          </div>
          {o ? (
            <p className="text-[0.88rem] text-ink-soft">
              against <span className="font-mono text-[0.76rem] text-ink">{shortId(o.target_premise_id)}</span> —{" "}
              {excerpt(premiseText(run, o.target_premise_id), 120)}
            </p>
          ) : null}
        </div>
        <div className="flex items-center gap-2">
          {tr.ended ? <OutcomeChip outcome={status} /> : <span className="rounded-[2px] bg-ink px-1.5 py-[1px] font-mono text-[0.68rem] text-paper">in progress</span>}
          <button type="button" className="btn btn-quiet" aria-expanded={expanded} onClick={() => setOpen(!expanded)}>
            {expanded ? "Fold" : "Transcript"}
          </button>
        </div>
      </div>
      {tr.ended && full && (full.rationale || full.error) ? (
        <p className="px-3 pt-2 text-[0.92rem]">
          {full.status === "failed" ? <span className="font-mono text-[0.78rem]">error: {full.error}</span> : excerpt(full.rationale, 260)}
        </p>
      ) : null}
      {expanded ? (
        <div className="space-y-4 px-3 py-3">
          {o ? (
            <details>
              <summary className="cursor-pointer text-[0.88rem] text-ink-soft">The objection</summary>
              <p className="turn-body mt-1.5 whitespace-pre-line">{o.text}</p>
            </details>
          ) : null}
          {tr.turns.length ? (
            [...groups.entries()]
              .sort((a, b) => a[0] - b[0])
              .map(([ex, turns]) => (
                <div key={ex} className="space-y-3">
                  <div className="smallcaps text-[0.85rem] text-ink-faint">{EXCHANGE_LABEL[ex] ?? `Exchange ${ex}`}</div>
                  {turns.map((t, i) => (
                    <TurnView key={i} turn={t} local={run.claims} fresh={hot && t === tr.turns[tr.turns.length - 1]} />
                  ))}
                </div>
              ))
          ) : (
            <p className="font-mono text-[0.78rem] text-ink-soft">Waiting for the Referee’s pre-screen…</p>
          )}
          <div ref={lastRef} />
        </div>
      ) : null}
      <div className="flex justify-end px-3 pb-2.5">
        <Link to={`/trial/${encodeURIComponent(tr.trial_id)}`} className="link text-[0.85rem]">
          Full trial page →
        </Link>
      </div>
    </li>
  );
}

/* ───────────────────────────── right: Director ───────────────────────────── */

export function DirectorPane({
  state,
  nums,
  briefTitles,
}: {
  state: ReplayState;
  nums: Record<string, number>;
  briefTitles: Record<string, string>;
}) {
  const q = state.queue;
  return (
    <div className="space-y-6">
      <div>
        <Label>Director queue</Label>
        <p className="mt-1 font-mono text-[0.72rem] text-ink-soft">priority = S · N · (0.5 + 0.5·C) + 0.1·E</p>
        <p className="text-[0.8rem] text-ink-faint">
          S survival · N novelty · C share of arguments resting on the premise · E untried agent/family. Plain code, no
          model.
        </p>
        {q ? (
          <>
            <p className="mt-3 font-mono text-[0.75rem]">
              step {q.step} · {q.queue.length} ranked · {q.picked.length} picked
            </p>
            <ol className="mt-2 space-y-1.5">
              {q.queue.map((r, i) => {
                const picked = q.picked.includes(r.objection_id);
                return (
                  <li
                    key={r.objection_id}
                    className={`border-l-2 py-1 pl-2.5 ${picked ? "border-ink bg-paper-deep" : "border-rule"}`}
                  >
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 text-[0.86rem]">
                      <span className="font-mono text-[0.7rem] text-ink-faint">#{i + 1}</span>
                      <span className="font-serif text-[0.98rem] italic">{nums[r.objection_id] ? `O${nums[r.objection_id]}` : shortId(r.objection_id)}</span>
                      <span>{agentLabel(r.agent)}</span>
                      <span className="font-mono text-[0.68rem] text-ink-soft">{r.family}</span>
                      {picked ? <span className="rounded-[2px] bg-ink px-1 font-mono text-[0.62rem] text-paper">picked</span> : null}
                    </div>
                    <div className="font-mono text-[0.68rem] text-ink-soft">
                      → {shortId(r.target_premise_id)}
                      {r.depth ? ` · depth ${r.depth}` : ""}
                    </div>
                    <div className="font-mono text-[0.68rem]">
                      S {num(r.S)} · N {num(r.N)} · C {num(r.C)} · E {r.E} ={" "}
                      <span className="font-medium">{num(r.priority, 3)}</span>
                    </div>
                  </li>
                );
              })}
            </ol>
          </>
        ) : (
          <p className="mt-3 text-[0.9rem] text-ink-soft">The Director has not ranked anything yet at this point in the replay.</p>
        )}
      </div>

      {state.revised.length ? (
        <div>
          <Label className="mb-1">Revised premises</Label>
          <ul className="space-y-2">
            {state.revised.map((r) => (
              <li key={r.id} className="border border-dotted border-revision_required px-2.5 py-1.5 text-[0.9rem]">
                <span className="mr-1 font-mono text-[0.7rem] text-revision_required-text">{shortId(r.id)}</span>
                {r.text}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {state.naive.length ? (
        <div>
          <Label className="mb-1">Naive Questioner</Label>
          <ul className="space-y-1.5 text-[0.9rem]">
            {state.naive.map((nq, i) => (
              <li key={i}>
                “{nq.question}”{" "}
                <span className="font-mono text-[0.68rem] text-ink-soft">{nq.sharpened ? "sharpened into an objection" : "not sharpened; does not count"}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div>
        <Label className="mb-1">Briefs written</Label>
        {state.briefs.length ? (
          <ul className="space-y-2">
            {state.briefs.map((b) => (
              <li key={b.brief_id} className="text-[0.92rem]">
                <Link to={`/brief/${encodeURIComponent(b.brief_id)}`} className="link">
                  {briefTitles[b.brief_id] ?? b.brief_id}
                </Link>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-[0.9rem] text-ink-soft">None yet at this point in the replay.</p>
        )}
      </div>

      {state.ended ? (
        <p className="border-t border-ink pt-2 font-mono text-[0.75rem]">run ended: {state.ended}</p>
      ) : null}
      {state.errors.length ? (
        <div className="border border-ink px-3 py-2 font-mono text-[0.75rem]">
          {state.errors.map((e, i) => (
            <p key={i}>{e}</p>
          ))}
        </div>
      ) : null}
    </div>
  );
}
