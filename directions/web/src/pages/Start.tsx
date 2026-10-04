import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { Code, Label } from "../components/ui";
import { useJSON } from "../lib/data";
import type { TopicConfig, TopicsFile } from "../types";

// "Start a topic": writes config/topics/<slug>.yaml in the browser and lists the commands to run it.
// The public site is a static replay, so the lab itself runs on the researcher's machine.

interface Draft {
  name: string;
  slug: string;
  area: string;
  description: string;
  searches: string; // one phrase per line
  keywords: string; // comma separated, for the on-topic filter
  levels: [string, string, string];
  schools: string; // one per line
  freshFrom: string;
}

const BLANK: Draft = {
  name: "",
  slug: "",
  area: "philosophy of religion",
  description: "",
  searches: "",
  keywords: "",
  levels: ["", "", ""],
  schools: "",
  freshFrom: "2026-08-01",
};

const slugify = (s: string) =>
  s
    .toLowerCase()
    .replace(/^the\s+/, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 40);

const reEscape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

function fromConfig(c: TopicConfig): Draft {
  // unwrap a query that is exactly one quoted phrase; keep queries with operators or inner quotes as written
  const phrases = Object.values(c.queries).map((q) => (/^"[^"]*"$/.test(q) ? q.slice(1, -1) : q));
  return {
    name: c.name,
    slug: c.slug,
    area: c.area,
    description: c.description,
    searches: phrases.join("\n"),
    keywords: c.relevant.split("|").join(", "),
    levels: [c.relevance_levels[1] ?? "", c.relevance_levels[2] ?? "", c.relevance_levels[3] ?? ""],
    schools: c.schools.join("\n"),
    freshFrom: c.fresh_from,
  };
}

const lines = (s: string) =>
  s
    .split("\n")
    .map((x) => x.trim())
    .filter(Boolean);

/** JSON strings and lists are valid YAML, which keeps quoting safe for any input. */
function toYaml(d: Draft): string {
  const j = JSON.stringify;
  const slug = d.slug || slugify(d.name) || "my-topic";
  const searches = lines(d.searches);
  // a phrase that already contains operators or quotes is passed through; otherwise phrase-match it
  const query = (p: string) => (/["()]|\b(AND|OR|NOT)\b/.test(p) ? p : `"${p}"`);
  const keywords = d.keywords
    .split(",")
    .map((k) => k.trim())
    .filter(Boolean);
  const relevant = keywords.length ? keywords.map((k) => (/[|\\.?*]/.test(k) ? k : reEscape(k))).join("|") : ".";
  const levels = ["none", ...d.levels.map((l, i) => l || ["touches the wider area", "concerns closely related arguments", `directly about ${d.name || "the topic"}`][i])];
  const schools = lines(d.schools);
  return [
    `# Crux Lab topic file. Save as config/topics/${slug}.yaml`,
    `slug: ${j(slug)}`,
    `name: ${j(d.name || "My topic")}`,
    `description: ${j(d.description)}`,
    `area: ${j(d.area || "philosophy")}`,
    "# OpenAlex title_and_abstract.search strings (label -> query); quoted = phrase match",
    "queries:",
    ...(searches.length ? searches.map((p) => `  ${j(p.replace(/"/g, ""))}: ${j(query(p))}`) : ['  "my topic": "\\"my topic\\""']),
    `fresh_from: ${j(d.freshFrom || "2026-08-01")}`,
    `fresh_queries: ${j(searches.length ? searches.map(query) : [])}`,
    "# a record is kept only if its title + abstract match this (case-insensitive regular expression)",
    `relevant: ${j(relevant)}`,
    `relevance_levels: ${j(levels)}`,
    "# optional: how many targets of each kind; spread: true takes classic targets from each search in turn",
    "# targets: {fresh: 3, classic: 2, fresh_min_relevance: 0, spread: false}",
    "# optional: a stricter regular expression for recent papers, when a fresh search is broad",
    "# fresh_relevant: \"god\\\\b|theis|religio\"",
    "# traditions the Tradition Lens agent may argue from",
    `schools: ${j(schools.length ? schools : ["naturalism", "classical theism"])}`,
    "",
  ].join("\n");
}

export default function Start() {
  const topics = useJSON<TopicsFile>("topics.json");
  const [params] = useSearchParams();
  const from = params.get("from");
  const [d, setD] = useState<Draft>(BLANK);
  const [copied, setCopied] = useState(false);

  // Prefill from ?from=<slug> once the topic list is in.
  useEffect(() => {
    if (topics.status !== "ready" || !from) return;
    const t = topics.data.topics.find((x) => x.slug === from);
    if (t) setD(fromConfig(t.config));
  }, [topics, from]);

  const yaml = useMemo(() => toYaml(d), [d]);
  const slug = d.slug || slugify(d.name) || "my-topic";
  const set = <K extends keyof Draft>(k: K, v: Draft[K]) => setD((x) => ({ ...x, [k]: v }));

  const download = () => {
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([yaml], { type: "text/yaml" }));
    a.download = `${slug}.yaml`;
    a.click();
    URL.revokeObjectURL(a.href);
  };
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(yaml);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  const templates = topics.status === "ready" ? topics.data.topics : [];
  const field = "mt-1 w-full border border-rule bg-[#1B1F23] px-3 py-2 font-serif text-[1rem] focus:border-ink";

  return (
    <div className="mx-auto max-w-[1200px] px-4 py-10 sm:px-6">
      <Label>for a topic that is not here yet</Label>
      <h1 className="font-serif text-[2.6rem] font-medium leading-tight">Start a topic</h1>
      <p className="measure mt-2 text-[1.05rem] text-ink-soft">
        Say you work on the fine-tuning argument rather than divine hiddenness. Crux Lab can do for your topic what it
        did here: gather the literature, pick recent papers that argue for something, attack and defend their
        arguments, and hand you research directions. This site only replays topics that have been run, so the lab
        itself runs on your machine. This page writes the topic file for you; the steps below run it.
      </p>

      <div className="mt-6 flex flex-wrap items-center gap-2">
        <span className="smallcaps mr-1 text-[0.95rem] text-ink-soft">start from</span>
        <button type="button" className="btn btn-quiet" onClick={() => setD(BLANK)}>
          blank
        </button>
        {templates.map((t) => (
          <button key={t.slug} type="button" className="btn btn-quiet" onClick={() => setD(fromConfig(t.config))}>
            {t.name}
          </button>
        ))}
      </div>

      <div className="mt-6 grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <form className="space-y-4" onSubmit={(e) => e.preventDefault()} aria-label="Topic definition">
          <label className="block">
            <span className="font-medium">Topic name</span>
            <input className={field} value={d.name} placeholder="The fine-tuning argument"
              onChange={(e) => setD((x) => ({ ...x, name: e.target.value, slug: x.slug && x.slug !== slugify(x.name) ? x.slug : slugify(e.target.value) }))} />
          </label>
          <label className="block">
            <span className="font-medium">Short id</span> <span className="text-[0.88rem] text-ink-soft">(used in file names and commands)</span>
            <input className={`${field} font-mono text-[0.9rem]`} value={d.slug} placeholder="fine-tuning" onChange={(e) => set("slug", slugify(e.target.value))} />
          </label>
          <label className="block">
            <span className="font-medium">Area</span>
            <input className={field} value={d.area} placeholder="philosophy of religion and philosophy of physics" onChange={(e) => set("area", e.target.value)} />
          </label>
          <label className="block">
            <span className="font-medium">What the topic covers</span>
            <textarea className={field} rows={3} value={d.description}
              placeholder="Arguments from the apparent fine-tuning of physical constants to a designer, and the replies: the multiverse, observation selection, the normalizability problem."
              onChange={(e) => set("description", e.target.value)} />
          </label>
          <label className="block">
            <span className="font-medium">Search phrases</span> <span className="text-[0.88rem] text-ink-soft">(one per line; each finds papers whose title or abstract contains it)</span>
            <textarea className={`${field} font-mono text-[0.85rem]`} rows={5} value={d.searches}
              placeholder={"fine-tuning argument\nanthropic principle\nmultiverse AND \"fine-tuning\""}
              onChange={(e) => set("searches", e.target.value)} />
          </label>
          <label className="block">
            <span className="font-medium">On-topic keywords</span> <span className="text-[0.88rem] text-ink-soft">(comma separated; a paper is kept if its title or abstract contains one)</span>
            <input className={`${field} font-mono text-[0.85rem]`} value={d.keywords} placeholder="fine-tun, design, anthropic, multiverse, constants"
              onChange={(e) => set("keywords", e.target.value)} />
          </label>
          <fieldset>
            <legend className="font-medium">How closely a paper must engage the topic</legend>
            <p className="text-[0.88rem] text-ink-soft">Used to rank candidate papers; 0 means unrelated.</p>
            {d.levels.map((l, i) => (
              <label key={i} className="mt-1 flex items-center gap-2">
                <span className="w-5 font-mono text-[0.85rem] text-ink-soft">{i + 1}</span>
                <input className={field} value={l}
                  placeholder={["touches the wider area", "concerns closely related arguments", "directly about the topic"][i]}
                  onChange={(e) => set("levels", d.levels.map((x, j) => (j === i ? e.target.value : x)) as Draft["levels"])} />
              </label>
            ))}
          </fieldset>
          <label className="block">
            <span className="font-medium">Traditions that should press objections</span> <span className="text-[0.88rem] text-ink-soft">(one per line)</span>
            <textarea className={field} rows={4} value={d.schools} placeholder={"Bayesian confirmation theory\nmultiverse naturalism\nclassical theism"}
              onChange={(e) => set("schools", e.target.value)} />
          </label>
          <label className="block">
            <span className="font-medium">“Fresh” means published on or after</span>
            <input type="date" className={`${field} font-mono text-[0.9rem]`} value={d.freshFrom} onChange={(e) => set("freshFrom", e.target.value)} />
          </label>
        </form>

        <div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <Label>your topic file</Label>
            <div className="flex gap-2">
              <button type="button" className="btn btn-quiet" onClick={copy}>{copied ? "Copied" : "Copy"}</button>
              <button type="button" className="btn btn-quiet" onClick={download}>Download {slug}.yaml</button>
            </div>
          </div>
          <pre tabIndex={0} className="mt-2 max-h-[30rem] overflow-auto border border-rule bg-paper-deep p-3 font-mono text-[0.76rem] leading-relaxed">
            {yaml}
          </pre>

          <h2 className="mt-8 font-serif text-[1.5rem] font-medium">Run it</h2>
          <ol className="mt-2 list-decimal space-y-3 pl-5 text-[0.97rem]">
            <li>
              Get the lab:
              <pre tabIndex={0} className="mt-1 overflow-x-auto border border-rule bg-paper-deep p-2 font-mono text-[0.76rem]">
                {"git clone https://github.com/univerdread/crux-lab.git\ncd crux-lab\nmake setup"}
              </pre>
            </li>
            <li>
              Give it a model: put one provider in <Code>.env</Code> (an evroc Think key gives eight open-model families; a
              Databricks workspace token, an OpenRouter key or an Anthropic key also work, as does a logged-in{" "}
              <Code>claude</Code> or <Code>codex</Code> command-line tool), then run <Code>make providers</Code>. More model
              families make the debate better: Defender A, Defender B and the Referee then come from three different ones.
            </li>
            <li>
              Save the file above as <Code>config/topics/{slug}.yaml</Code>.
            </li>
            <li>
              Run the lab on the topic, step by step:
              <pre tabIndex={0} className="mt-1 overflow-x-auto border border-rule bg-paper-deep p-2 font-mono text-[0.76rem]">
                {[`make corpus TOPIC=${slug}     # literature from OpenAlex + open-access full texts`,
                  `make targets TOPIC=${slug}    # pick papers that argue for a thesis`,
                  `make map TOPIC=${slug}        # extract claims and arguments`,
                  `make runs TOPIC=${slug}       # objections, prior-art checks, trials, briefs`,
                  `make assess TOPIC=${slug}     # a referee-style quality grade for every direction`,
                  `make revise TOPIC=${slug}     # each direction answers its strongest objection, re-graded`,
                  `make export TOPIC=${slug}`,
                  "make demo                       # open the site, then Topics → your topic"].join("\n")}
              </pre>
            </li>
            <li>
              Check the papers it picked (<Code>data/topics/{slug}/targets.json</Code>) before the long steps. You can
              also add an argument of your own: write its premises and conclusion in plain English in{" "}
              <Code>data/topics/{slug}/manual_targets/&lt;name&gt;.md</Code> and rerun <Code>make targets</Code>.
            </li>
          </ol>
          <p className="measure mt-4 text-[0.9rem] text-ink-soft">
            What to expect: OpenAlex’s free tier allows about a hundred searches a day, enough for one topic (set{" "}
            <Code>max_per_query: 200</Code> to use one search per query). The divine-hiddenness build made about 1,400
            model calls for five papers including its evaluations. The second topic, decision theory in philosophy of
            religion, was run end to end with exactly these steps in about 45 minutes: roughly $4.70 of evroc usage and
            about 120 Claude calls for six papers. Every call is cached, so a rerun only pays for what changed. If a
            step fails, the README describes each one.
          </p>
          <p className="mt-3">
            <Link to="/topics" className="link">← All topics</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
