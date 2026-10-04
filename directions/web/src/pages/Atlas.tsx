import { useDeferredValue, useMemo, useState, type FormEvent } from "react";
import { ArgumentMap } from "../components/ArgumentMap";
import { useDrawer } from "../components/drawer";
import { DataState, Disclaimer, Empty, Label } from "../components/ui";
import { API_URL, livePriorArt, type PriorArtHit } from "../lib/api";
import { BM25 } from "../lib/bm25";
import { useJSON } from "../lib/data";
import { excerpt, num } from "../lib/format";
import { recordFor } from "../lib/ids";
import type { Claim, ClaimsFile, TitleRecord } from "../types";

export default function Atlas() {
  const claims = useJSON<ClaimsFile>("claims.json");
  const records = useJSON<Record<string, TitleRecord>>("titles.json");
  const recs = records.status === "ready" ? records.data : undefined;
  return (
    <div className="mx-auto max-w-[1300px] px-4 py-10 sm:px-6">
      <Label>the corpus, mapped</Label>
      <h1 className="font-serif text-[2.6rem] font-medium leading-tight">Atlas</h1>
      <p className="measure mt-2 text-[1.05rem] text-ink-soft">
        Every claim the Extractor kept, each with a verbatim quote found in its source. Use the box below to check
        whether a move you have in mind already appears in what the lab has read.
      </p>
      <div className="mt-8">
        <DataState load={claims} what="the claim graph">
          {(f) => <AtlasView file={f} records={recs} />}
        </DataState>
      </div>
    </div>
  );
}

function AtlasView({ file, records }: { file: ClaimsFile; records?: Record<string, TitleRecord> }) {
  const byId = useMemo(() => Object.fromEntries(file.claims.map((c) => [c.id, c])) as Record<string, Claim>, [file]);
  const papers = useMemo(() => new Set(file.claims.map((c) => c.paper_id)).size, [file]);
  const relCounts = useMemo(() => {
    const m: Record<string, number> = {};
    for (const e of file.edges ?? []) m[e.relation] = (m[e.relation] ?? 0) + 1;
    return m;
  }, [file]);
  return (
    <div className="space-y-14">
      <dl className="flex flex-wrap gap-x-10 gap-y-3 border-y border-ink py-3">
        {[
          ["claims", file.claims.length],
          ["papers with claims", papers],
          ["arguments", file.arguments?.length ?? 0],
          ...Object.entries(relCounts).map(([k, v]) => [`${k} edges`, v] as [string, number]),
        ].map(([k, v]) => (
          <div key={String(k)}>
            <dt className="smallcaps text-[0.9rem] text-ink-soft">{k}</dt>
            <dd className="font-serif text-[1.7rem] leading-none">{v}</dd>
          </div>
        ))}
      </dl>
      <MoveSearch claims={file.claims} records={records} />
      <ArgumentsSection file={file} byId={byId} />
      <ClaimList claims={file.claims} records={records} />
    </div>
  );
}

/* ───────────── Has this move been made? ───────────── */

interface Hit {
  claim?: Claim;
  id: string;
  text: string;
  score: number;
  paperId?: string;
  title?: string;
}

function MoveSearch({ claims, records }: { claims: Claim[]; records?: Record<string, TitleRecord> }) {
  const { openClaim } = useDrawer();
  const [q, setQ] = useState("");
  const [mode, setMode] = useState<"local" | "live">("local");
  const [res, setRes] = useState<{ q: string; hits: Hit[]; searched: number; mode: string } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const index = useMemo(() => new BM25(claims.map((c) => `${c.text} ${c.quote ?? ""}`)), [claims]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const query = q.trim();
    if (query.length < 3) return;
    setErr(null);
    if (mode === "live" && API_URL) {
      setBusy(true);
      try {
        const r = await livePriorArt(query);
        setRes({
          q: query,
          searched: r.records_searched,
          mode: "live index (BM25 + embeddings)",
          hits: r.hits.map((h: PriorArtHit) => ({
            id: h.claim_id,
            text: h.text,
            score: h.score,
            paperId: typeof h.paper_id === "string" ? h.paper_id : undefined,
            title: typeof h.title === "string" ? h.title : undefined,
            claim: claims.find((c) => c.id === h.claim_id),
          })),
        });
      } catch (x) {
        setErr(String(x));
      } finally {
        setBusy(false);
      }
      return;
    }
    // One hit per work: OpenAlex lists some papers more than once, and those copies share `work`.
    const seen = new Set<string>();
    const hits: Hit[] = [];
    for (const h of index.search(query, 60)) {
      const c = claims[h.index];
      const w = c.work ?? c.paper_id;
      if (seen.has(w)) continue;
      seen.add(w);
      hits.push({ id: c.id, text: c.text, score: h.score, paperId: c.paper_id, claim: c });
      if (hits.length === 10) break;
    }
    setRes({ q: query, hits, searched: index.size, mode: "BM25 over exported claims" });
  };

  return (
    <section aria-labelledby="move-h" className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
      <div>
        <Label>prior-art check, by hand</Label>
        <h2 id="move-h" className="font-serif text-[1.9rem] font-medium leading-tight">
          Has this move been made?
        </h2>
        <p className="measure mt-2 text-[0.98rem] text-ink-soft">
          Describe the objection or reply you have in mind in a sentence or two. The lab returns the closest claims it
          has extracted, with their papers.{" "}
          {API_URL
            ? "Live mode asks the lab’s own hybrid index; local mode runs keyword retrieval (BM25) in your browser."
            : "This static site runs keyword retrieval (BM25) over the exported claims in your browser."}{" "}
          A match is a lead to read, not a verdict on sameness.
        </p>
        <form onSubmit={submit} className="mt-4 space-y-3">
          <label htmlFor="move-q" className="sr-only">
            Describe the move
          </label>
          <textarea
            id="move-q"
            className="field min-h-[7rem] w-full text-[1rem]"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Describe the objection or reply in your own words…"
          />
          <div className="flex flex-wrap items-center gap-3">
            <button type="submit" className="btn" disabled={busy || q.trim().length < 3}>
              {busy ? "Searching…" : "Search the corpus"}
            </button>
            {API_URL ? (
              <div role="group" aria-label="Search mode" className="flex gap-1.5">
                <button type="button" className="btn btn-quiet" aria-pressed={mode === "local"} onClick={() => setMode("local")}>
                  local BM25
                </button>
                <button type="button" className="btn btn-quiet" aria-pressed={mode === "live"} onClick={() => setMode("live")}>
                  live index
                </button>
              </div>
            ) : null}
          </div>
        </form>
      </div>
      <div aria-live="polite">
        {err ? <Empty>The search failed: {err}</Empty> : null}
        {res ? (
          <div>
            <p className="font-mono text-[0.72rem] text-ink-soft">
              {res.hits.length} closest of {res.searched} claims searched · {res.mode}
            </p>
            {res.hits.length ? (
              <ol className="mt-2">
                {res.hits.map((h, i) => {
                  const rec = recordFor(h.paperId ?? h.id, records);
                  return (
                    <li key={`${h.id}-${i}`} className="border-t border-rule py-3">
                      <div className="flex flex-wrap items-center gap-2 font-mono text-[0.7rem] text-ink-soft">
                        <span>#{i + 1}</span>
                        <span>score {num(h.score)}</span>
                        {h.claim ? <span>· {h.claim.kind}</span> : null}
                        <button type="button" className="link text-ink" onClick={() => openClaim(h.id, h.claim)}>
                          {h.id}
                        </button>
                      </div>
                      <p className="mt-1 text-[1rem] leading-snug">{h.text}</p>
                      <p className="mt-0.5 text-[0.88rem] text-ink-soft">
                        {rec ? (
                          <>
                            <cite className="not-italic">{rec.title}</cite>
                            {rec.year ? ` (${rec.year})` : ""}
                          </>
                        ) : (
                          h.title ?? h.paperId ?? ""
                        )}
                      </p>
                    </li>
                  );
                })}
              </ol>
            ) : (
              <Empty>No claim shares enough vocabulary with that description. Try the terms a paper would use.</Empty>
            )}
            <Disclaimer className="mt-4" />
          </div>
        ) : (
          <div className="flex h-full min-h-[10rem] items-center justify-center border border-dashed border-rule px-6 text-center text-[0.95rem] text-ink-soft">
            Results appear here, with the quote and record behind each claim one click away.
          </div>
        )}
      </div>
    </section>
  );
}

/* ───────────── argument graphs (one at a time) ───────────── */

function ArgumentsSection({ file, byId }: { file: ClaimsFile; byId: Record<string, Claim> }) {
  const args = file.arguments ?? [];
  const [sel, setSel] = useState(0);
  if (!args.length)
    return (
      <section>
        <Label>arguments</Label>
        <Empty>No arguments were mapped.</Empty>
      </section>
    );
  const a = args[Math.min(sel, args.length - 1)];
  return (
    <section aria-labelledby="args-h">
      <Label>reconstructed arguments</Label>
      <h2 id="args-h" className="font-serif text-[1.9rem] font-medium leading-tight">
        Argument graphs
      </h2>
      <div className="mt-3 flex flex-wrap gap-2" role="tablist" aria-label="Arguments">
        {args.map((x, i) => (
          <button
            key={x.id}
            role="tab"
            aria-selected={i === sel}
            className="btn btn-quiet max-w-[22rem] truncate"
            onClick={() => setSel(i)}
            title={x.title}
          >
            {x.title || x.id}
          </button>
        ))}
      </div>
      <div className="mt-4" role="tabpanel">
        <ArgumentMap argument={a} claims={byId} height={460} maxCols={5} />
        <p className="mt-2 font-mono text-[0.75rem]">
          {a.skeleton} · {a.valid === true ? "valid" : a.valid === false ? "invalid as stated" : "validity not determined"}
          {a.missing_premise ? " · dashed node: the Formalizer’s hidden premise" : ""}
        </p>
      </div>
    </section>
  );
}

/* ───────────── searchable claim list ───────────── */

const PAGE = 60;

function ClaimList({ claims, records }: { claims: Claim[]; records?: Record<string, TitleRecord> }) {
  const { openClaim } = useDrawer();
  const [text, setText] = useState("");
  const [kind, setKind] = useState("all");
  const [level, setLevel] = useState("all");
  const [limit, setLimit] = useState(PAGE);
  const dq = useDeferredValue(text.trim().toLowerCase());
  const kinds = useMemo(() => [...new Set(claims.map((c) => c.kind))].sort(), [claims]);
  const levels = useMemo(() => [...new Set(claims.map((c) => c.level))].sort(), [claims]);
  const filtered = useMemo(
    () =>
      claims.filter(
        (c) =>
          (kind === "all" || c.kind === kind) &&
          (level === "all" || c.level === level) &&
          (!dq || c.text.toLowerCase().includes(dq) || c.id.toLowerCase().includes(dq) || (c.quote ?? "").toLowerCase().includes(dq)),
      ),
    [claims, kind, level, dq],
  );
  return (
    <section aria-labelledby="claims-h">
      <Label>every kept claim</Label>
      <h2 id="claims-h" className="font-serif text-[1.9rem] font-medium leading-tight">
        Claim index
      </h2>
      <div className="mt-3 flex flex-wrap items-end gap-3">
        <label className="flex flex-col text-[0.85rem] text-ink-soft">
          filter text
          <input className="field mt-1 w-[18rem] max-w-full" value={text} onChange={(e) => { setText(e.target.value); setLimit(PAGE); }} />
        </label>
        <label className="flex flex-col text-[0.85rem] text-ink-soft">
          kind
          <select className="field mt-1" value={kind} onChange={(e) => { setKind(e.target.value); setLimit(PAGE); }}>
            <option value="all">all</option>
            {kinds.map((k) => (
              <option key={k}>{k}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col text-[0.85rem] text-ink-soft">
          source
          <select className="field mt-1" value={level} onChange={(e) => { setLevel(e.target.value); setLimit(PAGE); }}>
            <option value="all">all</option>
            {levels.map((k) => (
              <option key={k}>{k}</option>
            ))}
          </select>
        </label>
        <span className="pb-2 font-mono text-[0.72rem] text-ink-soft">
          {filtered.length} of {claims.length}
        </span>
      </div>
      {filtered.length ? (
        <ul className="mt-4">
          {filtered.slice(0, limit).map((c) => {
            const rec = recordFor(c.paper_id, records);
            return (
              <li key={c.id} className="grid gap-x-4 border-t border-rule py-2.5 md:grid-cols-[11rem_minmax(0,1fr)]">
                <div className="font-mono text-[0.7rem] text-ink-soft">
                  <button type="button" className="link text-ink" onClick={() => openClaim(c.id, c)}>
                    {c.id}
                  </button>
                  <div>
                    {c.kind} · {c.level}
                  </div>
                </div>
                <div>
                  <p className="text-[0.98rem] leading-snug">{c.text}</p>
                  <p className="text-[0.85rem] text-ink-soft">{rec ? excerpt(rec.title, 120) : c.paper_id}</p>
                </div>
              </li>
            );
          })}
        </ul>
      ) : (
        <Empty>No claim matches these filters.</Empty>
      )}
      {filtered.length > limit ? (
        <button className="btn btn-quiet mt-4" onClick={() => setLimit(limit + PAGE * 2)}>
          Show more ({filtered.length - limit} left)
        </button>
      ) : null}
    </section>
  );
}
