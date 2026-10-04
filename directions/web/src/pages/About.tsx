import type { ReactNode } from "react";
import { LoopRing, STAGES } from "../components/LoopRing";
import { DataState, KV, Label, Marginal, ModelBadge, OutcomeChip } from "../components/ui";
import { useJSON } from "../lib/data";
import { agentLabel } from "../lib/format";
import { OUTCOME_COLORS, type About as AboutData, type Outcome } from "../types";

// Method definitions (the spec), not results.
const OUTCOME_MEANING: Record<Outcome, string> = {
  misreading: "Attacks something the argument does not claim.",
  known_answer: "A reply in the corpus resolves it, cited by id and verified.",
  rebutted: "A defender gave an adequate new reply not found in the corpus.",
  revision_required: "The argument survives only by changing or adding a premise.",
  standing: "Every defense failed, or a defender conceded.",
};

const AGENTS: { name: string; constraint: string }[] = [
  { name: "Extractor", constraint: "Schema-valid output; every claim keeps a verbatim quote that must be found in the source text, or the claim is dropped." },
  { name: "Formalizer", constraint: "The propositional skeleton must parse; a truth table decides validity; a proposed hidden premise must make the argument valid on re-check." },
  { name: "Blind Thought-Experimenter", constraint: "No literature in its context; must name an existing premise id; gives a concrete case, not a citation." },
  { name: "Hidden-Premise Attacker", constraint: "Must target the Formalizer’s hidden premise." },
  { name: "Tradition Lens", constraint: "Declares one school first (skeptical theism, Molinism, open theism, Reformed epistemology, naturalism) and argues from it." },
  { name: "Naive Questioner", constraint: "A small model asks a plain question; it counts only after another agent sharpens it into an objection." },
  { name: "Defender A / Defender B", constraint: "See retrieved literature; must cite claim ids for literature; any premise change stated in one sentence. B is more concessive and, when possible, a different family." },
  { name: "Referee", constraint: "Picks exactly one outcome; quotes the deciding sentence verbatim; every cited id is verified and unverifiable ones are struck. Never rules on whether the conclusion is true." },
  { name: "Prior-Art Hunter", constraint: "Restates the objection three ways, searches BM25 + embeddings and OpenAlex, then gives each match a verdict: same move, related, different." },
  { name: "Director", constraint: "Plain code, no model: priority = S · N · (0.5 + 0.5·C) + 0.1·E." },
  { name: "Assessor", constraint: "Reads each finished research direction like a journal referee (never sees which models wrote it): scores coherence, robustness, significance and specificity 1–5, names the strongest objection and what the paper needs. The grade is computed in code; robustness 2 or lower means “not yet defensible”." },
];

// Status pills use ink tones (outcome colours are reserved for outcomes): solid = used in this build,
// dashed = wired but not used, dotted = partly (e.g. local stand-in).
function Status({ on, children }: { on: boolean | null; children: ReactNode }) {
  const color = on === true ? "#F4F1E9" : "#B4BBC2";
  const style = on === true ? "solid" : on === false ? "dashed" : "dotted";
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-[2px] border px-1.5 font-mono text-[0.7rem]" style={{ borderColor: color, borderStyle: style, color }}>
      <span aria-hidden className="inline-block h-1.5 w-1.5 rounded-full" style={{ backgroundColor: on === true ? color : "transparent", border: `1px solid ${color}` }} />
      {children}
    </span>
  );
}

export default function About() {
  const about = useJSON<AboutData>("about.json");
  return (
    <div className="mx-auto max-w-[1100px] px-4 py-10 sm:px-6">
      <Label>how it works</Label>
      <h1 className="font-serif text-[2.6rem] font-medium leading-tight">About Crux Lab</h1>
      <p className="measure mt-3 text-[1.12rem] leading-relaxed">
        In philosophy, the debate is the experiment. Crux Lab reads recent papers, reconstructs one argument from each
        with verbatim quotes, and then runs adversarial trials against its premises. Agents that never see the literature
        draft objections; two defenders who do see it reply; a referee labels the dialectical outcome. A plain-code
        Director decides which objection to try next, and what survives becomes a research brief for a human
        philosopher.
      </p>

      <div className="mt-10 space-y-12">
        <DataState load={about} what="about.json">
          {(a) => <Diversity a={a} />}
        </DataState>

        <Marginal label="the loop">
          <div className="grid items-center gap-8 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            <LoopRing className="w-full max-w-[420px]" />
            <ol className="space-y-2">
              {STAGES.map((s, i) => (
                <li key={s.name} className="grid grid-cols-[1.6rem_minmax(0,1fr)]">
                  <span className="font-mono text-[0.78rem] text-ink-faint">{i + 1}</span>
                  <span>
                    <span className="font-medium">{s.name}</span> — <span className="text-ink-soft">{s.note}</span>
                  </span>
                </li>
              ))}
            </ol>
          </div>
        </Marginal>

        <Marginal label="the agents">
          <p className="measure mb-4 text-[0.98rem] text-ink-soft">
            The agents are plain model calls made by the lab’s own Python code. They have no tools, no shell and no
            network access. Each constraint below is enforced in code, not only asked for in a prompt.
          </p>
          <dl className="space-y-3">
            {AGENTS.map((g) => (
              <div key={g.name} className="grid gap-x-6 border-t border-rule pt-2.5 md:grid-cols-[14rem_minmax(0,1fr)]">
                <dt className="font-medium">{g.name}</dt>
                <dd className="text-[0.98rem]">{g.constraint}</dd>
              </div>
            ))}
          </dl>
        </Marginal>

        <Marginal label="outcomes">
          <dl className="space-y-2.5">
            {(Object.keys(OUTCOME_COLORS) as Outcome[]).map((o) => (
              <div key={o} className="grid items-baseline gap-x-6 md:grid-cols-[14rem_minmax(0,1fr)]">
                <dt>
                  <OutcomeChip outcome={o} />
                </dt>
                <dd>{OUTCOME_MEANING[o]}</dd>
              </div>
            ))}
          </dl>
          <p className="measure mt-4 text-[0.95rem] text-ink-soft">
            An objection keeps the outcome most favourable to the original argument across both defenders: it has to
            survive both. Outcomes describe the state of the debate, not whether the argument’s conclusion is true.
          </p>
        </Marginal>

        <DataState load={about} what="about.json">
          {(a) => <Wiring a={a} />}
        </DataState>

        {about.status === "ready" && about.data.method_notes?.length ? (
          <Marginal label="how the lab keeps itself honest">
            <ul className="measure space-y-2">
              {about.data.method_notes.map((n, i) => (
                <li key={i} className="grid grid-cols-[1.4rem_minmax(0,1fr)]">
                  <span aria-hidden className="text-ink-faint">—</span>
                  <span>{n}</span>
                </li>
              ))}
            </ul>
          </Marginal>
        ) : null}

        <Marginal label="honest limits">
          <ul className="measure list-disc space-y-1.5 pl-5">
            <li>Novelty scores measure distance from what this lab’s corpus and one live OpenAlex search contain. They are not a claim that a move is new to the literature.</li>
            <li>Every judgment here (objections, replies, labels, prior-art verdicts) is a model output. Model judges are noisy; read the transcripts.</li>
            <li>Quotes are checked against source text by fuzzy matching, which catches fabrication but not every misattribution of emphasis.</li>
            <li>With fewer model families than roles, defenders and referee may share a family; the diversity status above says how many families ran.</li>
            <li>Further human review is required for every research direction on this site.</li>
          </ul>
        </Marginal>
      </div>
    </div>
  );
}

function Diversity({ a }: { a: AboutData }) {
  return (
    <section className="border-y-2 border-ink py-5" aria-labelledby="div-h">
      <div className="flex flex-wrap items-baseline justify-between gap-4">
        <div>
          <Label>model diversity in this build</Label>
          <p id="div-h" className="font-serif text-[2rem] font-medium leading-tight">
            {a.diversity ?? "not recorded"}
          </p>
        </div>
        <p className="font-mono text-[0.8rem]">families: {a.families?.length ? a.families.join(", ") : "none recorded"}</p>
      </div>
      <p className="measure mt-2 text-[0.95rem] text-ink-soft">
        The design calls for Defender A, Defender B and the Referee to come from three different model families, so that
        no single family both argues and judges. When fewer families are available the lab runs anyway and says so here.
      </p>
    </section>
  );
}

type RoleSpec = { provider?: string; model?: string; family?: string };

function Wiring({ a }: { a: AboutData }) {
  const providers = [...new Set((a.models ?? []).filter((m) => m.ok).map((m) => m.provider))];
  const dbModels = (a.models ?? []).filter((m) => m.ok && /databricks/i.test(m.provider));
  const embedder = typeof a.map_stats?.embedder === "string" ? (a.map_stats.embedder as string) : null;
  const dbEmbed = embedder ? /databricks/i.test(embedder) : false;
  const extra = (a as unknown as Record<string, unknown>).databricks;
  const roles = Object.entries(a.roles ?? {});
  return (
    <>
      <Marginal label="who played which role">
        {roles.length ? (
          <dl className="space-y-2">
            {roles.map(([role, spec]) => {
              const list: RoleSpec[] = Array.isArray(spec) ? (spec as RoleSpec[]) : [spec as RoleSpec];
              return (
                <div key={role} className="grid gap-x-6 border-t border-rule pt-2 md:grid-cols-[14rem_minmax(0,1fr)]">
                  <dt>{agentLabel(role)}</dt>
                  <dd className="flex flex-wrap gap-1.5">
                    {list.map((s, i) => (
                      <span key={i} className="inline-flex items-center gap-1">
                        <ModelBadge family={s?.family} model={s?.model} />
                        {s?.provider ? <span className="font-mono text-[0.66rem] text-ink-faint">via {s.provider}</span> : null}
                      </span>
                    ))}
                  </dd>
                </div>
              );
            })}
          </dl>
        ) : (
          <p className="text-ink-soft">No role assignment was exported.</p>
        )}
        {a.models?.length ? (
          <details className="mt-4">
            <summary className="cursor-pointer text-[0.92rem] text-ink-soft">All {a.models.length} candidate models probed</summary>
            <table className="table mt-2">
              <thead>
                <tr>
                  <th>provider</th>
                  <th>family</th>
                  <th>model</th>
                  <th>probe</th>
                </tr>
              </thead>
              <tbody>
                {a.models.map((m, i) => (
                  <tr key={i}>
                    <td className="font-mono text-[0.78rem]">{m.provider}</td>
                    <td className="font-mono text-[0.78rem]">{m.family}</td>
                    <td className="font-mono text-[0.78rem]">{m.model}</td>
                    <td className="font-mono text-[0.78rem]">{m.ok ? "ok" : "failed"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        ) : null}
      </Marginal>

      <Marginal label="Databricks">
        <p className="measure mb-4 text-[0.98rem] text-ink-soft">
          The sponsor’s platform is wired in as an option, never a dependency: the local index stays the source of truth.
          What this build actually used, read from the exported provider list:
        </p>
        <dl className="space-y-3">
          <div className="grid gap-x-6 border-t border-rule pt-2.5 md:grid-cols-[14rem_minmax(0,1fr)]">
            <dt className="font-medium">Model Serving / Foundation Model APIs</dt>
            <dd className="space-y-1">
              <Status on={dbModels.length > 0}>{dbModels.length ? "used in this build" : "not configured for this run"}</Status>
              <p className="text-[0.95rem]">
                {dbModels.length
                  ? `Agents ran on Databricks serving endpoints: ${dbModels.map((m) => m.model).join(", ")}.`
                  : `Databricks serving was not configured for this run. Agents ran via: ${providers.join(", ") || "no provider recorded"}.`}
              </p>
            </dd>
          </div>
          <div className="grid gap-x-6 border-t border-rule pt-2.5 md:grid-cols-[14rem_minmax(0,1fr)]">
            <dt className="font-medium">AI Search (formerly Vector Search)</dt>
            <dd className="space-y-1">
              <Status on={dbEmbed}>{dbEmbed ? "Databricks embeddings used" : "local index used"}</Status>
              <p className="text-[0.95rem]">
                Designed as a Delta Sync index over a <span className="font-mono text-[0.85rem]">claims</span> Delta table.
                {embedder ? ` This build embedded claims with: ${embedder}.` : " No embedder was recorded in the export."}
              </p>
            </dd>
          </div>
          <div className="grid gap-x-6 border-t border-rule pt-2.5 md:grid-cols-[14rem_minmax(0,1fr)]">
            <dt className="font-medium">MLflow tracing</dt>
            <dd className="space-y-1">
              {a.tracing ? (
                <>
                  <Status on={/databricks/i.test(a.tracing.backend) ? true : null}>
                    {/databricks/i.test(a.tracing.backend) ? "Databricks experiment" : "traced locally"}
                  </Status>
                  <p className="text-[0.95rem]">
                    MLflow tracing:{" "}
                    {a.tracing.traces === null ? "trace count not recorded" : `${a.tracing.traces} LLM calls traced`}, backend:{" "}
                    {a.tracing.backend}.
                  </p>
                </>
              ) : (
                <>
                  <Status on={null}>not recorded</Status>
                  <p className="text-[0.95rem]">Every model call is traced with MLflow; this export does not say where the traces went.</p>
                </>
              )}
            </dd>
          </div>
          <div className="grid gap-x-6 border-t border-rule pt-2.5 md:grid-cols-[14rem_minmax(0,1fr)]">
            <dt className="font-medium">Databricks App</dt>
            <dd className="text-[0.95rem]">Optional packaging of the live API; this site is a static replay and does not depend on it.</dd>
          </div>
        </dl>
        {extra ? (
          <div className="mt-4">
            <div className="smallcaps mb-1 text-ink-soft">exported Databricks status</div>
            <KV value={extra} />
          </div>
        ) : null}
      </Marginal>

      <Marginal label="corpus and map">
        <dl className="flex flex-wrap gap-x-10 gap-y-3">
          {Object.entries(a.corpus ?? {}).map(([k, v]) => (
            <div key={k}>
              <dt className="smallcaps text-[0.9rem] text-ink-soft">{k.replace(/_/g, " ")}</dt>
              <dd className="font-serif text-[1.7rem] leading-none">{String(v)}</dd>
            </div>
          ))}
        </dl>
        {typeof a.targets_meta?.note === "string" ? (
          <p className="measure mt-4 text-[0.98rem]">
            <span className="smallcaps mr-1 text-ink-soft">note on targets</span>
            {a.targets_meta.note as string}
          </p>
        ) : null}
        {Object.keys(a.map_stats ?? {}).length ? (
          <details className="mt-4">
            <summary className="cursor-pointer text-[0.92rem] text-ink-soft">Mapping statistics</summary>
            <div className="mt-2">
              <KV value={a.map_stats} />
            </div>
          </details>
        ) : null}
      </Marginal>

      <Marginal label="stack">
        <ul className="measure list-disc space-y-1 pl-5 text-[0.98rem]">
          <li>Python lab: FastAPI with server-sent events for live mode, SQLite store, Pydantic schemas, BM25 plus embeddings for retrieval, MLflow tracing.</li>
          <li>Sources: OpenAlex for metadata and abstracts, open-access PDFs for full texts.</li>
          <li>This site: Vite, React, TypeScript, Tailwind, React Flow for argument maps, Recharts for the results. It replays exported JSON files and needs no server.</li>
        </ul>
      </Marginal>
    </>
  );
}
