"""E1 prior-art recall: can the lab find the paper that made a move, from a reworded version?

50 objection-like claims from corpus abstracts are reworded by an LLM with names and jargon removed,
then searched 4 ways. Metric: recall@5 of the source paper per method."""
from __future__ import annotations

import asyncio
import random

from pydantic import BaseModel

from crux_lab.agents.roles import render
from crux_lab.config import TOPIC
from crux_lab.graph.index import INDEX_DIR, HybridIndex
from crux_lab.graph.schema import Claim
from crux_lab.graph.store import Store
from crux_lab.eval.common import model_ids, stamp, write
from crux_lab.lab.novelty import Restatements, RerankOut
from crux_lab.llm.client import LLMClient

N = 50


class Reworded(BaseModel):
    reworded: str


def pick_items(store: Store, n: int = N, seed: int = 7) -> list[Claim]:
    claims = [c for c in store.all(Claim) if c.level == "abstract"]
    pref = [c for c in claims if c.kind == "objection"]
    rest = [c for c in claims if c.kind in ("conclusion", "reply") and c.paper_id not in {p.paper_id for p in pref}]
    rng = random.Random(seed)
    rng.shuffle(pref)
    rng.shuffle(rest)
    out, seen = [], set()
    for c in pref + rest:
        if c.paper_id in seen:
            continue
        seen.add(c.paper_id)
        out.append(c)
        if len(out) == n:
            break
    return out


def papers_from_hits(hits, to_paper) -> list[str]:
    out = []
    for h in hits:
        p = to_paper(h)
        if p and p not in out:
            out.append(p)
    return out


async def method4(client: LLMClient, q: str, claims_ix: HybridIndex, abstracts_ix: HybridIndex) -> list[str]:
    """claims + 3-way restatement + rerank (the lab's novelty pipeline, without live OpenAlex)."""
    system, user = render("restate", argument="(unknown argument)", target="(unknown premise)", objection=q)
    rs, _ = await client.json("reranker", user, Restatements, system)
    queries = [q] + ([rs.paper_vocabulary, rs.plain_english, rs.neighboring_tradition] if rs else [])
    fused: dict[str, float] = {}
    text: dict[str, str] = {}
    for qq in queries:
        for rank, h in enumerate(claims_ix.search(qq, k=20)):
            pid = h.meta.get("paper_id")
            fused[pid] = fused.get(pid, 0) + 1 / (60 + rank)
            text.setdefault(pid, f"{h.meta.get('title', '')}: {h.text}")
    cands = sorted(fused, key=lambda p: -fused[p])[:12]
    listing = "\n\n".join(f"[{i + 1}] {text[p]}" for i, p in enumerate(cands))
    system, user = render("rerank", target_id="(unknown)", target_text="(the premise this move attacks)",
                          objection=q, passages=listing)
    out, _ = await client.json("reranker", user, RerankOut, system, max_tokens=3000)
    if not out:
        return cands
    score = {cands[j.n - 1]: j.similarity for j in out.judgments if 1 <= j.n <= len(cands)}
    return sorted(cands, key=lambda p: (-score.get(p, 0), -fused[p]))


async def run(client: LLMClient | None = None, n: int = N) -> dict:
    client = client or LLMClient()
    store = Store()
    claims_ix = HybridIndex.load(INDEX_DIR / "claims")
    abstracts_ix = HybridIndex.load(INDEX_DIR / "abstracts", embedder=claims_ix.embedder)
    items = pick_items(store, n)

    async def reword(c: Claim):
        system, user = render("eval_reword", claim=c.text)
        r, _ = await client.json("reranker", user, Reworded, system)
        return r.reworded if r else None

    reworded = await asyncio.gather(*[reword(c) for c in items])
    pairs = [(c, q) for c, q in zip(items, reworded) if q]
    m4 = await asyncio.gather(*[method4(client, q, claims_ix, abstracts_ix) for _, q in pairs])
    # Duplicate records of one work (Zenodo/figshare versions etc.) count as the same paper: rank works,
    # not records. The strict record-level score is kept alongside for transparency.
    from crux_lab.corpus.build import load_corpus
    from crux_lab.corpus.dedup import work_ids
    wid = work_ids(load_corpus())

    def top_works(ranked: list[str], k: int = 5) -> list[str]:
        out: list[str] = []
        for pid in ranked:
            w = wid.get(pid, pid)
            if w not in out:
                out.append(w)
            if len(out) == k:
                break
        return out
    methods = {"BM25 over abstracts": [], "embeddings over abstracts": [], "embeddings over claims": [],
               "claims + 3-way restatement + rerank": []}
    rows = []
    strict_methods = {k: [] for k in methods}
    for (c, q), r4 in zip(pairs, m4):
        r1 = [h.id for h in abstracts_ix.bm25_search(q, k=30)]
        r2 = [h.id for h in abstracts_ix.dense_search(q, k=30)]
        r3 = papers_from_hits(claims_ix.dense_search(q, k=60), lambda h: h.meta.get("paper_id"))
        hits, strict_hits = {}, {}
        for name, ranked in zip(methods, (r1, r2, r3, r4)):
            ok = wid.get(c.paper_id, c.paper_id) in top_works(ranked)
            methods[name].append(ok)
            hits[name] = ok
            strict = c.paper_id in ranked[:5]
            strict_methods[name].append(strict)
            strict_hits[name] = strict
        rows.append({"claim_id": c.id, "paper_id": c.paper_id, "original": c.text, "reworded": q, "hit": hits,
                     "hit_strict_record": strict_hits})
    n_ok = len(pairs)
    data = {
        "experiment": "E1 prior-art recall", "n": n_ok,
        "methods": [{"name": k, "recall_at_5": round(sum(v) / max(1, n_ok), 3), "hits": sum(v),
                     "recall_at_5_strict_record": round(sum(strict_methods[k]) / max(1, n_ok), 3)}
                    for k, v in methods.items()],
        "unit": "work (duplicate records of one paper merged by title + first author)",
        "settings": {"items": "objection-like claims extracted from corpus abstracts (kind objection first, then conclusion/reply), one per paper, seed 7",
                     "rewording": "LLM removes names and jargon", "k": 5,
                     "claims_indexed": len(claims_ix), "abstracts_indexed": len(abstracts_ix),
                     "embedder": claims_ix.embedder.name},
        "models": model_ids(client, ["reranker"]), "timestamp": stamp(), "items": rows,
        "limits": ("The query is a reworded version of a claim the Extractor took from the source paper's abstract, "
                   "and that claim is itself in the claims index, so this measures recovery of a known move under "
                   "paraphrase, not discovery of unknown prior art. Items come from the whole corpus of the topic "
                   f"({TOPIC.get('name', 'the topic')}: its searches plus recent work in the area), not only from papers "
                   "directly on it. Corpus: OpenAlex abstracts only (no PhilArchive). "
                   "One rewording per item; no human labels. Recall is scored per work: OpenAlex lists many papers "
                   "more than once (versions), so duplicate records are merged (title + first-author surname) before "
                   "taking the top 5; recall_at_5_strict_record gives the stricter record-level score."),
    }
    # Run-to-run variance: dense retrieval (local embeddings on Apple MPS) is not bit-reproducible, so a re-run
    # over the same items can flip near-ties in the top 5. Keep earlier runs' scores instead of overwriting them.
    from crux_lab.config import RESULTS
    import json as _json
    prev_path = RESULTS / "e1.json"
    if prev_path.exists():
        prev = _json.loads(prev_path.read_text())
        if sorted(r["claim_id"] for r in prev.get("items", [])) == sorted(r["claim_id"] for r in rows):
            data["previous_runs"] = [{**r, "unit": r.get("unit", "record")} for r in prev.get("previous_runs", [])] + [
                {"timestamp": prev.get("timestamp"), "methods": prev.get("methods"), "unit": prev.get("unit", "record")}]
    if data.get("previous_runs"):
        data["limits"] += (" Embedding-based retrieval is not bit-reproducible across runs (local model on Apple MPS): "
                           "previous_runs holds the scores of earlier runs over the same 50 items and the same cached "
                           "rewordings (each with its scoring unit; compare record-level runs with recall_at_5_strict_record), "
                           "which shows the run-to-run variance.")
    write("e1", data)
    return data
