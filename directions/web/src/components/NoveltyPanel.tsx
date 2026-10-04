import { assessedNovelty, NOT_ASSESSED, notAssessedReason } from "../lib/assessment";
import type { CSSProperties } from "react";
import type { NearestMatch, Novelty } from "../types";
import { num } from "../lib/format";
import { useDrawer } from "./drawer";
import { Disclaimer, Label } from "./ui";

// Prior-art verdicts are not trial outcomes, so they are set in ink rather than outcome colours.
const VERDICT_STYLE: Record<string, { label: string; style: CSSProperties }> = {
  same_move: { label: "same move", style: { background: "#F4F1E9", color: "#121416", borderColor: "#F4F1E9" } },
  related: { label: "related", style: { borderColor: "#F4F1E9", color: "#F4F1E9" } },
  different: { label: "different", style: { borderColor: "#4A525B", color: "#808A94" } },
  cited_in_trial: { label: "cited in trial", style: { borderColor: "#B4BBC2", color: "#B4BBC2", borderStyle: "dotted" } },
};

export function VerdictTag({ verdict }: { verdict?: string }) {
  if (!verdict) return null;
  const v = VERDICT_STYLE[verdict] ?? { label: verdict.replace(/_/g, " "), style: { borderColor: "#B4BBC2", color: "#B4BBC2" } };
  return (
    <span className="whitespace-nowrap rounded-[2px] border px-1.5 font-mono text-[0.66rem]" style={v.style}>
      {v.label}
    </span>
  );
}

/** A 0–1 bar, for novelty scores. A missing value is said in words, never drawn as a bar. */
export function Meter({ value, label }: { value: number | null | undefined; label: string }) {
  const v = value === null || value === undefined || Number.isNaN(value) ? null : Math.max(0, Math.min(1, value));
  if (v === null)
    return (
      <span className="font-mono text-[0.72rem] text-ink-soft" aria-label={`${label}: ${NOT_ASSESSED.toLowerCase()}`}>
        {NOT_ASSESSED.toLowerCase()}
      </span>
    );
  return (
    <div className="flex items-center gap-2" role="img" aria-label={`${label}: ${v === null ? "not available" : num(v)}`}>
      <div className="h-1.5 w-20 overflow-hidden rounded-full bg-paper-edge">
        {v !== null ? <div className="h-full bg-ink" style={{ width: `${v * 100}%` }} /> : null}
      </div>
      <span className="font-mono text-[0.75rem]">{num(v)}</span>
    </div>
  );
}

export function NearestList({ nearest }: { nearest: NearestMatch[] }) {
  const { openRecord } = useDrawer();
  if (!nearest.length) return <p className="text-[0.92rem] text-ink-soft">No nearest matches were recorded.</p>;
  return (
    <ol className="space-y-3">
      {nearest.map((m, i) => (
        <li key={`${m.record_id}-${i}`} className="print-break-avoid border-t border-rule pt-2.5">
          <div className="flex flex-wrap items-center gap-2">
            <VerdictTag verdict={m.verdict} />
            <span className="font-mono text-[0.7rem] text-ink-faint">similarity {num(m.similarity)}</span>
            <button
              type="button"
              className="link text-left text-[0.98rem] font-medium"
              onClick={() => openRecord(m.paper_id, { quote: m.quote, title: m.title, recordId: m.record_id })}
            >
              {m.title || m.paper_id}
            </button>
          </div>
          {m.quote ? <blockquote className="mt-1 border-l border-rule pl-3 text-[0.95rem] italic leading-relaxed text-ink-soft">“{m.quote}”</blockquote> : null}
          <div className="mt-0.5 font-mono text-[0.68rem] text-ink-faint">{m.record_id}</div>
        </li>
      ))}
    </ol>
  );
}

export function NoveltyPanel({
  data,
  showDisclaimer = true,
}: {
  data: Pick<Novelty, "novelty" | "records_searched" | "nearest"> & Partial<Novelty>;
  showDisclaimer?: boolean;
}) {
  const restatements = Object.entries(data.restatements ?? {}).filter(([, v]) => v);
  const score = assessedNovelty(data);
  return (
    <div className="space-y-4">
      {score === null ? (
        <p className="border-l-2 border-ink pl-3 text-[0.95rem]" role="status">
          <span className="font-medium">{NOT_ASSESSED}.</span> {notAssessedReason(data)}
        </p>
      ) : null}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <div>
          <Label>novelty score</Label>
          <div className="font-serif text-[1.9rem] leading-tight">{score === null ? NOT_ASSESSED : num(score)}</div>
        </div>
        <div>
          <Label>records searched</Label>
          <div className="font-serif text-[1.9rem] leading-tight">{data.records_searched ?? "—"}</div>
        </div>
        {data.reranked !== undefined ? (
          <div>
            <Label>reranked</Label>
            <div className="font-serif text-[1.9rem] leading-tight">{data.reranked}</div>
          </div>
        ) : null}
        {data.live_openalex ? (
          <div className="min-w-0">
            <Label>live OpenAlex search</Label>
            <div className="break-words font-mono text-[0.78rem] leading-snug">{data.live_openalex}</div>
          </div>
        ) : null}
      </div>
      <p className="text-[0.88rem] text-ink-soft">
        Novelty is 1 minus the highest similarity among passages the reranker judged to make the same or a related move.
        It measures distance from what this lab could find, not originality in the literature at large.
      </p>
      {restatements.length ? (
        <details>
          <summary className="cursor-pointer text-[0.92rem] text-ink-soft">The three restatements searched</summary>
          <dl className="mt-2 space-y-2">
            {restatements.map(([k, v]) => (
              <div key={k}>
                <dt className="smallcaps text-[0.85rem] text-ink-soft">{k.replace(/_/g, " ")}</dt>
                <dd className="text-[0.95rem]">{v}</dd>
              </div>
            ))}
          </dl>
        </details>
      ) : null}
      <div>
        <Label className="mb-1">Nearest matches</Label>
        <NearestList nearest={data.nearest ?? []} />
      </div>
      {showDisclaimer ? <Disclaimer /> : null}
    </div>
  );
}
