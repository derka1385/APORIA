import { trialFailure } from "../lib/assessment";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router";
import { NoveltyPanel } from "../components/NoveltyPanel";
import { TurnView } from "../components/TurnView";
import { CitedText } from "../components/text";
import { Code, DataState, Disclaimer, Empty, Label, Marginal, ModelBadge, OutcomeChip } from "../components/ui";
import { fetchJSON, useJSON } from "../lib/data";
import { agentLabel, displayTitle, shortId, speakerLabel } from "../lib/format";
import { paperShort, trialPaperShort } from "../lib/ids";
import type { Index, PerDefender, Run, Trial } from "../types";

type Found = { run: Run; trial: Trial } | { missing: true } | null;

function useTrial(id: string, index: Index | null): Found {
  const [found, setFound] = useState<{ id: string; value: Found }>({ id: "", value: null });
  useEffect(() => {
    if (!index) return;
    let alive = true;
    const guess = trialPaperShort(id);
    const runs = [...(index.runs ?? [])].sort(
      (a, b) => Number(paperShort(b.paper_id) === guess) - Number(paperShort(a.paper_id) === guess),
    );
    (async () => {
      for (const r of runs) {
        try {
          const run = await fetchJSON<Run>(`runs/${r.run_id}.json`);
          const trial = (run.trials ?? []).find((t) => t.id === id);
          if (trial) {
            if (alive) setFound({ id, value: { run, trial } });
            return;
          }
        } catch {
          /* a missing run file is skipped */
        }
      }
      if (alive) setFound({ id, value: { missing: true } });
    })();
    return () => {
      alive = false;
    };
  }, [id, index]);
  return found.id === id ? found.value : null;
}

export default function TrialPage() {
  const { id = "" } = useParams();
  const index = useJSON<Index>("index.json");
  const found = useTrial(id, index.status === "ready" ? index.data : null);
  return (
    <div className="mx-auto max-w-[1100px] px-4 py-8 sm:px-6">
      <DataState load={index} what="the index">
        {() =>
          found === null ? (
            <p className="font-mono text-sm text-ink-soft" aria-live="polite">
              Finding trial {id}…
            </p>
          ) : "missing" in found ? (
            <Empty>
              No exported run contains a trial with id <Code>{id}</Code>.
            </Empty>
          ) : (
            <TrialView run={found.run} trial={found.trial} />
          )
        }
      </DataState>
    </div>
  );
}

function TrialView({ run, trial }: { run: Run; trial: Trial }) {
  const o = (run.objections ?? []).find((x) => x.id === trial.objection_id);
  const target = o?.target_premise_id ?? "";
  const targetText = run.claims?.[target]?.text ?? run.revised_premises?.[target] ?? "";
  const nov = run.novelty?.[trial.objection_id];
  const rounds = trial.rounds ?? [];
  const pre = rounds.filter((t) => t.exchange === 0);
  const exA = rounds.filter((t) => t.exchange === 1);
  const exB = rounds.filter((t) => t.exchange === 2);
  const briefId = (run.briefs ?? []).find((b) => b === `brief-${trial.objection_id}`);
  const failed = trial.status === "failed";

  return (
    <article className="space-y-8">
      <header className="space-y-3">
        <Label>
          <Link to={`/runs/${encodeURIComponent(run.run_id)}`} className="hover:underline">
            {displayTitle(run.target.title)}
          </Link>{" "}
          / trial
        </Label>
        <h1 className="font-serif text-[2.1rem] font-medium leading-tight">
          {o ? `${agentLabel(o.agent)} against ${shortId(target)}` : `Trial ${shortId(trial.id)}`}
        </h1>
        <div className="flex flex-wrap items-center gap-3">
          <OutcomeChip outcome={failed ? "failed" : trial.outcome} size="lg" />
          <span className="font-mono text-[0.72rem] text-ink-soft">{trial.id}</span>
        </div>
        {failed ? (
          <p className="border border-dashed border-ink px-3 py-2 font-mono text-[0.85rem]" role="status">
            {trialFailure(trial)} It has no combined outcome and does not count as a result; the discussion it did
            produce is below{trial.error && trial.missing_labels?.length ? ` (${trial.error})` : ""}.
          </p>
        ) : null}
        {!failed && trial.rationale ? (
          <p className="measure text-[1.12rem] leading-relaxed">
            <span className="smallcaps mr-1 text-ink-soft">in plain words</span>
            {trial.rationale}
          </p>
        ) : null}
        {!failed && trial.deciding_quote ? (
          <blockquote className="measure border-l-2 border-ink pl-4 italic">
            <span className="smallcaps not-italic mr-1 text-ink-soft">deciding sentence</span>“{trial.deciding_quote}”
          </blockquote>
        ) : null}
        {trial.revised_premise ? (
          <p className="measure border border-dashed border-revision_required px-3 py-2">
            <span className="smallcaps mr-1 text-revision_required-text">revised premise</span>
            {trial.revised_premise}
          </p>
        ) : null}
        <div className="flex flex-wrap gap-3 pt-1">
          {briefId ? (
            <Link to={`/brief/${encodeURIComponent(briefId)}`} className="btn">
              Read the research brief →
            </Link>
          ) : null}
          <Link to={`/runs/${encodeURIComponent(run.run_id)}?at=end`} className="btn btn-quiet">
            Back to the run
          </Link>
        </div>
      </header>

      <Marginal label="the objection">
        {o ? (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-medium">{agentLabel(o.agent)}</span>
              <ModelBadge family={o.family} model={o.model} />
              <span className="font-mono text-[0.72rem] text-ink-soft">
                {o.kind}
                {o.tradition ? ` · ${o.tradition}` : ""}
                {o.depth ? ` · depth ${o.depth}` : ""}
              </span>
            </div>
            <p className="measure text-[0.95rem]">
              <span className="smallcaps mr-1 text-ink-soft">target premise</span>
              <span className="font-mono text-[0.8rem]">{shortId(target)}</span> — {targetText || "(text not exported)"}
            </p>
            <div className="measure border-l-2 border-ink pl-3">
              <CitedText text={o.text} className="turn-body" local={run.claims} />
            </div>
            {o.premise_fails_because ? (
              <p className="measure text-[0.95rem]">
                <span className="smallcaps mr-1 text-ink-soft">why the premise fails</span>
                {o.premise_fails_because}
              </p>
            ) : null}
          </div>
        ) : (
          <Empty>The objection record for {trial.objection_id} is not in this run file.</Empty>
        )}
      </Marginal>

      <Marginal label="prior-art check">
        {nov ? <NoveltyPanel data={nov} /> : <Empty>No prior-art check was recorded for this objection.</Empty>}
      </Marginal>

      <Marginal label="pre-screen">
        {pre.length ? (
          <div className="space-y-3">
            {pre.map((t, i) => (
              <TurnView key={i} turn={t} local={run.claims} />
            ))}
          </div>
        ) : (
          <p className="text-ink-soft">No pre-screen turn recorded.</p>
        )}
      </Marginal>

      <Exchange label="Defender A" speaker="defender_a" turns={exA} verdict={trial.per_defender?.defender_a} run={run} />
      <Exchange label="Defender B" speaker="defender_b" turns={exB} verdict={trial.per_defender?.defender_b} run={run} />

      <Marginal label="cited and verified">
        {trial.cited_claim_ids?.length ? (
          <p className="font-mono text-[0.8rem]">{trial.cited_claim_ids.join(" · ")}</p>
        ) : (
          <p className="text-[0.95rem] text-ink-soft">No literature citation survived verification in this trial.</p>
        )}
      </Marginal>

      <Disclaimer />
    </article>
  );
}

function Exchange({
  label,
  speaker,
  turns,
  verdict,
  run,
}: {
  label: string;
  speaker: string;
  turns: Run["trials"][number]["rounds"];
  verdict?: PerDefender;
  run: Run;
}) {
  const body = turns.filter((t) => t.phase !== "label");
  const labels = turns.filter((t) => t.phase === "label");
  return (
    <Marginal label={`${label} exchange`}>
      {body.length ? (
        <div className="space-y-4">
          {body.map((t, i) => (
            <TurnView key={i} turn={t} local={run.claims} />
          ))}
        </div>
      ) : (
        <p className="text-ink-soft">No {speakerLabel(speaker)} exchange recorded (the trial may have stopped at the pre-screen).</p>
      )}
      {verdict ? (
        <div className="mt-5 border border-rule bg-[#1B1F23] px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="smallcaps text-ink-soft">referee on {label}</span>
            <OutcomeChip outcome={verdict.outcome} />
            <ModelBadge family={verdict.family} model={verdict.model} />
          </div>
          {verdict.rationale ? <p className="mt-2">{verdict.rationale}</p> : null}
          {verdict.deciding_quote ? (
            <blockquote className="mt-2 border-l-2 border-ink pl-3 text-[0.95rem] italic">“{verdict.deciding_quote}”</blockquote>
          ) : null}
          {verdict.revised_premise ? (
            <p className="mt-2 text-[0.95rem]">
              <span className="smallcaps mr-1 text-revision_required-text">revised premise</span>
              {verdict.revised_premise}
            </p>
          ) : null}
          {verdict.verified?.length || verdict.struck?.length ? (
            <p className="mt-2 font-mono text-[0.72rem] text-ink-soft">
              verified: {verdict.verified?.join(", ") || "none"} · struck:{" "}
              {verdict.struck?.length ? <s>{verdict.struck.join(", ")}</s> : "none"}
            </p>
          ) : null}
        </div>
      ) : labels.length ? (
        <div className="mt-4 space-y-3">
          {labels.map((t, i) => (
            <TurnView key={i} turn={t} local={run.claims} />
          ))}
        </div>
      ) : body.length ? (
        <p className="mt-4 text-[0.95rem] text-ink-soft">The Referee produced no valid label for this exchange.</p>
      ) : null}
    </Marginal>
  );
}
