import { OUTCOME_COLORS, OUTCOME_LABELS, type Outcome } from "../types";

const ORDER: (Outcome | "failed")[] = ["standing", "revision_required", "rebutted", "known_answer", "misreading", "failed"];

export function OutcomeBar({ outcomes, showCounts = true }: { outcomes: Partial<Record<Outcome | "failed", number>>; showCounts?: boolean }) {
  const parts = ORDER.map((k) => ({ k, n: outcomes[k] ?? 0 })).filter((p) => p.n > 0);
  const total = parts.reduce((s, p) => s + p.n, 0);
  if (!total) return <span className="font-mono text-[0.75rem] text-ink-faint">no trials yet</span>;
  const label = parts.map((p) => `${p.n} ${p.k === "failed" ? "failed" : OUTCOME_LABELS[p.k as Outcome].toLowerCase()}`).join(", ");
  return (
    <div className="space-y-1.5">
      <div className="flex h-2 w-full max-w-[16rem] overflow-hidden rounded-[1px] bg-paper-edge" role="img" aria-label={`Trial outcomes: ${label}`}>
        {parts.map((p) => (
          <div
            key={p.k}
            style={{
              width: `${(p.n / total) * 100}%`,
              backgroundColor: p.k === "failed" ? "transparent" : OUTCOME_COLORS[p.k as Outcome],
              backgroundImage: p.k === "failed" ? "repeating-linear-gradient(45deg,#F4F1E9 0 1px,transparent 1px 4px)" : undefined,
            }}
          />
        ))}
      </div>
      {showCounts ? (
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 font-mono text-[0.7rem] text-ink-soft">
          {parts.map((p) => (
            <span key={p.k} className="inline-flex items-center gap-1">
              <span
                aria-hidden
                className="inline-block h-1.5 w-1.5 rounded-full"
                style={{ backgroundColor: p.k === "failed" ? "#F4F1E9" : OUTCOME_COLORS[p.k as Outcome] }}
              />
              {p.n} {p.k === "failed" ? "failed" : OUTCOME_LABELS[p.k as Outcome].toLowerCase()}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function OutcomeLegend() {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-[0.72rem] text-ink-soft">
      {(Object.keys(OUTCOME_COLORS) as Outcome[]).map((o) => (
        <li key={o} className="inline-flex items-center gap-1.5">
          <span aria-hidden className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: OUTCOME_COLORS[o] }} />
          {OUTCOME_LABELS[o]}
        </li>
      ))}
    </ul>
  );
}
