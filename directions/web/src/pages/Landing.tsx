import { useState } from "react";
import { Link } from "react-router";
import { DirectionItem, LeadCard } from "../components/DirectionItem";
import { HowItWorks, OutcomeGuide } from "../components/Guide";
import { useEffect } from "react";
import { LoopRing } from "../components/LoopRing";
import { OutcomeBar } from "../components/OutcomeBar";
import { Code, DataState, Disclaimer, Empty, Label, Stat } from "../components/ui";
import { useJSON } from "../lib/data";
import { displayTitle, when } from "../lib/format";
import type { About, BriefSummary, Index } from "../types";

const TOP = 5;

export default function Landing() {
  const index = useJSON<Index>("index.json");
  const briefs = useJSON<BriefSummary[]>("briefs.json");
  const about = useJSON<About>("about.json");
  const [paper, setPaper] = useState<string | null>(null);
  const pickPaper = (runId: string | null) => {
    setPaper(runId);
    document.getElementById("paper-filter")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="mx-auto max-w-[1200px] px-4 sm:px-6">
      <section className="grid items-center gap-10 py-12 md:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)] md:py-20">
        <div>
          <p className="mb-4 font-mono text-[13px] text-ink-faint">
            Research directions finder · Hack-Nation Challenge 3 · Agentic scientific discovery
          </p>
          <h1 className="max-w-[15ch] font-serif text-[2.6rem] leading-[1.02] sm:text-[4rem]">
            Many ways of thinking. <em>Which objections survive?</em>
          </h1>
          <p className="measure mt-6 text-[1.2rem] leading-snug text-ink-soft">
            APORIA reconstructs the arguments of philosophy papers and sets differently built reasoners on them: up to
            eight model families and, in its newest runs, five cognitive profiles (explorer, formalist, skeptic,
            synthesizer, minimalist). Every objection they find is checked against the literature and tried against
            two defenders; the lab learns which way of thinking is finding open questions and spends its next
            experiments there. What survives becomes a graded research direction for you.
          </p>
          <p className="measure mt-4 text-[0.95rem] text-ink-soft">
            {about.status === "ready" && about.data.topic?.name ? (
              <>
                Topic: <span className="text-ink">{about.data.topic.name}</span> ({about.data.topic.area}).
              </>
            ) : null}
            {index.status === "ready" && index.data.targets.length ? (
              <>
                {" "}
                <FreshNote fresh={index.data.targets.filter((t) => t.kind === "fresh").length} total={index.data.targets.length} />
              </>
            ) : null}{" "}
            <Link to="/topics" className="link">
              Another topic?
            </Link>{" "}
            None of it is a claim of novelty: further human review is always required.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <a href="#directions" className="btn">
              Find a research direction ↓
            </a>
            <a href="#how" className="btn btn-quiet">
              How the lab works
            </a>
            <Link to="/runs" className="btn btn-quiet">
              Replay a run
            </Link>
          </div>
          <p className="mt-8 font-mono text-[12px] leading-relaxed text-ink-faint">
            diverge (five cognitive policies, Δ) → check the literature → test against two defenders → learn which
            way of thinking finds open questions → decide the next experiment → grade and brief
          </p>
        </div>
        <ReasoningObject />
      </section>

      <section aria-labelledby="headline-h" className="pt-2">
        <h2 id="headline-h" className="sr-only">
          Headline numbers
        </h2>
        <DataState load={index} what="the index">
          {(ix) =>
            ix.headline?.length ? (
              <div className="grid gap-8 sm:grid-cols-3">
                {ix.headline.map((h) => (
                  <Stat key={h.label} value={h.value} label={h.label} source={h.source} />
                ))}
              </div>
            ) : (
              <Empty>No headline numbers yet: they appear once runs or evaluations have been exported.</Empty>
            )
          }
        </DataState>
      </section>

      <section id="directions" aria-labelledby="directions-h" className="scroll-mt-6 pt-16">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <Label>where to write next</Label>
            <h2 id="directions-h" className="font-serif text-[2.2rem] font-medium leading-tight">
              Research directions
            </h2>
            <p className="measure mt-1 text-[1rem] text-ink-soft">
              Objections that came through the lab’s trials, as leads for a paper, best first. A direction ranks high when
              it is all three at once: it survived the defenders (survival), nothing close to it turned up in the
              literature (novelty), and the Assessor judged it sound (quality, out of 5). The lead score is their product.
              Pick a paper to see only its directions. Each opens a printable brief with the argument, the strongest
              replies and why they failed, and the closest literature.
            </p>
          </div>
        </div>
        {paper ? null : (
          <DataState load={briefs} what="research briefs">
            {(list) => (list.length ? <LeadCard brief={list[0]} /> : null)}
          </DataState>
        )}
        <DataState load={index} what="the index">
          {(ix) => (
            <div id="paper-filter" className="mt-6 flex scroll-mt-4 flex-wrap items-center gap-2" role="group" aria-label="Filter research directions by paper">
              <span className="smallcaps mr-1 text-[0.95rem] text-ink-soft">paper</span>
              <button type="button" className="btn btn-quiet" aria-pressed={paper === null} onClick={() => setPaper(null)}>
                All papers
              </button>
              {ix.runs.map((r) => {
                const t = displayTitle(r.title);
                const short = t.length > 40 ? `${t.slice(0, 38).trimEnd()}…` : t;
                return (
                  <button
                    key={r.run_id}
                    type="button"
                    className="btn btn-quiet"
                    aria-pressed={paper === r.run_id}
                    title={t}
                    onClick={() => setPaper(r.run_id)}
                  >
                    {short}
                  </button>
                );
              })}
            </div>
          )}
        </DataState>
        <div className="mt-6">
          <DataState load={briefs} what="research briefs">
            {(list) =>
              list.length ? (
                <>
                  <ol>
                    {(paper ? list.filter((b) => b.run_id === paper) : list.slice(1, TOP)).map((b, i) => (
                      <DirectionItem key={b.id} brief={b} rank={i + (paper ? 1 : 2)} />
                    ))}
                  </ol>
                  {!paper && list.length > TOP ? (
                    <p className="border-t border-rule pt-4">
                      <Link to="/briefs" className="link">
                        All {list.length} research directions →
                      </Link>
                    </p>
                  ) : null}
                  <Disclaimer className="mt-6" />
                  <OutcomeGuide />
                </>
              ) : (
                <Empty>
                  No research briefs yet. A brief is written when an objection survives both defenders (or, failing
                  that, for the best rebutted one). Run <Code>make runs</Code> then <Code>make export</Code>.
                </Empty>
              )
            }
          </DataState>
        </div>
      </section>

      <section aria-labelledby="runs-h" className="pt-16">
        <Label>the experiments</Label>
        <h2 id="runs-h" className="font-serif text-[2.2rem] font-medium leading-tight">
          Runs
        </h2>
        <p className="measure mt-1 text-[1rem] text-ink-soft">
          One run per target paper: the reconstructed argument, every objection, every trial. Open one to replay it
          turn by turn.
        </p>
        <div className="mt-6">
          <DataState load={index} what="the index">
            {(ix) =>
              ix.runs?.length ? (
                <ul>
                  {ix.runs.map((r) => (
                    <li key={r.run_id} className="grid gap-x-6 gap-y-2 border-t border-rule py-5 md:grid-cols-[minmax(0,1fr)_16rem_8rem]">
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2 font-mono text-[0.7rem] text-ink-soft">
                          <span className="rounded-[2px] border border-rule px-1.5">{r.kind}</span>
                          <span>{r.paper_id}</span>
                          {r.finished_at ? <span>· finished {when(r.finished_at)}</span> : null}
                        </div>
                        <h3 className="mt-1 font-serif text-[1.18rem] font-medium leading-snug">
                          <Link to={`/runs/${encodeURIComponent(r.run_id)}`} className="link decoration-transparent hover:decoration-ink">
                            {displayTitle(r.title)}
                          </Link>
                        </h3>
                        {r.argument_title ? <p className="text-[0.95rem] text-ink-soft">Argument: {r.argument_title}</p> : null}
                        <p className="mt-1 font-mono text-[0.72rem] text-ink-soft">
                          {r.objections} objections · {r.trials} trials · {r.briefs?.length ?? 0} briefs · families:{" "}
                          {r.families?.join(", ") || "—"}
                        </p>
                        {r.stop_reason ? <p className="font-mono text-[0.7rem] text-ink-faint">stopped: {r.stop_reason}</p> : null}
                      </div>
                      <OutcomeBar outcomes={r.outcomes ?? {}} />
                      <div>
                        <Link to={`/runs/${encodeURIComponent(r.run_id)}`} className="btn btn-quiet">
                          Replay →
                        </Link>
                      </div>
                    </li>
                  ))}
                </ul>
              ) : (
                <Empty>
                  No runs exported yet. Run <Code>make runs</Code> then <Code>make export</Code>.
                </Empty>
              )
            }
          </DataState>
        </div>
      </section>

      <DataState load={index} what="the index">
        {(ix) => <HowItWorks index={ix} about={about.status === "ready" ? about.data : null} onPickPaper={pickPaper} />}
      </DataState>
    </div>
  );
}

/** How many targets postdate the models' training, said plainly, including when none do. */
function FreshNote({ fresh, total }: { fresh: number; total: number }) {
  if (fresh === 0)
    return (
      <>
        All {total} target papers are older work (no recent open-access paper on this topic passed the screen), so the
        models may already know published replies to them; the prior-art check and the “known answer” label matter
        more here.
      </>
    );
  return (
    <>
      {fresh === total ? `All ${total}` : `${fresh} of ${total}`} target papers were published after 1 August 2026, so
      the models cannot have read published replies to them.
    </>
  );
}

/** APORIA's particle object replaying a recorded run of its five reasoners (served next to this site as
 * engine/ with APORIA's data/); where it is not served, the lab's loop diagram instead. */
function ReasoningObject() {
  const base = import.meta.env.BASE_URL;
  const [featured, setFeatured] = useState<string | null | undefined>(undefined);
  useEffect(() => {
    fetch(`${base}data/index.json`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => setFeatured(d && typeof d.featured === "string" ? d.featured : null))
      .catch(() => setFeatured(null));
  }, [base]);
  if (!featured) return <LoopRing className="mx-auto w-full max-w-[480px]" />;
  return (
    <figure className="m-0">
      <iframe
        title="Particle object replaying a recorded run of APORIA's five reasoners"
        src={`${base}engine/?embed&replay=../data/runs/${featured}.json`}
        loading="lazy"
        className="block aspect-square w-full rounded-md border border-rule bg-[#030407]"
      />
      <figcaption className="mt-2.5 font-mono text-[12px] leading-relaxed text-ink-faint">
        The reasoning object, replaying a recorded run of the five reasoners on one question. Colour is the cognitive
        function running; a dissolving region is a revised hypothesis.{" "}
        <a href={`${base}lab/`} className="link">
          Replay it step by step
        </a>
      </figcaption>
    </figure>
  );
}
