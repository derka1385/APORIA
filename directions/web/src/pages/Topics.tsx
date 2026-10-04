import { Link } from "react-router";
import { Code, DataState, Label } from "../components/ui";
import { useJSON } from "../lib/data";
import { currentTopic, switchTopic } from "../lib/topics";
import type { TopicInfo, TopicsFile } from "../types";

export default function Topics() {
  const topics = useJSON<TopicsFile>("topics.json");
  const cur = currentTopic();
  return (
    <div className="mx-auto max-w-[1100px] px-4 py-10 sm:px-6">
      <Label>choose what to explore</Label>
      <h1 className="font-serif text-[2.6rem] font-medium leading-tight">Topics</h1>
      <p className="measure mt-2 text-[1.05rem] text-ink-soft">
        Crux Lab works on one topic at a time: it gathers the literature on the topic, picks a handful of papers that
        argue for something, and runs an experiment on each paper’s argument. These are the topics set up in this
        repository. A topic that has been run can be explored here; one that has not shows exactly how to run it.
      </p>

      <DataState load={topics} what="the topic list">
        {(f) => (
          <ul className="mt-8 space-y-6">
            {f.topics.map((t) => (
              <TopicCard key={t.slug} t={t} current={cur?.slug === t.slug} />
            ))}
            <li className="border border-dashed border-rule p-5">
              <h2 className="font-serif text-[1.5rem] font-medium">A topic of your own</h2>
              <p className="measure mt-1 text-[0.98rem] text-ink-soft">
                Interested in something else, say the fine-tuning argument, the problem of evil or moral realism? A
                topic is a short file: what to search for, how to recognise an on-topic paper, and which philosophical
                traditions should press objections. The next page writes it with you and lists the steps to run it.
              </p>
              <Link to="/start" className="btn mt-3 inline-block">
                Start a topic →
              </Link>
            </li>
          </ul>
        )}
      </DataState>
    </div>
  );
}

function TopicCard({ t, current }: { t: TopicInfo; current: boolean }) {
  const ready = t.status === "ready" && t.counts;
  return (
    <li className="border-t border-ink pt-5">
      <div className="flex flex-wrap items-center gap-2 font-mono text-[0.7rem] text-ink-soft">
        <span className="rounded-[2px] border border-rule px-1.5">{ready ? "explored" : "configured, not run yet"}</span>
        <span>{t.area}</span>
        {current ? <span className="rounded-[2px] bg-ink px-1.5 text-paper">viewing now</span> : null}
      </div>
      <h2 className="mt-1 font-serif text-[1.7rem] font-medium leading-tight">{t.name}</h2>
      <p className="measure mt-1 text-[1rem]">{t.description}</p>

      {ready && t.counts ? (
        <p className="mt-2 font-mono text-[0.78rem] text-ink-soft">
          {t.counts.papers} papers · {t.counts.objections} objections · {t.counts.trials} trials · {t.counts.briefs}{" "}
          research directions
          {t.counts.works ? ` · literature: ${t.counts.works.toLocaleString()} works` : ""}
          {t.families?.length ? ` · ${t.families.length} model families (${t.families.join(", ")})` : ""}
        </p>
      ) : null}

      {ready && t.lead ? (
        <div className="mt-3 border-l-2 border-ink pl-3">
          <Label>strongest lead</Label>
          <p className="measure font-serif text-[1.1rem] leading-snug">
            {current ? (
              <Link to={`/brief/${encodeURIComponent(t.lead.id)}`} className="link decoration-transparent hover:decoration-ink">
                {t.lead.question}
              </Link>
            ) : (
              t.lead.question
            )}
          </p>
          <p className="font-mono text-[0.72rem] text-ink-soft">
            novelty {t.lead.novelty.toFixed(2)}
            {t.lead.quality != null ? ` · quality ${Number((t.lead.quality * 5).toFixed(2))}/5` : ""}
            {t.lead.score !== undefined ? ` · lead score ${t.lead.score.toFixed(3)}` : ""}
          </p>
        </div>
      ) : null}

      <div className="mt-3 grid gap-4 md:grid-cols-2">
        <div>
          <Label>searches the literature for</Label>
          <p className="text-[0.92rem]">{t.searches.join(" · ")}</p>
        </div>
        <div>
          <Label>objections pressed from</Label>
          <p className="text-[0.92rem]">{t.schools.join(" · ")}</p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        {ready ? (
          current ? (
            <Link to="/" className="btn">
              Its research directions →
            </Link>
          ) : (
            <button type="button" className="btn" onClick={() => switchTopic(t.slug)}>
              Explore this topic →
            </button>
          )
        ) : null}
        <Link to={`/start?from=${encodeURIComponent(t.slug)}`} className="btn btn-quiet">
          Use as a template
        </Link>
      </div>

      {!ready ? (
        <details className="mt-4">
          <summary className="cursor-pointer text-[0.98rem] font-medium">How to run this topic</summary>
          <p className="measure mt-2 text-[0.92rem] text-ink-soft">
            The public site only replays topics that have been run. To run this one, on your own machine with a model
            provider set up (see <Link to="/start" className="link">Start a topic</Link>, steps 1–2), the topic file is
            already in the repository at <Code>{t.config_path}</Code>:
          </p>
          <pre tabIndex={0} className="mt-2 overflow-x-auto border border-rule bg-paper-deep p-3 font-mono text-[0.78rem]">
            {t.commands.join("\n")}
          </pre>
        </details>
      ) : null}
    </li>
  );
}
