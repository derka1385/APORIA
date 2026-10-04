import { Link } from "react-router";
import { displayTitle } from "../lib/format";
import type { About, Index, Outcome } from "../types";
import { Code, Label, OutcomeChip } from "./ui";

/** What each Referee label means, most promising for a researcher first. Definitions follow the lab's spec. */
const OUTCOME_GUIDE: { outcome: Outcome; survival: string; means: string; forYou: string }[] = [
  {
    outcome: "standing",
    survival: "1.0",
    means: "Every defence failed, or a defender conceded without a workable repair.",
    forYou: "The strongest lead: the argument has no answer to this yet.",
  },
  {
    outcome: "revision_required",
    survival: "0.8",
    means: "The argument survives only if a premise is changed or added; the defenders say which.",
    forYou: "A good lead: this premise needs work, and the brief shows the repair the defenders needed.",
  },
  {
    outcome: "rebutted",
    survival: "0.3",
    means: "A defender gave an adequate new reply that is not already in the literature the lab holds.",
    forYou: "A weaker lead, mostly for someone defending the argument.",
  },
  {
    outcome: "known_answer",
    survival: "0.1",
    means: "A published reply already resolves it; the lab cites that reply and verifies the citation.",
    forYou: "Not new: read the cited reply instead.",
  },
  {
    outcome: "misreading",
    survival: "0.0",
    means: "The objection attacked something the paper does not claim. The Referee stops it before any debate.",
    forYou: "Not a lead.",
  },
];

export function OutcomeGuide() {
  return (
    <div className="mt-5">
      <Label>what the labels mean</Label>
      <dl className="mt-1 divide-y divide-rule border-y border-rule">
        {OUTCOME_GUIDE.map((g) => (
          <div key={g.outcome} className="grid gap-x-6 gap-y-1 py-2.5 md:grid-cols-[11.5rem_minmax(0,1fr)_minmax(0,1fr)]">
            <dt className="flex items-center gap-2">
              <OutcomeChip outcome={g.outcome} />
              <span className="font-mono text-[0.68rem] text-ink-soft" title="survival score used for ranking">
                S {g.survival}
              </span>
            </dt>
            <dd className="text-[0.95rem]">{g.means}</dd>
            <dd className="text-[0.95rem] text-ink-soft">{g.forYou}</dd>
          </div>
        ))}
      </dl>
      <p className="measure mt-2 text-[0.88rem] text-ink-soft">
        Each objection faces two defenders separately and keeps the outcome most favourable to the paper, so a label
        here holds against both. Research directions are ranked by lead score: survival × novelty × the Assessor’s
        quality score out of 5. Labels describe the state of the
        debate, never whether the paper’s conclusion is true. Separately, an Assessor agent reads every direction
        like a journal referee and gives it a quality grade (promising, needs work, or not yet defensible) with the
        strongest objection to it and what the paper would need.
      </p>
    </div>
  );
}

const STEPS: { name: string; text: string }[] = [
  {
    name: "Read",
    text: "The Extractor pulls the paper’s claims, each with a verbatim quote found in the text, and rebuilds its main argument as numbered premises and a conclusion.",
  },
  {
    name: "Formalise",
    text: "A truth table checks whether the premises entail the conclusion. If they do not, the Formalizer names the hidden premise the argument relies on.",
  },
  {
    name: "Object",
    text: "About a dozen objections, each against one premise: blind thought experiments (one per model), an attack on the hidden premise, two tradition lenses (for example skeptical theism or Molinism), and a beginner’s question sharpened into an objection. None of these agents sees the literature.",
  },
  {
    name: "Check prior art",
    text: "Each objection is restated three ways and searched against the corpus and a live OpenAlex query; a strict reranker asks whether a passage makes the same move against the same premise. That gives the novelty score.",
  },
  {
    name: "Test",
    text: "The Director (plain code, no model) picks the most promising objections, up to six trials per paper. In a trial two defenders from different models reply with cited literature, the objector answers back, and the Referee labels the outcome.",
  },
  {
    name: "Revise",
    text: "If the argument survives only with a changed premise, that premise joins the argument and is attacked in turn.",
  },
  {
    name: "Brief",
    text: "The best survivors become research briefs: the question, the objection, the replies and why they failed, the nearest literature, and what a paper on it would argue.",
  },
];

function lowerFirst(s: string): string {
  return s && s[1] !== s[1]?.toUpperCase() ? s[0].toLowerCase() + s.slice(1) : s;
}

export function HowItWorks({
  index,
  about,
  onPickPaper,
}: {
  index: Index;
  about: About | null;
  onPickPaper: (runId: string) => void;
}) {
  const corpus = about?.corpus;
  const topic = lowerFirst(about?.topic?.name ?? "divine hiddenness");
  const claims = (about?.map_stats?.claims_indexed as number | undefined) ?? null;
  const targets = new Map(index.targets.map((t) => [t.id, t]));
  return (
    <section id="how" aria-labelledby="how-h" className="scroll-mt-6 pt-16">
      <Label>for new readers</Label>
      <h2 id="how-h" className="font-serif text-[2.2rem] font-medium leading-tight">
        How the lab works, and how to explore it
      </h2>

      <div className="mt-6 grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div>
          <h3 className="font-serif text-[1.35rem] font-medium">One experiment = one paper</h3>
          <p className="measure mt-1 text-[0.98rem] text-ink-soft">
            The lab runs per paper. A run takes one paper’s main argument through these steps; the{" "}
            <Link to="/runs" className="link">
              Lab
            </Link>{" "}
            page replays a run turn by turn.
          </p>
          <ol className="mt-3 space-y-2.5">
            {STEPS.map((s, i) => (
              <li key={s.name} className="grid grid-cols-[1.6rem_minmax(0,1fr)] gap-x-2">
                <span className="font-mono text-[0.8rem] text-ink-soft">{i + 1}.</span>
                <p className="text-[0.97rem]">
                  <span className="font-medium">{s.name}.</span> {s.text}
                </p>
              </li>
            ))}
          </ol>
        </div>

        <div>
          <h3 className="font-serif text-[1.35rem] font-medium">The papers in this build</h3>
          <p className="measure mt-1 text-[0.98rem] text-ink-soft">
            {index.runs.length} papers, one run each. “Fresh” papers were published after 1 August 2026, so the models
            cannot have read replies to them; “classic” papers are older work on {topic}.
          </p>
          <ul className="mt-3">
            {index.runs.map((r) => {
              const t = targets.get(r.target_id);
              return (
                <li key={r.run_id} className="border-t border-rule py-3">
                  <div className="flex flex-wrap items-center gap-2 font-mono text-[0.68rem] text-ink-soft">
                    <span className="rounded-[2px] border border-rule px-1.5">{r.kind}</span>
                    {t?.published ? <span>published {t.published}</span> : t?.year ? <span>{t.year}</span> : null}
                  </div>
                  <p className="mt-0.5 font-serif text-[1.05rem] leading-snug">{displayTitle(r.title)}</p>
                  {t?.thesis ? <p className="text-[0.9rem] text-ink-soft">Thesis: {t.thesis}</p> : null}
                  <div className="mt-1.5 flex flex-wrap gap-2">
                    <button type="button" className="btn btn-quiet" onClick={() => onPickPaper(r.run_id)}>
                      Its research directions ({r.briefs?.length ?? 0})
                    </button>
                    <Link to={`/runs/${encodeURIComponent(r.run_id)}`} className="btn btn-quiet">
                      Replay its run →
                    </Link>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      </div>

      <div className="mt-12 grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div>
          <h3 className="font-serif text-[1.35rem] font-medium">Looking into something else</h3>
          <ul className="mt-2 space-y-3 text-[0.97rem]">
            <li>
              <span className="font-medium">Another paper in this build.</span> Use the paper filter above the research
              directions, or replay that paper’s run.
            </li>
            <li>
              <span className="font-medium">A different topic</span> (say, the problem of evil rather than{" "}
              {topic}). The lab runs one topic at a time. See{" "}
              <Link to="/topics" className="link">
                Topics
              </Link>{" "}
              for what has been run and what is set up; to add your own,{" "}
              <Link to="/start" className="link">
                Start a topic
              </Link>{" "}
              writes the topic file and lists the steps to run it on your machine.
            </li>
            <li>
              <span className="font-medium">An idea of your own.</span> The{" "}
              <Link to="/atlas" className="link">
                Atlas
              </Link>{" "}
              has a “Has this move been made?” box: describe an objection or reply in a sentence and it searches
              {claims ? ` all ${claims.toLocaleString()} claims` : " every claim"} the lab extracted
              {corpus ? ` from ${corpus.distinct_works ?? corpus.records} works` : ""} gathered for this topic, with the
              papers they come from.
            </li>
            <li>
              <span className="font-medium">A paper the lab has not read.</span> This public site is a replay of
              finished runs: it has no server and no model access, so it cannot start new experiments. To run the lab on
              another argument, clone the repository, write the argument’s premises and conclusion in plain English in{" "}
              <Code>data/manual_targets/&lt;name&gt;.md</Code>, then run <Code>make targets map</Code> and{" "}
              <Code>make run TARGET=manual-&lt;name&gt;</Code>. That needs a model provider (see the{" "}
              <a href="https://github.com/univerdread/crux-lab#quickstart" className="link">
                README
              </a>
              ) and was not exercised in this build.
            </li>
          </ul>
        </div>

        <div>
          <h3 className="font-serif text-[1.35rem] font-medium">Where the papers come from</h3>
          <p className="measure mt-2 text-[0.97rem]">
            The corpus comes from <span className="font-medium">OpenAlex</span>, an open index of scholarly works
            {corpus
              ? `: ${corpus.records.toLocaleString()} records (${(corpus.distinct_works ?? corpus.records).toLocaleString()} distinct works, since OpenAlex lists some papers more than once), ${corpus.full_texts} of them with open-access full text`
              : ""}
            .{" "}
            {corpus?.searches?.length
              ? `Searches covered ${corpus.searches.join(", ")}, plus recent work in the area published since August 2026.`
              : "Searches covered divine hiddenness, nonresistant nonbelief, divine silence and related topics, plus philosophy of religion published since August 2026."}
          </p>
          <p className="measure mt-3 text-[0.97rem]">
            <span className="font-medium">Why not PhilArchive?</span> The plan was to take fresh papers from
            PhilArchive’s bulk-metadata interface (OAI-PMH). During this build its address on api.philpapers.org refused
            data queries without an API key, and its address on philarchive.org sat behind bot protection that blocks
            automated clients. The lab does not work around bot protection, so it used OpenAlex, which indexes much of
            the same literature. A PhilPapers API key does not open it either: the key is
            accepted, but that address no longer serves OAI-PMH, and PhilPapers’ terms point to the philarchive.org
            address, forbid mass-querying by scripts, and ask third parties to get in touch for bulk access. Asking
            PhilPapers to allow this harvester is the way to bring PhilArchive back in.
          </p>
        </div>
      </div>
    </section>
  );
}
