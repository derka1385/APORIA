"""APORIA -> Crux Lab bridge: every objection APORIA's reasoners produced is checked against the literature.

APORIA measures whether differently configured reasoners produce *different* objections ("unique objections");
this asks whether those objections are also *new*: the lab's prior-art check (hybrid retrieval over the topic's
claim and abstract indexes, then the strict reranker) scores each one, and the result is aggregated by
condition, Δ and profile. One rerank per objection, on its own wording (no restatement step, no live search).
"""
from __future__ import annotations

import asyncio
import glob
import json
import statistics
from pathlib import Path

from crux_lab.config import INDEX_DIR, RESULTS, TOPIC
from crux_lab.graph.index import HybridIndex
from crux_lab.lab import novelty
from crux_lab.llm.client import LLMClient


def load_objections(run_glob: str) -> list[dict]:
    seen, out = set(), []
    for f in sorted(glob.glob(run_glob)):
        r = json.loads(Path(f).read_text())
        if r.get("failed"):
            continue
        for prof, ag in r["agents"].items():
            for n in ag["nodes"]:
                if n["type"] == "objection" and n["text"].strip() and n["text"] not in seen:
                    seen.add(n["text"])
                    out.append({"run": r["id"], "condition": r["condition"], "delta": r["delta"], "profile": prof,
                                "model": (r.get("models") or [None])[0], "text": n["text"].strip(),
                                "node": n["id"]})
    return out


async def check_all(items: list[dict], client: LLMClient) -> list[dict]:
    claims_ix = HybridIndex.load(INDEX_DIR / "claims")
    abstracts_ix = HybridIndex.load(INDEX_DIR / "abstracts", embedder=claims_ix.embedder)
    question = TOPIC.get("bridge_question", TOPIC.get("name", ""))

    async def one(i, it):
        r = await novelty.check(client, f"aporia-{i}", it["text"], question, "Q", question, claims_ix, abstracts_ix,
                                use_live=False, restate=False)
        return {**it, "novelty": r.novelty, "status": r.status, "records_searched": r.records_searched,
                "nearest": [m.model_dump() for m in r.nearest[:3]]}
    return await asyncio.gather(*[one(i, it) for i, it in enumerate(items)])


def summarize(rows: list[dict]) -> dict:
    def agg(key):
        groups: dict = {}
        for r in rows:
            groups.setdefault(key(r), []).append(r)
        out = []
        for k, g in sorted(groups.items(), key=lambda kv: str(kv[0])):
            nov = [r["novelty"] for r in g if r["novelty"] is not None]
            out.append({"group": k, "objections": len(g), "assessed": len(nov),
                        "mean_novelty": round(statistics.mean(nov), 3) if nov else None,
                        "share_novel": round(sum(n > 0.5 for n in nov) / len(nov), 3) if nov else None})
        return out
    return {"by_condition": agg(lambda r: f"{r['condition']} Δ {r['delta']}"),
            "by_profile": agg(lambda r: r["profile"])}


async def main(run_glob: str) -> dict:
    items = load_objections(run_glob)
    client = LLMClient()
    rows = await check_all(items, client)
    data = {"experiment": "APORIA objections against the literature", "question": TOPIC.get("bridge_question"),
            "n": len(rows), "reranker": client.spec_for("reranker").label, **summarize(rows), "objections": rows,
            "limits": ("One rerank per objection on its own wording (no restatement, no live OpenAlex), against an "
                       "abstract-level corpus of the topic's OpenAlex search; APORIA's runs used small local models "
                       "(qwen) and its runs differ in condition and Δ, so groups are small. Novelty is distance from "
                       "what retrieval found, never a claim of originality.")}
    (RESULTS / "bridge.json").write_text(json.dumps(data, indent=1, ensure_ascii=False))
    return data
