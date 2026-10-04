"""`make map`: target papers -> claims -> arguments -> skeletons; abstract claims for the corpus;
then the BM25 + embedding indexes over claims and over abstracts."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from crux_lab.config import MAP_STATS, ROOT
from crux_lab.corpus.build import load_corpus
from crux_lab.corpus.targets import load_targets
from crux_lab.graph.extract import (ExtractStats, abstract_claims, extract_paper_claims,
                                    reconstruct_arguments)
from crux_lab.graph.formalize import formalize
from crux_lab.graph.index import INDEX_DIR, Embedder, HybridIndex
from crux_lab.graph.schema import Argument, Claim, Edge, Paper
from crux_lab.graph.store import Store
from crux_lab.llm.client import LLMClient

log = logging.getLogger(__name__)
STATS = MAP_STATS


def target_text(t: dict) -> str:
    return (ROOT / t["text_path"]).read_text("utf-8")


async def map_target(client: LLMClient, store: Store, t: dict, papers: dict[str, dict],
                     stats: ExtractStats) -> dict:
    pid = t["paper_id"]
    if store.all(Argument, parent=pid):
        args = store.all(Argument, parent=pid)
        return {"target": t["id"], "arguments": len(args), "skipped": "already mapped"}
    p = papers.get(pid, {"title": t["title"], "abstract": ""})
    claims = [c for c in store.all(Claim, parent=pid) if c.level == "fulltext"]
    if not claims:
        claims = await extract_paper_claims(client, pid, t["title"], target_text(t), stats)
        store.put_many(claims)
    args = await reconstruct_arguments(client, pid, t["title"], p.get("abstract", ""), claims)
    by_id = {c.id: c for c in claims}
    out = []
    for a in args:
        a2, mp = await formalize(client, a, by_id)
        if mp:
            store.put(mp)
            store.put(Edge(src=mp.id, dst=a2.conclusion_id, relation="supports"))
        store.put(a2)
        store.put_many([Edge(src=x, dst=a2.conclusion_id, relation="supports") for x in a2.premise_ids])
        out.append(a2)
    return {"target": t["id"], "claims": len(claims), "arguments": len(out),
            "premises": [len(a.premise_ids) for a in out], "valid": [a.valid for a in out],
            "missing_premise": [bool(a.missing_premise) for a in out]}


def build_indexes(store: Store, corpus: list[dict]) -> dict:
    emb = Embedder()
    claims = [c for c in store.all(Claim) if c.level in ("fulltext", "abstract")]
    titles = {p["id"]: p["title"] for p in corpus}
    ci = HybridIndex([c.id for c in claims], [c.text for c in claims],
                     [{"paper_id": c.paper_id, "kind": c.kind, "quote": c.quote, "level": c.level,
                       "title": titles.get(c.paper_id, "")} for c in claims], embedder=emb)
    ci.save(INDEX_DIR / "claims")
    papers = [p for p in corpus if p.get("abstract")]
    ai = HybridIndex([p["id"] for p in papers], [f"{p['title']}. {p['abstract']}" for p in papers],
                     [{"title": p["title"], "year": p.get("year")} for p in papers], embedder=emb)
    ai.save(INDEX_DIR / "abstracts")
    return {"claims_indexed": len(ci), "abstracts_indexed": len(ai), "embedder": emb.name}


async def main(targets_only: bool = False) -> None:
    client = LLMClient()
    store = Store()
    corpus = load_corpus()
    papers = {p["id"]: p for p in corpus}
    store.put_many(Paper(id=p["id"], source=p["source"], title=p["title"], authors=p.get("authors", []),
                         year=p.get("year"), abstract=p.get("abstract", ""), url=p.get("url") or "",
                         pdf_path=p.get("pdf_path"), deposited_at=p.get("publication_date") or p.get("deposited_at"))
                   for p in corpus)
    tstats, astats = ExtractStats(), ExtractStats()
    targets = load_targets()
    results = await asyncio.gather(*[map_target(client, store, t, papers, tstats) for t in targets],
                                   return_exceptions=True)
    target_report = [r if isinstance(r, dict) else {"error": repr(r)} for r in results]
    for r in target_report:
        log.info("target: %s", r)
    if not targets_only:
        done = {c.paper_id for c in store.all(Claim) if c.level == "abstract"}
        todo = [p for p in corpus if p.get("abstract") and p["id"] not in done]
        store.put_many(await abstract_claims(client, todo, astats))
    idx = build_indexes(store, corpus)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "targets": target_report,
        "fulltext_claims": {"proposed": tstats.proposed, "kept": tstats.kept,
                            "drop_rate": round(tstats.drop_rate, 3)},
        "abstract_claims": {"proposed": astats.proposed, "kept": astats.kept,
                            "drop_rate": round(astats.drop_rate, 3)},
        "dropped_examples": (tstats.dropped + astats.dropped)[:30],
        **idx, "llm": client.stats, "budget": client.budget.summary(),
    }
    prev = json.loads(STATS.read_text()) if STATS.exists() else {}
    if prev and not tstats.proposed:
        report["fulltext_claims"] = prev.get("fulltext_claims", report["fulltext_claims"])
    if prev and not astats.proposed:
        report["abstract_claims"] = prev.get("abstract_claims", report["abstract_claims"])
    STATS.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(json.dumps({k: v for k, v in report.items() if k != "dropped_examples"}, indent=1)[:3000])
