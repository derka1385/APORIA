import { useMemo, useState } from "react";
import { useSearchParams } from "react-router";
import { DirectionItem } from "../components/DirectionItem";
import { OutcomeGuide } from "../components/Guide";
import { Code, DataState, Disclaimer, Empty, Label } from "../components/ui";
import { useJSON } from "../lib/data";
import { displayTitle } from "../lib/format";
import { OUTCOME_LABELS, type BriefSummary, type Outcome } from "../types";

export default function Briefs() {
  const briefs = useJSON<BriefSummary[]>("briefs.json");
  return (
    <div className="mx-auto max-w-[1200px] px-4 py-10 sm:px-6">
      <Label>where to write next</Label>
      <h1 className="font-serif text-[2.6rem] font-medium leading-tight">Research directions</h1>
      <p className="measure mt-2 text-[1.05rem] text-ink-soft">
        Each direction is an objection the lab generated without seeing the literature, then put through two defenders
        and a referee, then checked against the corpus, then graded by an Assessor. Best first, by lead score: survival ×
        novelty × quality (the Assessor’s latest score out of 5), so the top of the list is new, has survived, and is
        sound. Open one for the printable brief.
      </p>
      <OutcomeGuide />
      <div className="mt-8">
        <DataState load={briefs} what="research briefs">
          {(list) => <BriefList list={list} />}
        </DataState>
      </div>
    </div>
  );
}

function BriefList({ list }: { list: BriefSummary[] }) {
  const [filter, setFilter] = useState<Outcome | "all">("all");
  // The paper filter lives in the URL (?paper=<run id>) so one paper's directions can be shared as a link.
  const [params, setParams] = useSearchParams();
  const paper = params.get("paper");
  const papers = useMemo(() => {
    const m = new Map<string, string>();
    for (const b of list) if (b.run_id && !m.has(b.run_id)) m.set(b.run_id, displayTitle(b.paper_title || b.run_id));
    return [...m.entries()];
  }, [list]);
  const pickPaper = (runId: string | null) => {
    const next = new URLSearchParams(params);
    if (runId) next.set("paper", runId);
    else next.delete("paper");
    setParams(next, { replace: true });
  };
  const byPaper = paper ? list.filter((b) => b.run_id === paper) : list;
  const present = useMemo(() => [...new Set(list.map((b) => b.outcome).filter(Boolean))] as Outcome[], [list]);
  const shown = filter === "all" ? byPaper : byPaper.filter((b) => b.outcome === filter);
  if (!list.length)
    return (
      <Empty>
        No research briefs yet. Run <Code>make runs</Code> then <Code>make export</Code>.
      </Empty>
    );
  return (
    <>
      {papers.length > 1 ? (
        <div className="mb-3 flex flex-wrap items-center gap-2" role="group" aria-label="Filter by paper">
          <span className="smallcaps mr-1 text-[0.95rem] text-ink-soft">paper</span>
          <button className="btn btn-quiet" aria-pressed={!paper} onClick={() => pickPaper(null)}>
            all papers
          </button>
          {papers.map(([id, title]) => (
            <button key={id} className="btn btn-quiet" aria-pressed={paper === id} title={title} onClick={() => pickPaper(id)}>
              {title.length > 40 ? `${title.slice(0, 38).trimEnd()}…` : title}
            </button>
          ))}
        </div>
      ) : null}
      {present.length > 1 ? (
        <div className="mb-4 flex flex-wrap items-center gap-2" role="group" aria-label="Filter by outcome">
          <span className="smallcaps mr-1 text-[0.95rem] text-ink-soft">outcome</span>
          <button className="btn btn-quiet" aria-pressed={filter === "all"} onClick={() => setFilter("all")}>
            all ({byPaper.length})
          </button>
          {present.map((o) => (
            <button key={o} className="btn btn-quiet" aria-pressed={filter === o} onClick={() => setFilter(o)}>
              {OUTCOME_LABELS[o].toLowerCase()} ({byPaper.filter((b) => b.outcome === o).length})
            </button>
          ))}
        </div>
      ) : null}
      {!shown.length ? <Empty>No research directions match this filter.</Empty> : null}
      <ol>
        {shown.map((b) => (
          <DirectionItem key={b.id} brief={b} rank={list.indexOf(b) + 1} />
        ))}
      </ol>
      <Disclaimer className="mt-6" />
    </>
  );
}
