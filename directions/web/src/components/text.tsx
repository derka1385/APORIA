import { Fragment, type ReactNode } from "react";
import type { Claim } from "../types";
import { useDrawer } from "./drawer";

// Corpus claim ids ("W123.c004", "W123.a1") and the lab's own premise ids ("W123.arg1.mp", "W123.arg1.r2").
const CITE = /\[([A-Za-z0-9_-]+(?:\.arg\d+)?\.(?:c\d{1,3}|a\d{1,3}|r\d{1,2}|mp))\]/g;

/** A clickable corpus id that opens the record drawer. Struck ids are shown struck through and not clickable. */
export function ClaimRef({ id, struck = false, local, label }: { id: string; struck?: boolean; local?: Record<string, Claim>; label?: string }) {
  const { openClaim } = useDrawer();
  if (struck)
    return (
      <s
        className="font-mono text-[0.92em] text-ink-faint decoration-ink decoration-[1.5px]"
        title="Unverifiable citation: struck by the Referee"
      >
        {id}
        <span className="sr-only"> (struck: unverifiable citation)</span>
      </s>
    );
  return (
    <button
      type="button"
      onClick={() => openClaim(id, local?.[id])}
      className="h-fit cursor-pointer self-start rounded-[2px] bg-paper-deep px-1 font-mono text-[0.92em] text-ink underline decoration-ink/40 decoration-dotted underline-offset-2 hover:decoration-ink hover:decoration-solid"
      title={`Open the corpus record for ${id}`}
      aria-label={label ? `${label} (${id}): open the corpus record` : undefined}
    >
      {label ?? id}
    </button>
  );
}

/** Agent text with inline [claim.id] citations made clickable (or struck), split into paragraphs. */
export function CitedText({
  text,
  struck = [],
  local,
  className = "",
}: {
  text: string;
  struck?: string[];
  local?: Record<string, Claim>;
  className?: string;
}) {
  const struckSet = new Set(struck);
  const paras = text.split(/\n{2,}/);
  return (
    <div className={`space-y-2 ${className}`}>
      {paras.map((p, i) => (
        <p key={i} className="whitespace-pre-line">
          {renderInline(p, struckSet, local)}
        </p>
      ))}
    </div>
  );
}

function renderInline(p: string, struck: Set<string>, local?: Record<string, Claim>): ReactNode[] {
  const out: ReactNode[] = [];
  let last = 0;
  for (const m of p.matchAll(CITE)) {
    const idx = m.index ?? 0;
    if (idx > last) out.push(<Fragment key={`t${idx}`}>{p.slice(last, idx)}</Fragment>);
    out.push(
      <Fragment key={`c${idx}`}>
        [<ClaimRef id={m[1]} struck={struck.has(m[1])} local={local} />]
      </Fragment>,
    );
    last = idx + m[0].length;
  }
  if (last < p.length) out.push(<Fragment key="end">{p.slice(last)}</Fragment>);
  return out;
}

export function CitationList({ cited, struck, local }: { cited: string[]; struck: string[]; local?: Record<string, Claim> }) {
  if (!cited.length && !struck.length) return null;
  return (
    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-[0.78rem]">
      <span className="smallcaps text-ink-soft">cites</span>
      {cited.map((id) => (
        <ClaimRef key={id} id={id} local={local} />
      ))}
      {struck.map((id) => (
        <ClaimRef key={`s-${id}`} id={id} struck />
      ))}
    </div>
  );
}
