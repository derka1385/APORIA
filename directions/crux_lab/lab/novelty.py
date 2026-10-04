"""Novelty check: 3 restatements -> hybrid search (claims + abstracts) + live OpenAlex -> rerank.

novelty = 1 - max similarity among same_move/related matches. If the reranker finds none,
novelty = 1 - the highest similarity of any reranked passage (never a free 1.0).
Never a claim of novelty: the result always carries records_searched and the nearest matches.

A check that could not be completed is *not assessed*: novelty is None and `status` says why
(no_candidates | rerank_failed | retrieval_failed). Nothing downstream may score, rank or round it.
"""
from __future__ import annotations

import hashlib
import json
import os
import logging
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from crux_lab.agents.roles import render
from crux_lab.config import RAW
from crux_lab.graph.extract import quote_found
from crux_lab.graph.index import HybridIndex
from crux_lab.graph.schema import NearestMatch
from crux_lab.llm.client import LLMClient

log = logging.getLogger(__name__)
LIVE_CACHE = RAW / "openalex_live"
LIVE_DAILY_CAP = int(os.environ.get("OPENALEX_LIVE_CAP", "45"))      # OpenAlex without a key allows ~100 requests/day; the corpus build uses ~30
RANGES = {"same_move": (0.7, 1.0), "related": (0.3, 0.69), "different": (0.0, 0.29)}


class Restatements(BaseModel):
    paper_vocabulary: str
    plain_english: str
    neighboring_tradition: str


class Verdict(BaseModel):
    n: int
    verdict: str = Field(pattern="^(same_move|related|different)$")
    similarity: float = Field(ge=0, le=1)
    quote: str = ""


class RerankOut(BaseModel):
    judgments: list[Verdict]


@dataclass
class Passage:
    record_id: str
    paper_id: str
    text: str
    title: str
    source: str            # "claims" | "abstracts" | "openalex_live"


ASSESSED = "assessed"
REASONS = {
    "no_candidates": "No eligible literature candidates were available for this check.",
    "rerank_failed": "The literature assessment could not be completed: the reranker returned no valid judgment "
                     "after its retries. Retry the check.",
    "retrieval_failed": "The literature assessment could not be completed: retrieval failed. Retry the check.",
}


@dataclass
class NoveltyResult:
    objection_id: str
    restatements: dict
    novelty: float | None               # None = not assessed (see status)
    records_searched: int
    reranked: int
    nearest: list[NearestMatch]
    live_openalex: str
    matches: list[NearestMatch] = field(default_factory=list)
    status: str = ASSESSED              # assessed | no_candidates | rerank_failed | retrieval_failed
    reason: str = ""

    def to_dict(self) -> dict:
        return {"objection_id": self.objection_id, "restatements": self.restatements,
                "novelty": round(self.novelty, 3) if self.novelty is not None else None,
                "status": self.status, "reason": self.reason,
                "records_searched": self.records_searched,
                "reranked": self.reranked, "live_openalex": self.live_openalex,
                "nearest": [m.model_dump() for m in self.nearest],
                "matches": [m.model_dump() for m in self.matches]}


def unassessed(objection_id: str, restatements: dict, status: str, records_searched: int, reranked: int,
               live_openalex: str, detail: str = "") -> NoveltyResult:
    reason = REASONS[status] + (f" ({detail})" if detail else "")
    return NoveltyResult(objection_id, restatements, None, records_searched, reranked, [], live_openalex,
                         [], status, reason)


def normalize(n: dict | None) -> dict | None:
    """A stored novelty record with an explicit status. Records written before statuses existed are checked:
    a 1.0 with nothing reranked, or with no reranker judgments at all, was a failure path scored as maximal
    novelty (fixed 2026-10-04), so it is surfaced as not assessed. The stored number is kept under
    `legacy_novelty` for the record; it is never used as a score."""
    if n is None:
        return None
    if n.get("status"):
        return n
    out = dict(n)
    if n.get("novelty") is None:
        out.update(status="rerank_failed", reason=REASONS["rerank_failed"])
    elif not n.get("reranked"):
        out.update(status="no_candidates", reason=REASONS["no_candidates"], novelty=None, legacy_novelty=n["novelty"])
    elif not n.get("matches") and n.get("novelty") == 1.0:
        out.update(status="rerank_failed", reason=REASONS["rerank_failed"], novelty=None, legacy_novelty=n["novelty"])
    else:
        out.update(status=ASSESSED, reason="")
    return out


def is_assessed(n: dict | None) -> bool:
    """True only for a completed check with a numeric score."""
    n = normalize(n)
    return bool(n) and n.get("status") == ASSESSED and n.get("novelty") is not None


def keywords(text: str, n: int = 10) -> str:
    """Content words for a live search (long sentences match nothing; punctuation breaks filters)."""
    from crux_lab.graph.index import tokenize
    return " ".join(list(dict.fromkeys(tokenize(text)))[:n])


def _live_today() -> int:
    import time
    if not LIVE_CACHE.exists():
        return 0
    day = time.time() - 86400
    return sum(1 for f in LIVE_CACHE.glob("*.json") if f.stat().st_mtime > day)


def live_openalex(query: str, n: int = 10) -> tuple[list[Passage], str]:
    """One cached OpenAlex search. Fails soft (budget is ~100 requests/day without a key)."""
    from crux_lab.corpus import openalex

    LIVE_CACHE.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(query.encode()).hexdigest()[:16]
    path = LIVE_CACHE / f"{key}.json"
    if path.exists():
        works = json.loads(path.read_text())
        status = "cached"
    elif _live_today() >= LIVE_DAILY_CAP:
        return [], f"skipped (daily cap of {LIVE_DAILY_CAP} live OpenAlex searches reached)"
    else:
        try:
            works = [openalex.to_paper(w) for w in openalex.search(
                keywords(query), max_records=n, per_page=n, field="search")]
            path.write_text(json.dumps(works))
            status = "ok"
        except Exception as e:  # noqa: BLE001
            log.info("live OpenAlex unavailable: %s", e)
            return [], f"unavailable ({str(e)[:80]})"
    out = [Passage(f"live:{w['id']}", w["id"], f"{w['title']}. {w['abstract'][:1200]}", w["title"], "openalex_live")
           for w in works if w.get("abstract")]
    return out, f"{status}: {len(out)} results"


async def check(client: LLMClient, objection_id: str, objection: str, argument_text: str,
                target_id: str, target_text: str, claims_ix: HybridIndex, abstracts_ix: HybridIndex,
                use_live: bool = True, exclude_paper: str | None = None, k: int = 20,
                rerank_n: int = 14, restate: bool = True) -> NoveltyResult:
    rs = None
    if restate:
        system, user = render("restate", argument=argument_text, target=f"{target_id}: {target_text}",
                              objection=objection)
        rs, _ = await client.json("reranker", user, Restatements, system)
    queries = [objection] + ([rs.paper_vocabulary, rs.plain_english, rs.neighboring_tradition] if rs else [])
    fused: dict[str, tuple[float, Passage]] = {}

    from crux_lab.corpus.dedup import work_of
    excluded_work = work_of(exclude_paper) if exclude_paper else None

    def add(p: Passage, score: float):
        if exclude_paper and (p.paper_id == exclude_paper or work_of(p.paper_id) == excluded_work):
            return    # the target paper itself (or another record of it) is not prior art for an objection to it
        old = fused.get(p.record_id)
        fused[p.record_id] = (score + (old[0] if old else 0), p)

    restated = rs.model_dump() if rs else {}
    try:
        for q in queries:
            for rank, h in enumerate(claims_ix.search(q, k=k)):
                add(Passage(h.id, h.meta.get("paper_id", ""), h.text, h.meta.get("title", ""), "claims"), 1 / (60 + rank))
            for rank, h in enumerate(abstracts_ix.search(q, k=k // 2)):
                add(Passage(f"abs:{h.id}", h.id, h.text[:1500], h.meta.get("title", ""), "abstracts"), 0.8 / (60 + rank))
    except (OSError, ValueError, RuntimeError, KeyError, IndexError) as e:   # local index failure, not budget
        log.warning("novelty retrieval failed for %s: %s", objection_id, e)
        return unassessed(objection_id, restated, "retrieval_failed", 0, 0, "skipped", repr(e)[:120])
    live_status, live_n = "skipped", 0
    if use_live:
        import asyncio
        live, live_status = await asyncio.to_thread(live_openalex, rs.plain_english if rs else objection)
        live_n = len(live)
        for rank, p in enumerate(live):
            add(p, 0.8 / (60 + rank))
    cands = [p for _, p in sorted(fused.values(), key=lambda x: -x[0])][:rerank_n]
    records_searched = len(claims_ix) + len(abstracts_ix) + live_n
    if not cands:
        return unassessed(objection_id, restated, "no_candidates", records_searched, 0, live_status)

    listing = "\n\n".join(f"[{i + 1}] ({p.title[:90]})\n{p.text}" for i, p in enumerate(cands))
    system, user = render("rerank", target_id=target_id, target_text=target_text, objection=objection,
                          passages=listing)

    def validate(o: RerankOut) -> str | None:
        seen = {j.n for j in o.judgments}
        missing = [i for i in range(1, len(cands) + 1) if i not in seen]
        if missing:
            return f"judge every passage; missing numbers {missing}"
        return None

    out, _ = await client.json("reranker", user, RerankOut, system, validate=validate, max_tokens=4000)
    if out is None:     # the client's bounded retries are exhausted: no judgment, so no score
        return unassessed(objection_id, restated, "rerank_failed", records_searched, len(cands), live_status)
    matches: list[NearestMatch] = []
    for j in out.judgments:
        if not 1 <= j.n <= len(cands):
            continue
        p = cands[j.n - 1]
        lo, hi = RANGES[j.verdict]
        sim = min(hi, max(lo, j.similarity))          # similarity must sit inside its verdict band
        quote = j.quote if j.quote and quote_found(j.quote, p.text) else ""
        verdict = j.verdict
        if verdict != "different" and not quote:
            verdict, sim = "related" if verdict == "same_move" else verdict, min(sim, 0.69)
        matches.append(NearestMatch(record_id=p.record_id, paper_id=p.paper_id, verdict=verdict,
                                    similarity=round(sim, 3), quote=quote, title=p.title))
    if not matches:
        return unassessed(objection_id, restated, "rerank_failed", records_searched, len(cands), live_status,
                          "no judgment referred to a listed passage")
    matches.sort(key=lambda m: -m.similarity)
    hits = [m.similarity for m in matches if m.verdict in ("same_move", "related")]
    novelty = 1 - (max(hits) if hits else (matches[0].similarity if matches else 0.0))
    from crux_lab.corpus.dedup import distinct_nearest
    return NoveltyResult(objection_id, restated, novelty, records_searched,
                         len(cands), distinct_nearest(matches), live_status, matches)
