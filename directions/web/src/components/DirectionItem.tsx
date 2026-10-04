import { fmtScore, GradeChip } from "./Quality";
import { Link } from "react-router";
import type { BriefSummary } from "../types";
import { displayTitle, excerpt, num, shortId } from "../lib/format";
import { Meter } from "./NoveltyPanel";
import { OutcomeChip } from "./ui";

/** One research direction: the brief's question and paper direction first, the evidence trail after. */
export function DirectionItem({ brief, rank, long = false }: { brief: BriefSummary; rank: number; long?: boolean }) {
  return (
    <li className="grid gap-x-6 gap-y-2 border-t border-rule py-6 md:grid-cols-[3rem_minmax(0,1fr)_14rem]">
      <div className="font-serif text-[1.6rem] leading-none text-ink-faint" aria-hidden>
        {rank}
      </div>
      <div className="min-w-0 space-y-2.5">
        {brief.tier === 0 ? (
          <div className="smallcaps text-[0.88rem] text-ink-soft">top direction for this paper</div>
        ) : null}
        <h3 className="font-serif text-[1.38rem] font-medium leading-snug">
          <Link to={`/brief/${encodeURIComponent(brief.id)}`} className="link decoration-transparent hover:decoration-ink">
            {brief.research_question}
          </Link>
        </h3>
        {brief.paper_direction ? (
          <p className="measure text-[1.02rem] leading-relaxed text-ink">{long ? brief.paper_direction : excerpt(brief.paper_direction, 340)}</p>
        ) : null}
        {brief.revision?.research_question ? (
          <p className="measure mt-2 text-[0.95rem]">
            <span className="smallcaps mr-1 text-ink-soft">revised</span>
            {brief.revision.research_question}
          </p>
        ) : null}
        {(brief.revision?.assessment?.summary ?? brief.assessment?.summary) ? (
          <p className="measure mt-2 border-l-2 border-ink pl-3 text-[0.92rem] italic text-ink-soft">
            Assessor{brief.revision?.assessment ? " (after revision)" : ""}:{" "}
            {brief.revision?.assessment?.summary ?? brief.assessment?.summary}
          </p>
        ) : null}
        <p className="measure text-[0.92rem] text-ink-soft">
          Challenges <span className="font-mono text-[0.8rem]">{shortId(brief.challenged_premise?.id ?? "")}</span>
          {brief.challenged_premise?.text ? <> — “{excerpt(brief.challenged_premise.text, 200)}”</> : null}
          {brief.paper_title ? (
            <>
              {" "}
              in <cite className="not-italic">{displayTitle(brief.paper_title)}</cite>
            </>
          ) : null}
        </p>
        <Link to={`/brief/${encodeURIComponent(brief.id)}`} className="link inline-block text-[0.95rem]">
          Read the brief →
        </Link>
      </div>
      <dl className="grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-1.5 self-start text-[0.85rem] md:border-l md:border-rule md:pl-4">
        <dt className="smallcaps text-ink-soft">outcome</dt>
        <dd>
          <OutcomeChip outcome={brief.outcome} />
        </dd>
        {brief.assessment ? (
          <>
            <dt className="smallcaps text-ink-soft">quality</dt>
            <dd className="flex flex-wrap items-center gap-1">
              {brief.revision?.assessment ? (
                <>
                  <GradeChip grade={brief.revision.assessment.grade} overall={brief.revision.assessment.overall} />
                  <span className="font-mono text-[0.66rem] text-ink-soft" title="compared with the grade before the revision round">
                    {revisionNote(brief.assessment, brief.revision.assessment)}
                  </span>
                </>
              ) : (
                <GradeChip grade={brief.assessment.grade} overall={brief.assessment.overall} />
              )}
            </dd>
          </>
        ) : null}
        <dt className="smallcaps text-ink-soft">novelty</dt>
        <dd>
          <Meter value={brief.novelty} label="novelty score" />
        </dd>
        <dt className="smallcaps text-ink-soft">searched</dt>
        <dd className="font-mono text-[0.75rem]">{brief.records_searched} records</dd>
        <dt className="smallcaps text-ink-soft">survival</dt>
        <dd className="font-mono text-[0.75rem]">{num(brief.survival)}</dd>
        {brief.score !== undefined ? (
          <>
            <dt className="smallcaps text-ink-soft">lead score</dt>
            <dd className="font-mono text-[0.75rem]" title={leadFormula(brief)}>
              {num(brief.score, 3)}
            </dd>
          </>
        ) : null}
      </dl>
    </li>
  );
}

/** The lead score spelled out: survival × novelty × quality (the Assessor's latest score out of 5). */
export function leadFormula(b: BriefSummary): string {
  const q = b.quality != null ? `quality ${fmtScore(b.quality * 5)}/5` : "quality not graded (counted as 3/5)";
  return `survival ${num(b.survival)} × novelty ${num(b.novelty)} × ${q}`;
}

/** After the revision round: name the old grade only if it changed; otherwise the old score, or "unchanged". */
function revisionNote(before: { grade: string; overall: number }, after: { grade: string; overall: number }): string {
  if (before.grade !== after.grade) return `after revision · was ${before.grade}`;
  if (before.overall !== after.overall) return `after revision · was ${fmtScore(before.overall)}/5`;
  return "after revision · unchanged";
}

/** The single best direction, given the most room: the lead score's three parts are shown, not just the total. */
export function LeadCard({ brief }: { brief: BriefSummary }) {
  const latest = brief.revision?.assessment ?? brief.assessment;
  const question = brief.revision?.research_question || brief.research_question;
  const direction = (brief.revision?.research_question && brief.revision.paper_direction) || brief.paper_direction;
  return (
    <article aria-labelledby="lead-h" className="mt-6 border border-ink bg-paper-deep/40 p-5 sm:p-7">
      <div className="flex flex-wrap items-center gap-2">
        <span className="smallcaps text-[0.95rem] text-ink">strongest lead</span>
        <OutcomeChip outcome={brief.outcome} />
        {latest ? <GradeChip grade={latest.grade} overall={latest.overall} /> : null}
      </div>
      <h3 id="lead-h" className="mt-2 font-serif text-[1.3rem] font-medium leading-snug sm:text-[1.75rem]">
        <Link to={`/brief/${encodeURIComponent(brief.id)}`} className="link decoration-transparent hover:decoration-ink">
          {question}
        </Link>
      </h3>
      {question !== brief.research_question ? (
        <p className="mt-1 text-[0.88rem] text-ink-soft">
          Revised after the Assessor’s first read; the original question and direction are on the brief.
        </p>
      ) : null}
      {direction ? <p className="measure mt-3 text-[1.05rem] leading-relaxed">{direction}</p> : null}
      {latest?.summary ? (
        <p className="measure mt-3 border-l-2 border-ink pl-3 text-[0.95rem] italic text-ink-soft">Assessor: {latest.summary}</p>
      ) : null}
      <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 border-t border-rule pt-3 sm:grid-cols-4">
        <LeadPart label="survival" value={num(brief.survival)} note="against both defenders" />
        <LeadPart
          label="novelty"
          value={num(brief.novelty)}
          note={
            brief.novelty >= 0.999
              ? "no passage the reranker read was judged similar (see About on calibration)"
              : `${brief.records_searched} records searched`
          }
        />
        <LeadPart
          label="quality"
          value={brief.quality != null ? `${fmtScore(brief.quality * 5)}/5` : "—"}
          note="Assessor, latest read"
        />
        <LeadPart label="lead score" value={num(brief.score, 3)} note="the product; highest here" />
      </dl>
      <p className="mt-3 text-[0.92rem] text-ink-soft">
        From <cite className="not-italic">{displayTitle(brief.paper_title)}</cite>.{" "}
        <Link to={`/brief/${encodeURIComponent(brief.id)}`} className="link">
          Read the brief →
        </Link>
      </p>
    </article>
  );
}

function LeadPart({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div>
      <dt className="smallcaps text-[0.85rem] text-ink-soft">{label}</dt>
      <dd className="font-mono text-[1.1rem]">{value}</dd>
      <dd className="text-[0.78rem] text-ink-soft">{note}</dd>
    </div>
  );
}
