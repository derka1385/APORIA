import type { Assessment, QualityGrade, Revision } from "../types";
import { Label } from "./ui";

// The Assessor's academic-quality grade (crux_lab/lab/assess.py). Ink tones only: outcome colours stay
// reserved for trial outcomes. solid = promising, dashed = needs work, dotted = not yet defensible.
const STYLE: Record<QualityGrade, { border: string; note: string }> = {
  promising: { border: "solid", note: "coherent, and survives the strongest obvious objection" },
  "needs work": { border: "dashed", note: "a real question, but the answer to the main objection needs work" },
  "not yet defensible": { border: "dotted", note: "as framed, it falls to an obvious objection; see what it needs" },
};

/** Scores are averages of four integers (multiples of 0.25): show them exactly, without trailing zeros. */
export const fmtScore = (x: number) => String(Number(x.toFixed(2)));

export function GradeChip({ grade, overall }: { grade: QualityGrade; overall?: number }) {
  const st = STYLE[grade] ?? STYLE["needs work"];
  return (
    <span
      className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-[2px] border border-ink px-1.5 py-[1px] font-mono text-[0.7rem]"
      style={{ borderStyle: st.border }}
      title={`Assessor: ${grade} — ${st.note}`}
    >
      {grade}
      {overall !== undefined ? <span className="text-ink-soft">{fmtScore(overall)}/5</span> : null}
    </span>
  );
}

const CRITERIA: { key: keyof Assessment["scores"]; label: string; q: string }[] = [
  { key: "coherence", label: "Coherence", q: "Is the objection consistent and aimed at the premise as stated?" },
  { key: "robustness", label: "Robustness", q: "Does the direction survive the strongest objection to it?" },
  { key: "significance", label: "Significance", q: "Would it matter for the debate?" },
  { key: "specificity", label: "Specificity", q: "Is it concrete enough to write?" },
];

export function QualityPanel({ a }: { a: Assessment }) {
  return (
    <section aria-labelledby="quality-h" className="border border-ink p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <Label>academic quality check</Label>
          <h2 id="quality-h" className="font-serif text-[1.35rem] font-medium leading-tight">
            What a journal referee would say
          </h2>
        </div>
        <GradeChip grade={a.grade} overall={a.overall} />
      </div>
      <p className="measure mt-2 text-[1.02rem] italic">{a.summary}</p>
      <dl className="mt-3 grid gap-x-4 gap-y-2 sm:grid-cols-2">
        {CRITERIA.map((c) => (
          <div key={c.key}>
            <dt className="flex items-baseline justify-between gap-2 text-[0.92rem]">
              <span className="font-medium">{c.label}</span>
              <span className="font-mono text-[0.78rem]" aria-label={`${a.scores[c.key]} out of 5`}>
                {"●".repeat(a.scores[c.key])}
                <span className="text-rule">{"●".repeat(5 - a.scores[c.key])}</span> {a.scores[c.key]}/5
              </span>
            </dt>
            <dd className="text-[0.86rem] text-ink-soft">{a.reasons?.[c.key] ?? c.q}</dd>
          </div>
        ))}
      </dl>
      {a.strongest_objection ? (
        <div className="mt-4">
          <Label>strongest objection to this direction</Label>
          <p className="measure text-[0.97rem]">{a.strongest_objection}</p>
          {a.reply_available !== undefined ? (
            <p className="mt-1 text-[0.86rem] text-ink-soft">
              A viable answer {a.reply_available ? "is" : "is not yet"} in the brief or the debate.
            </p>
          ) : null}
        </div>
      ) : null}
      {a.what_it_needs ? (
        <div className="mt-3">
          <Label>what the paper would need</Label>
          <p className="measure text-[0.97rem]">{a.what_it_needs}</p>
        </div>
      ) : null}
      <p className="mt-3 text-[0.8rem] text-ink-soft">
        An AI assessment{a.model ? ` (${a.model})` : ""}, not peer review; philosophers or works it mentions come
        from the model’s own knowledge and are not checked against the corpus. The grade is computed from the four scores:
        a direction is “promising” only if it is coherent and robust (both 4+) and averages 3.75+; it is “not yet
        defensible” if coherence or robustness is 2 or lower.
      </p>
    </section>
  );
}

export function RevisionPanel({ r, before }: { r: Revision; before?: Assessment | null }) {
  const after = r.assessment;
  return (
    <section aria-labelledby="revision-h" className="border border-dashed border-ink p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <Label>revision round</Label>
          <h2 id="revision-h" className="font-serif text-[1.35rem] font-medium leading-tight">
            Revised to answer the referee
          </h2>
        </div>
        {after ? (
          <span className="flex items-center gap-2 font-mono text-[0.72rem] text-ink-soft">
            {before ? <GradeChip grade={before.grade} overall={before.overall} /> : null}
            <span aria-hidden>→</span>
            <GradeChip grade={after.grade} overall={after.overall} />
          </span>
        ) : null}
      </div>
      <p className="mt-2 text-[0.92rem] italic text-ink-soft">
        {r.what_changed}
        {r.narrowed ? " The thesis was narrowed." : ""}
      </p>
      <h3 className="mt-3 font-serif text-[1.15rem] font-medium leading-snug">{r.research_question}</h3>
      <p className="measure mt-2 text-[1rem] leading-relaxed">{r.paper_direction}</p>
      <div className="mt-3">
        <Label>how the paper answers the main objection</Label>
        <p className="measure text-[0.98rem]">{r.reply_to_strongest_objection}</p>
      </div>
      {after ? (
        <div className="mt-4 border-t border-rule pt-3">
          <Label>fresh re-assessment</Label>
          <p className="measure text-[0.98rem] italic">{after.summary}</p>
          <p className="mt-1 font-mono text-[0.75rem] text-ink-soft">
            {Object.entries(after.scores)
              .map(([k, v]) => `${k} ${v}/5`)
              .join(" · ")}
          </p>
          {after.strongest_objection ? (
            <p className="measure mt-2 text-[0.92rem]">
              <span className="font-medium">Strongest remaining objection:</span> {after.strongest_objection}
            </p>
          ) : null}
          {after.what_it_needs ? (
            <p className="measure mt-1 text-[0.92rem]">
              <span className="font-medium">What it still needs:</span> {after.what_it_needs}
            </p>
          ) : null}
        </div>
      ) : null}
      <p className="mt-3 text-[0.8rem] text-ink-soft">
        Rewritten by {r.model ?? "a reviser model"} from the referee’s critique, then graded again by the assessor in a
        fresh read that does not see its earlier critique. Both grades are kept.
      </p>
    </section>
  );
}

/** One line near the top of a brief: the grade (before → after revision) and a link to the full check below. */
export function QualityStrip({ a, after }: { a: Assessment; after: Assessment | null }) {
  return (
    <p className="no-print mt-4 flex flex-wrap items-center gap-2 border-y border-rule py-2 text-[0.92rem]">
      <span className="smallcaps text-ink-soft">academic quality</span>
      <GradeChip grade={a.grade} overall={a.overall} />
      {after ? (
        <>
          <span aria-hidden className="text-ink-soft">→</span>
          <GradeChip grade={after.grade} overall={after.overall} />
          <span className="text-ink-soft">after revision</span>
        </>
      ) : null}
      <a href="#quality" className="link ml-auto">
        Referee’s assessment{after ? " and revision" : ""} ↓
      </a>
    </p>
  );
}
