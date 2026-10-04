import { assessedNovelty } from "../lib/assessment";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router";
import { DirectorPane, MapPane, objectionNumbers, TrialsPane } from "../components/LabPanes";
import { OutcomeBar } from "../components/OutcomeBar";
import { DataState, Disclaimer, Label, ModelBadge } from "../components/ui";
import { API_URL, liveRunURL } from "../lib/api";
import { useJSON } from "../lib/data";
import { displayTitle, when } from "../lib/format";
import { attributeTurns, describeEvent, dwell, replay, type LooseEvent } from "../lib/replay";
import type { BriefSummary, Index, Outcome, Run } from "../types";

export default function Lab() {
  const { run: runId = "" } = useParams();
  const load = useJSON<Run>(`runs/${runId}.json`);
  return (
    <div className="mx-auto max-w-[1400px] px-4 sm:px-6">
      <DataState load={load} what={`run ${runId}`}>
        {(run) => <LabView key={run.run_id} run={run} />}
      </DataState>
    </div>
  );
}

const SPEEDS = [0.5, 1, 2, 4, 8];

function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

function LabView({ run }: { run: Run }) {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const index = useJSON<Index>("index.json");
  const briefsLoad = useJSON<BriefSummary[]>("briefs.json");
  const staticEvents = useMemo(() => (run.events ?? []) as LooseEvent[], [run]);
  const attribution = useMemo(() => attributeTurns(run), [run]);

  const [live, setLive] = useState<{ events: LooseEvent[]; status: "connecting" | "streaming" | "done" | "error"; error?: string } | null>(null);
  const events = live ? live.events : staticEvents;
  const startAtEnd = params.get("at") === "end" || prefersReducedMotion();
  const [cursor, setCursor] = useState(() => (startAtEnd ? staticEvents.length : 0));
  const [playing, setPlaying] = useState(() => !startAtEnd && staticEvents.length > 0);
  const [speed, setSpeed] = useState(() => {
    const s = Number(params.get("speed"));
    return SPEEDS.includes(s) ? s : 1;
  });
  const total = events.length;
  const pos = live ? total : Math.min(cursor, total);

  const isPlaying = playing && pos < total;
  const state = useMemo(() => replay(events, pos, live ? [] : attribution), [events, pos, live, attribution]);
  const nums = useMemo(() => objectionNumbers(state, run), [state, run]);

  // autoplay
  useEffect(() => {
    if (!playing || live || cursor >= total) return;
    const t = window.setTimeout(() => setCursor((c) => Math.min(total, c + 1)), dwell(events[cursor]) / speed);
    return () => window.clearTimeout(t);
  }, [playing, cursor, total, speed, events, live]);

  const step = useCallback(
    (d: number) => {
      setPlaying(false);
      setCursor((c) => Math.max(0, Math.min(total, c + d)));
    },
    [total],
  );

  const togglePlay = useCallback(() => {
    if (cursor >= total) {
      setCursor(0);
      setPlaying(true);
    } else setPlaying(!(playing && cursor < total));
  }, [cursor, total, playing]);

  // keyboard: space = play/pause, arrows = step
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el && (el.closest("input, textarea, select, button, a, [contenteditable=true], [role=dialog]") || e.metaKey || e.ctrlKey || e.altKey)) return;
      if (e.key === " ") {
        e.preventDefault();
        togglePlay();
      } else if (e.key === "ArrowRight") step(1);
      else if (e.key === "ArrowLeft") step(-1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [step, togglePlay]);

  // live mode (optional): stream the same RunEvent objects over SSE
  const esRef = useRef<EventSource | null>(null);
  useEffect(() => () => esRef.current?.close(), []);
  const startLive = () => {
    const url = liveRunURL(run.target.id);
    if (!url) return;
    esRef.current?.close();
    setPlaying(false);
    setLive({ events: [], status: "connecting" });
    const es = new EventSource(url);
    esRef.current = es;
    es.onmessage = (m) => {
      try {
        const ev = JSON.parse(m.data) as LooseEvent;
        setLive((l) => (l ? { ...l, status: "streaming", events: [...l.events, ev] } : l));
      } catch {
        /* ignore malformed frames */
      }
    };
    es.addEventListener("done", () => {
      es.close();
      setLive((l) => (l ? { ...l, status: "done" } : l));
    });
    es.onerror = () => {
      es.close();
      setLive((l) => (l && l.status !== "done" ? { ...l, status: "error", error: "connection to the live API closed" } : l));
    };
  };
  const stopLive = () => {
    esRef.current?.close();
    setLive(null);
  };

  const log = useMemo(() => {
    const out: string[] = [];
    for (let i = Math.max(0, pos - 5); i < pos; i++) out.push(`${String(i + 1).padStart(3, " ")}  ${describeEvent(events[i])}`);
    return out;
  }, [events, pos]);

  const briefTitles = useMemo(() => {
    const m: Record<string, string> = {};
    if (briefsLoad.status === "ready") for (const b of briefsLoad.data) m[b.id] = b.research_question;
    return m;
  }, [briefsLoad]);

  // final picture of the run (independent of the replay cursor), for the plain-language summary
  const finalOutcomes = useMemo(() => {
    const o: Partial<Record<Outcome | "failed", number>> = {};
    for (const t of run.trials ?? []) {
      const k = t.status === "failed" ? "failed" : t.outcome ?? "failed";
      o[k] = (o[k] ?? 0) + 1;
    }
    return o;
  }, [run]);

  const runs = index.status === "ready" ? index.data.runs : [];
  const t = run.target;

  return (
    <div className="pb-10">
      {/* header: plain-language summary first */}
      <section className="grid gap-x-10 gap-y-5 py-8 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-3">
            <Label>
              <Link to="/runs" className="hover:underline">
                lab
              </Link>{" "}
              / replay
            </Label>
            {runs.length > 1 ? (
              <select
                className="field py-0.5 font-mono text-[0.75rem]"
                aria-label="Switch run"
                value={run.run_id}
                onChange={(e) => navigate(`/runs/${encodeURIComponent(e.target.value)}`)}
              >
                {runs.map((r) => (
                  <option key={r.run_id} value={r.run_id}>
                    {r.run_id}
                  </option>
                ))}
              </select>
            ) : null}
          </div>
          <h1 className="mt-2 font-serif text-[2rem] font-medium leading-tight sm:text-[2.4rem]">{displayTitle(t.title)}</h1>
          <p className="mt-1 text-[0.95rem] text-ink-soft">
            {[t.authors?.join(", "), t.year, t.kind === "fresh" ? `fresh paper${t.published ? `, published ${t.published}` : ""}` : `${t.kind} target`]
              .filter(Boolean)
              .join(" · ")}
            {t.url ? (
              <>
                {" · "}
                <a href={t.url} className="link" target="_blank" rel="noreferrer">
                  source ↗
                </a>
              </>
            ) : null}
          </p>
          {t.thesis ? (
            <p className="measure mt-3 text-[1.05rem]">
              <span className="smallcaps mr-1 text-ink-soft">thesis</span>
              {t.thesis}
            </p>
          ) : null}
          <p className="measure mt-2 text-[1rem]">
            <span className="smallcaps mr-1 text-ink-soft">argument</span>
            {run.argument.title || run.argument.id}
          </p>
          {t.reason ? <p className="measure mt-2 text-[0.88rem] text-ink-soft">Why this target: {t.reason}</p> : null}
        </div>
        <div className="space-y-3 border-t border-ink pt-3 lg:border-l lg:border-t-0 lg:pl-6 lg:pt-0">
          <Label>what this run found</Label>
          <p className="text-[0.98rem]">
            {(run.objections ?? []).length} objections drafted, {(run.trials ?? []).length} taken to trial.
          </p>
          <OutcomeBar outcomes={finalOutcomes} />
          {run.briefs?.length ? (
            <div>
              <div className="smallcaps text-[0.9rem] text-ink-soft">research directions from this run</div>
              <ul className="mt-1 space-y-1.5">
                {run.briefs.map((b) => (
                  <li key={b} className="text-[0.98rem] leading-snug">
                    <Link to={`/brief/${encodeURIComponent(b)}`} className="link">
                      {briefTitles[b] ?? b}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-[0.92rem] text-ink-soft">No brief came out of this run.</p>
          )}
          <p className="font-mono text-[0.7rem] text-ink-soft">
            stopped: {run.stop_reason || "—"} · finished {when(run.finished_at)}
          </p>
          <p className="flex flex-wrap items-center gap-1.5 font-mono text-[0.7rem] text-ink-soft">
            diversity: <span className="text-ink">{run.diversity || "—"}</span>
            {Object.entries(run.models ?? {}).map(([role, label]) => {
              const [fam, ...m] = String(label).split(":");
              return (
                <span key={role} className="inline-flex items-center gap-1">
                  {role.replace(/_/g, " ")} <ModelBadge family={fam} model={m.join(":")} />
                </span>
              );
            })}
          </p>
        </div>
      </section>

      {/* transport */}
      <div className="no-print sticky top-0 z-20 -mx-4 border-y border-ink bg-paper/95 px-4 py-2 backdrop-blur-[2px] sm:-mx-6 sm:px-6">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <div className="flex items-center gap-1.5" role="group" aria-label="Replay controls">
            <button className="btn btn-quiet" onClick={() => step(-total)} disabled={!!live || pos === 0} aria-label="Jump to start">
              |◀
            </button>
            <button className="btn btn-quiet" onClick={() => step(-1)} disabled={!!live || pos === 0} aria-label="Step back">
              ◀
            </button>
            <button
              className="btn min-w-[5.2rem] justify-center"
              onClick={togglePlay}
              disabled={!!live || total === 0}
              aria-pressed={isPlaying}
            >
              {isPlaying ? "Pause" : pos >= total && total > 0 ? "Replay" : "Play"}
            </button>
            <button className="btn btn-quiet" onClick={() => step(1)} disabled={!!live || pos >= total} aria-label="Step forward">
              ▶
            </button>
            <button className="btn btn-quiet" onClick={() => step(total)} disabled={!!live || pos >= total} aria-label="Jump to end">
              ▶|
            </button>
          </div>
          <label className="flex items-center gap-1.5 font-mono text-[0.72rem]">
            speed
            <select className="field py-0.5 text-[0.72rem]" value={speed} onChange={(e) => setSpeed(Number(e.target.value))} disabled={!!live}>
              {SPEEDS.map((s) => (
                <option key={s} value={s}>
                  {s}×
                </option>
              ))}
            </select>
          </label>
          <input
            type="range"
            min={0}
            max={total}
            value={pos}
            onChange={(e) => {
              setPlaying(false);
              setCursor(Number(e.target.value));
            }}
            disabled={!!live || total === 0}
            aria-label="Replay position"
            className="min-w-[8rem] flex-1 accent-[#F4F1E9]"
          />
          <span className="font-mono text-[0.72rem] tabular-nums text-ink-soft">
            event {pos} / {total}
          </span>
          {API_URL ? (
            live ? (
              <button className="btn" onClick={stopLive}>
                Back to replay ({live.status})
              </button>
            ) : (
              <button className="btn" onClick={startLive} title="Stream this target from the live API">
                Run live
              </button>
            )
          ) : null}
        </div>
        <p className="mt-1 truncate text-[0.92rem]" aria-live="polite">
          {live?.status === "error" ? live.error : describeEvent(pos > 0 ? events[pos - 1] : null)}
        </p>
      </div>
      {total === 0 && !live ? (
        <p className="mt-4 text-[0.95rem] text-ink-soft">This run file has no recorded events, so there is nothing to replay; the final state is shown.</p>
      ) : null}

      <nav aria-label="Panes" className="no-print mt-4 flex gap-4 font-mono text-[0.75rem] xl:hidden">
        <a href="#pane-map" className="link">map</a>
        <a href="#pane-trials" className="link">trials</a>
        <a href="#pane-director" className="link">director</a>
      </nav>

      <div className="mt-5 grid gap-8 xl:grid-cols-[minmax(0,5fr)_minmax(0,6.2fr)_minmax(0,3.4fr)] xl:gap-6">
        <section id="pane-map" aria-label="Argument map and objections" className="scroll-mt-28 xl:max-h-[calc(100vh-7.5rem)] xl:overflow-y-auto xl:pr-2">
          <MapPane run={run} state={total === 0 && !live ? replayFinal(run) : state} nums={nums} />
        </section>
        <section id="pane-trials" aria-label="Trials" className="scroll-mt-28 xl:max-h-[calc(100vh-7.5rem)] xl:overflow-y-auto xl:border-l xl:border-rule xl:px-4">
          <TrialsPane run={run} state={state} nums={nums} log={log} follow={isPlaying || !!live} />
        </section>
        <section id="pane-director" aria-label="Director queue" className="scroll-mt-28 xl:max-h-[calc(100vh-7.5rem)] xl:overflow-y-auto xl:border-l xl:border-rule xl:pl-4">
          <DirectorPane state={state} nums={nums} briefTitles={briefTitles} />
        </section>
      </div>
      <Disclaimer className="mt-10" />
    </div>
  );
}

/** For a run without events, show its final objections and outcomes on the map. */
function replayFinal(run: Run) {
  const s = replay([], 0);
  s.objections = run.objections ?? [];
  for (const t of run.trials ?? []) s.outcomes[t.objection_id] = t.status === "failed" ? "failed" : t.outcome ?? "failed";
  for (const [id, text] of Object.entries(run.revised_premises ?? {})) s.revised.push({ id, text, from_trial: "" });
  for (const [id, n] of Object.entries(run.novelty ?? {}))
    s.novelty[id] = {
      novelty: assessedNovelty(n),
      status: n.status,
      reason: n.reason,
      records_searched: n.records_searched,
      nearest: n.nearest,
    };
  return s;
}
