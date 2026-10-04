import type { ReactNode } from "react";
import { Link } from "react-router";
import type { Load } from "../lib/data";
import { OUTCOME_COLORS, OUTCOME_LABELS, OUTCOME_TEXT_COLORS, type Outcome } from "../types";

export function isOutcome(o: unknown): o is Outcome {
  return typeof o === "string" && o in OUTCOME_COLORS;
}

export function outcomeColor(o: string | null | undefined): string {
  return isOutcome(o) ? OUTCOME_COLORS[o] : "#F4F1E9";
}

export function OutcomeChip({ outcome, size = "sm" }: { outcome: string | null | undefined; size?: "sm" | "lg" }) {
  const big = size === "lg";
  if (isOutcome(outcome)) {
    const c = OUTCOME_COLORS[outcome];
    return (
      <span
        className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-[2px] border font-mono ${big ? "px-2.5 py-1 text-[0.8rem]" : "px-1.5 py-[1px] text-[0.7rem]"}`}
        style={{ borderColor: c, color: OUTCOME_TEXT_COLORS[outcome], backgroundColor: `${c}12` }}
      >
        <span aria-hidden className={`inline-block rounded-full ${big ? "h-2 w-2" : "h-1.5 w-1.5"}`} style={{ backgroundColor: c }} />
        {OUTCOME_LABELS[outcome]}
      </span>
    );
  }
  const failed = outcome === "failed";
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-[2px] border border-dashed font-mono text-ink-soft ${big ? "px-2.5 py-1 text-[0.8rem]" : "px-1.5 py-[1px] text-[0.7rem]"}`}
      style={{ borderColor: failed ? "#F4F1E9" : "#4A525B" }}
    >
      {failed ? "Failed" : "No outcome"}
    </span>
  );
}

/** Every agent turn carries one of these: family · model. */
export function ModelBadge({ family, model, className = "" }: { family?: string | null; model?: string | null; className?: string }) {
  if (!family && !model) return null;
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded-[2px] border border-rule bg-[#1B1F23] px-1.5 py-[1px] font-mono text-[0.68rem] text-ink-soft ${className}`}
      title="model family · model"
    >
      {family ?? "?"}
      <span className="px-1 text-ink-faint">·</span>
      {model ?? "?"}
    </span>
  );
}

export function Label({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <div className={`smallcaps text-[0.95rem] text-ink-soft ${className}`}>{children}</div>;
}

/** A section with a marginal label on wide screens. */
export function Marginal({ label, children, id, className = "" }: { label: ReactNode; children: ReactNode; id?: string; className?: string }) {
  return (
    <section id={id} className={`grid gap-2 border-t border-rule pt-5 md:grid-cols-[10rem_minmax(0,1fr)] md:gap-8 ${className}`}>
      <Label className="md:pt-1">{label}</Label>
      <div className="min-w-0">{children}</div>
    </section>
  );
}

export function Disclaimer({ text, className = "" }: { text?: string | null; className?: string }) {
  return (
    <p className={`border-l-[3px] border-ink bg-paper-deep px-4 py-2.5 font-serif text-[1.05rem] font-medium italic ${className}`} role="note">
      {text || "Further human review required."}
    </p>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="border border-dashed border-rule px-4 py-5 text-[0.95rem] text-ink-soft">{children}</div>;
}

export function Code({ children }: { children: ReactNode }) {
  return <code className="rounded-[2px] bg-paper-deep px-1 py-[1px] font-mono text-[0.82em]">{children}</code>;
}

export function DataState<T>({ load, what, children }: { load: Load<T>; what: string; children: (data: T) => ReactNode }) {
  if (load.status === "ready") return <>{children(load.data)}</>;
  if (load.status === "loading")
    return (
      <p className="py-6 font-mono text-sm text-ink-soft" aria-live="polite">
        Loading {what}…
      </p>
    );
  if (load.status === "missing")
    return (
      <Empty>
        No data yet: <Code>web/public/data/{load.path}</Code> has not been exported. The lab writes it with{" "}
        <Code>make export</Code> once runs finish.
      </Empty>
    );
  return <Empty>Could not read {what}: {load.error}</Empty>;
}

export function Stat({ value, label, source }: { value: ReactNode; label: ReactNode; source?: ReactNode }) {
  return (
    <div className="border-t border-ink pt-3">
      <div className="font-serif text-[2.6rem] leading-none tracking-tight">{value}</div>
      <div className="mt-2 text-[0.98rem] leading-snug">{label}</div>
      {source ? <div className="mt-1 font-mono text-[0.68rem] text-ink-faint">source: {source}</div> : null}
    </div>
  );
}

export function TextLink({ to, children, className = "" }: { to: string; children: ReactNode; className?: string }) {
  return (
    <Link to={to} className={`link ${className}`}>
      {children}
    </Link>
  );
}

/** Renders an arbitrary JSON value as a compact key/value list (settings, roles, stats). */
export function KV({ value, depth = 0 }: { value: unknown; depth?: number }) {
  if (value === null || value === undefined) return <span className="text-ink-faint">—</span>;
  if (typeof value !== "object") return <span className="font-mono text-[0.8rem]">{String(value)}</span>;
  if (Array.isArray(value)) {
    if (!value.length) return <span className="text-ink-faint">none</span>;
    if (value.every((v) => typeof v !== "object" || v === null))
      return <span className="font-mono text-[0.8rem]">{value.map(String).join(", ")}</span>;
    return (
      <ol className="list-decimal space-y-1 pl-5">
        {value.map((v, i) => (
          <li key={i}>
            <KV value={v} depth={depth + 1} />
          </li>
        ))}
      </ol>
    );
  }
  const entries = Object.entries(value as Record<string, unknown>);
  if (!entries.length) return <span className="text-ink-faint">none</span>;
  return (
    <dl className={`grid grid-cols-[minmax(7rem,max-content)_minmax(0,1fr)] gap-x-4 gap-y-1 ${depth ? "text-[0.9rem]" : ""}`}>
      {entries.map(([k, v]) => (
        <div key={k} className="contents">
          <dt className="font-mono text-[0.75rem] text-ink-soft">{k}</dt>
          <dd className="min-w-0 break-words">
            <KV value={v} depth={depth + 1} />
          </dd>
        </div>
      ))}
    </dl>
  );
}
