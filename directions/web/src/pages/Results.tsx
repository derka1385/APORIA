import { useEffect, useState, type ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useDrawer } from "../components/drawer";
import { ClaimRef } from "../components/text";
import { Code, DataState, Empty, KV, Label, Marginal, OutcomeChip } from "../components/ui";
import { currentTopic } from "../lib/topics";
import { useJSON } from "../lib/data";
import { num, pct, when } from "../lib/format";
import type { E1, E2, E3, ResultsFile } from "../types";

export default function Results() {
  const results = useJSON<ResultsFile>("results.json");
  return (
    <div className="mx-auto max-w-[1100px] px-4 py-10 sm:px-6">
      <Label>does the lab work?</Label>
      <h1 className="font-serif text-[2.6rem] font-medium leading-tight">Results</h1>
      <p className="measure mt-2 text-[1.05rem] text-ink-soft">
        Three automatic evaluations, no human labels. Each is reported as it came out of <Code>results/</Code>,
        including null or negative results, with its own statement of limits.
      </p>
      <div className="mt-8 space-y-14">
        <DataState load={results} what="the evaluation results">
          {(r) => (
            <>
              <E1Section e={r.e1} />
              <E2Section e={r.e2} />
              <E3Section e={r.e3} />
            </>
          )}
        </DataState>
      </div>
    </div>
  );
}

/** Why an evaluation is missing for the topic being viewed (E2 and E3 were designed around the first topic). */
const NOT_RUN_WHY: Record<string, string> = {
  E2: "E2 needs a canonical argument whose published objections and replies are in the corpus (an e2_fixture in the topic file); this topic has none, so it was not run.",
  E3: "E3 compares model conditions on the same arguments and was run for divine hiddenness only; it was not repeated for this topic.",
};

function NotRun({ name }: { name: string }) {
  const t = currentTopic();
  if (t && !t.default && NOT_RUN_WHY[name]) return <Empty>{NOT_RUN_WHY[name]}</Empty>;
  return (
    <Empty>
      No result for {name} yet: <Code>results/{name.toLowerCase()}.json</Code> is empty or missing. Run{" "}
      <Code>make eval</Code>, then <Code>make export</Code>.
    </Empty>
  );
}

function Meta({ n, timestamp, models, settings, limits }: { n?: ReactNode; timestamp: string; models: Record<string, string>; settings: Record<string, unknown>; limits: string }) {
  return (
    <div className="mt-6 space-y-4">
      {limits ? (
        <div>
          <Label className="mb-1">limits, verbatim</Label>
          <blockquote className="measure whitespace-pre-line border-l-2 border-revision_required pl-4 text-[1rem] leading-relaxed">{limits}</blockquote>
        </div>
      ) : (
        <p className="text-[0.92rem] text-ink-soft">No limits statement was written for this evaluation.</p>
      )}
      <div className="flex flex-wrap gap-x-8 gap-y-2 font-mono text-[0.75rem] text-ink-soft">
        {n !== undefined ? <span>n = {n}</span> : null}
        <span>run {when(timestamp)}</span>
      </div>
      <details>
        <summary className="cursor-pointer text-[0.92rem] text-ink-soft">Models and settings</summary>
        <div className="mt-3 grid gap-6 md:grid-cols-2">
          <div>
            <div className="smallcaps mb-1 text-ink-soft">models</div>
            <KV value={models} />
          </div>
          <div>
            <div className="smallcaps mb-1 text-ink-soft">settings</div>
            <KV value={settings} />
          </div>
        </div>
      </details>
    </div>
  );
}

function useNarrow(): boolean {
  const [narrow, setNarrow] = useState(() => typeof window !== "undefined" && window.innerWidth < 640);
  useEffect(() => {
    const on = () => setNarrow(window.innerWidth < 640);
    window.addEventListener("resize", on);
    return () => window.removeEventListener("resize", on);
  }, []);
  return narrow;
}

function E1Section({ e }: { e: E1 | null }) {
  const narrow = useNarrow();
  return (
    <Marginal label="E1 · prior-art recall">
      <h2 className="font-serif text-[1.6rem] font-medium leading-tight">Can the lab find the paper an objection came from?</h2>
      <p className="measure mt-1 text-[0.98rem] text-ink-soft">
        Objections extracted from corpus papers are reworded without names or jargon, then searched four ways. Recall@5:
        how often the source work is among the top five distinct works (duplicate records of one paper merged).
      </p>
      {e && e.methods?.length ? (
        <>
          <div className="mt-5 w-full" style={{ height: Math.max(180, e.methods.length * 64 + 40) }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={e.methods} layout="vertical" margin={{ top: 4, right: narrow ? 44 : 80, bottom: 4, left: 0 }}>
                <CartesianGrid horizontal={false} stroke="#353B42" strokeDasharray="2 4" />
                <XAxis
                  type="number"
                  domain={[0, 1]}
                  tickFormatter={(v: number) => pct(v)}
                  tick={{ fontFamily: "JetBrains Mono, monospace", fontSize: 11, fill: "#B4BBC2" }}
                  stroke="#F4F1E9"
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={narrow ? 120 : 210}
                  tick={{ fontFamily: "Newsreader, Georgia, serif", fontSize: narrow ? 12 : 14, fill: "#F4F1E9" }}
                  stroke="#F4F1E9"
                />
                <Tooltip
                  cursor={{ fill: "#1B1F23" }}
                  contentStyle={{ background: "#121416", border: "1px solid #F4F1E9", borderRadius: 2, fontFamily: "JetBrains Mono, monospace", fontSize: 12 }}
                  formatter={(v) => [pct(Number(v)), "recall@5"]}
                />
                <Bar dataKey="recall_at_5" fill="#F4F1E9" barSize={22} isAnimationActive={false}>
                  <LabelList
                    dataKey="recall_at_5"
                    position="right"
                    formatter={(v) => pct(Number(v))}
                    style={{ fontFamily: "JetBrains Mono, monospace", fontSize: 12, fill: "#F4F1E9" }}
                  />
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
          <table className="table mt-4">
            <caption className="sr-only">E1 recall at 5 per search method</caption>
            <thead>
              <tr>
                <th>method</th>
                <th className="num">recall@5</th>
                <th className="num">hits / n</th>
                <th className="num" title="Record-level: duplicate records of a paper count as misses">strict, per record</th>
              </tr>
            </thead>
            <tbody>
              {e.methods.map((m) => (
                <tr key={m.name}>
                  <td>{m.name}</td>
                  <td className="num">{pct(m.recall_at_5)}</td>
                  <td className="num">
                    {m.hits} / {e.n}
                  </td>
                  <td className="num">{m.recall_at_5_strict_record != null ? pct(m.recall_at_5_strict_record) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <Meta n={e.n} timestamp={e.timestamp} models={e.models} settings={e.settings} limits={e.limits} />
        </>
      ) : e ? (
        <>
          <Empty>E1 ran but recorded no methods.</Empty>
          <Meta n={e.n} timestamp={e.timestamp} models={e.models} settings={e.settings} limits={e.limits} />
        </>
      ) : (
        <NotRun name="E1" />
      )}
    </Marginal>
  );
}

function share(a: number, n: number): string {
  return n ? `${a}/${n} (${pct(a / n)})` : "—";
}

function E2Section({ e }: { e: E2 | null }) {
  return (
    <Marginal label="E2 · gauntlet calibration">
      <h2 className="font-serif text-[1.6rem] font-medium leading-tight">Does the Referee recognise answered objections and misreadings?</h2>
      <p className="measure mt-1 text-[0.98rem] text-ink-soft">
        Published objections whose published replies are in the corpus should come out as known answers, with the right
        reply cited. Deliberately distorted premises should come out as misreadings.
      </p>
      {e ? (
        <>
          <table className="table mt-5">
            <thead>
              <tr>
                <th>set</th>
                <th className="num">n</th>
                <th className="num">expected label</th>
                <th className="num">published reply cited</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Published objections with replies in the corpus</td>
                <td className="num">{e.known_answer?.n ?? "—"}</td>
                <td className="num">{e.known_answer ? share(e.known_answer.labelled_known_answer, e.known_answer.n) : "—"}</td>
                <td className="num">{e.known_answer ? share(e.known_answer.correct_reply_cited, e.known_answer.n) : "—"}</td>
              </tr>
              {e.known_answer?.gold_reply_cited_by_a_defender !== undefined ? (
                <tr>
                  <td>Published objections where a defender cited the published reply</td>
                  <td className="num">{e.known_answer.n}</td>
                  <td className="num">n/a</td>
                  <td className="num">{share(e.known_answer.gold_reply_cited_by_a_defender, e.known_answer.n)}</td>
                </tr>
              ) : null}
              <tr>
                <td>Deliberate misreadings</td>
                <td className="num">{e.misreading?.n ?? "—"}</td>
                <td className="num">{e.misreading ? share(e.misreading.caught, e.misreading.n) : "—"}</td>
                <td className="num">n/a</td>
              </tr>
            </tbody>
          </table>
          {e.items?.length ? (
            <details className="mt-4">
              <summary className="cursor-pointer text-[0.92rem] text-ink-soft">All {e.items.length} items, with the objections tested</summary>
              <ol className="mt-2">
                {e.items.map((it, i) => (
                  <E2Item key={i} it={it} />
                ))}
              </ol>
            </details>
          ) : null}
          <Meta timestamp={e.timestamp} models={e.models} settings={e.settings} limits={e.limits} />
        </>
      ) : (
        <NotRun name="E2" />
      )}
    </Marginal>
  );
}

function E2Item({ it }: { it: E2["items"][number] }) {
  const { openRecord } = useDrawer();
  return (
    <li className="border-t border-rule py-2.5">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[0.85rem]">
        <span className="font-mono text-[0.72rem]">{it.kind.replace(/_/g, " ")}</span>
        {it.target ? <span className="font-mono text-[0.72rem] text-ink-soft">→ {it.target}</span> : null}
        <OutcomeChip outcome={it.status === "failed" ? "failed" : it.outcome} />
        <span className={`font-mono text-[0.72rem] ${it.correct ? "text-ink" : "text-ink-soft"}`}>{it.correct ? "correct" : "not correct"}</span>
        <span className="font-mono text-[0.72rem] text-ink-soft">
          {it.kind === "known_answer" ? "reply in " : "from "}
          {it.source_paper
            .split(/,\s*/)
            .filter(Boolean)
            .map((pid, i) => (
              <span key={pid}>
                {i ? ", " : ""}
                <button type="button" className="link" onClick={() => openRecord(pid)}>
                  {pid}
                </button>
              </span>
            ))}
        </span>
        {it.objection_paper ? (
          <span className="font-mono text-[0.72rem] text-ink-soft">
            objection from{" "}
            <button type="button" className="link" onClick={() => openRecord(it.objection_paper!)}>
              {it.objection_paper}
            </button>
          </span>
        ) : null}
      </div>
      {it.objection ? (
        <details className="mt-1">
          <summary className="cursor-pointer text-[0.88rem] text-ink-soft">The objection</summary>
          <p className="turn-body mt-1 whitespace-pre-line">{it.objection}</p>
          {it.reply_claims?.length ? (
            <p className="mt-1 flex flex-wrap items-baseline gap-1.5 text-[0.75rem] text-ink-soft">
              <span className="smallcaps">published reply</span>
              {it.reply_claims.map((c) => (
                <ClaimRef key={c} id={c} />
              ))}
            </p>
          ) : null}
          {it.cited?.length ? (
            <p className="mt-1 flex flex-wrap items-baseline gap-1.5 text-[0.75rem] text-ink-soft">
              <span className="smallcaps">defenders cited</span>
              {it.cited.map((c) => (
                <ClaimRef key={c} id={c} />
              ))}
            </p>
          ) : null}
        </details>
      ) : null}
    </li>
  );
}

function E3Section({ e }: { e: E3 | null }) {
  return (
    <Marginal label="E3 · diversity ablation">
      <h2 className="font-serif text-[1.6rem] font-medium leading-tight">Do constrained roles and mixed model families find different objections?</h2>
      <p className="measure mt-1 text-[0.98rem] text-ink-soft">
        Objections to the same arguments under three conditions: one model with a plain prompt, one model with the
        lab’s constrained roles, and mixed families with constrained roles.
      </p>
      {e && e.conditions?.length ? (
        <>
          <div className="mt-5 overflow-x-auto">
            <table className="table min-w-[44rem]">
              <thead>
                <tr>
                  <th>condition</th>
                  <th className="num">n</th>
                  <th className="num">distinct premises</th>
                  <th className="num">mean pairwise distance</th>
                  <th className="num">share passing pre-screen</th>
                  <th className="num">share surviving</th>
                  <th className="num">share novelty &gt; 0.5</th>
                </tr>
              </thead>
              <tbody>
                {e.conditions.map((c) => (
                  <tr key={c.name}>
                    <td>{c.name}</td>
                    <td className="num">{c.n}</td>
                    <td className="num">{c.distinct_premises}</td>
                    <td className="num">{num(c.mean_pairwise_distance, 3)}</td>
                    <td className="num">{c.share_passing_prescreen === undefined ? "—" : pct(c.share_passing_prescreen)}</td>
                    <td className="num">{c.share_surviving === null ? <span title="Not available: see the limits below">n/a*</span> : pct(c.share_surviving)}</td>
                    <td
                      className="num"
                      title={
                        c.novelty_assessed !== undefined
                          ? `over ${c.novelty_assessed} completed novelty checks; ${c.novelty_unavailable ?? 0} could not be assessed`
                          : undefined
                      }
                    >
                      {c.share_novelty_gt_05 === null ? "n/a" : pct(c.share_novelty_gt_05)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {e.conditions.some((c) => c.share_surviving === null) ? (
            <p className="mt-2 text-[0.85rem] text-ink-soft">* Not available for this evaluation; the limits below say why.</p>
          ) : null}
          <Meta timestamp={e.timestamp} models={e.models} settings={e.settings} limits={e.limits} />
        </>
      ) : e ? (
        <>
          <Empty>E3 ran but recorded no conditions.</Empty>
          <Meta timestamp={e.timestamp} models={e.models} settings={e.settings} limits={e.limits} />
        </>
      ) : (
        <NotRun name="E3" />
      )}
    </Marginal>
  );
}
