"""Target selection -> data/targets.json: 3 fresh targets + 2 classic fallbacks (+ manual targets).

A topic may change the split with `targets: {fresh, classic, fresh_min_relevance}`."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from crux_lab.agents.roles import render
from crux_lab.config import MANUAL_TARGETS, ROOT, TARGETS, TOPIC
from crux_lab.corpus.build import load_corpus
from crux_lab.llm.client import LLMClient

log = logging.getLogger(__name__)


class Screen(BaseModel):
    in_area: bool
    argues_for_thesis: bool
    thesis: str = ""
    topic_relevance: int = Field(ge=0, le=3)
    argument_clarity: int = Field(ge=0, le=3)
    english: bool


async def screen(client: LLMClient, papers: list[dict]) -> dict[str, Screen]:
    async def one(p):
        levels = TOPIC.get("relevance_levels") or ["none", "related", "closely related", "directly on topic"]
        scale = ", ".join(f"{i} {lvl}" for i, lvl in enumerate(levels[:4])) + "."
        system, user = render("target_screen", title=p["title"], abstract=p["abstract"][:3000],
                              area=TOPIC.get("area", "philosophy"), scale=scale)
        obj, _ = await client.json("reranker", user, Screen, system)
        return p["id"], obj
    res = await asyncio.gather(*[one(p) for p in papers])
    return {pid: s for pid, s in res if s}


def english_fulltext(p: dict) -> bool:
    """Code check on the text itself: the screen judges from the abstract, which may be translated."""
    from crux_lab.config import ROOT
    try:
        t = (ROOT / p["pdf_path"]).read_text("utf-8")[2000:12000]
    except OSError:
        return False
    letters = [c for c in t if c.isalpha()]
    ascii_share = sum(c.isascii() for c in letters) / max(1, len(letters))
    common = sum(t.lower().count(w) for w in (" the ", " and ", " of ", " that ", " is "))
    return ascii_share > 0.95 and common > 80


PEER_REVIEWED_POR = ("religious studies", "sophia", "international journal for philosophy of religion",
                     "faith and philosophy", "european journal for philosophy of religion",
                     "philosophia christi", "heythrop", "religions", "philosophy compass", "philosophia",
                     "american catholic philosophical quarterly", "new blackfriars", "theology and science")


def tiebreak(p: dict) -> tuple:
    """Ties: established philosophy-of-religion venue first, then shorter full text (cheaper to map)."""
    venue = (p.get("venue") or "").lower()
    return (not any(v == venue or v in venue for v in PEER_REVIEWED_POR), p.get("fulltext_chars") or 10**9)


def journal_article(p: dict) -> bool:
    """Ties among classics: a journal article before a preprint, dissertation or dataset."""
    venue = (p.get("venue") or "").lower()
    return p.get("type") == "article" and not any(r in venue for r in ("arxiv", "repec", "hal ", "ssrn", "zenodo"))


def score(s: Screen) -> float:
    if not (s.in_area and s.argues_for_thesis and s.english):
        return -1
    return s.topic_relevance * 2 + s.argument_clarity


def spread(ranked: list[dict], screens: dict[str, Screen], min_score: int) -> list[dict]:
    """Round-robin over the topic's searches, in the order the topic file lists them, so the targets cover
    the topic's sub-debates instead of the one the screen rates highest. Within a search: the existing rank."""
    by_query: dict[str, list[dict]] = {}
    for p in ranked:
        if score(screens[p["id"]]) >= min_score:
            by_query.setdefault(p.get("query") or "", []).append(p)
    order = [q for q in TOPIC.get("queries", {}) if q in by_query] + [q for q in by_query
                                                                      if q not in TOPIC.get("queries", {})]
    out: list[dict] = []
    while any(by_query.values()):
        for q in order:
            if by_query[q]:
                out.append(by_query[q].pop(0))
    return out


def manual_targets() -> list[dict]:
    out = []
    for f in sorted(MANUAL_TARGETS.glob("*.md")):
        out.append({"id": f"manual-{f.stem}", "paper_id": f"manual:{f.stem}", "kind": "manual",
                    "title": f.stem.replace("-", " ").title(), "text_path": str(f.relative_to(ROOT)),
                    "reason": "Manual target supplied by the human in data/manual_targets/."})
    return out


async def select(client: LLMClient | None = None) -> list[dict]:
    client = client or LLMClient()
    corpus = [p for p in load_corpus() if p.get("pdf_path") and english_fulltext(p)]
    fresh = [p for p in corpus if p.get("fresh")]
    classic = [p for p in corpus if not p.get("fresh")]
    screens = await screen(client, fresh + classic)
    ranked_fresh = sorted([p for p in fresh if p["id"] in screens and score(screens[p["id"]]) >= 0],
                          key=lambda p: (-score(screens[p["id"]]), *tiebreak(p)))
    ranked_classic = sorted([p for p in classic if p["id"] in screens and score(screens[p["id"]]) >= 0],
                            key=lambda p: (-screens[p["id"]].topic_relevance,
                                           -screens[p["id"]].argument_clarity,
                                           not journal_article(p),
                                           -(p.get("cited_by_count") or 0)))
    plan = TOPIC.get("targets") or {}
    n_fresh, n_classic = int(plan.get("fresh", 3)), int(plan.get("classic", 2))
    min_rel = int(plan.get("fresh_min_relevance", 0))
    ranked_fresh = [p for p in ranked_fresh if screens[p["id"]].topic_relevance >= min_rel]
    n_classic += max(0, n_fresh - len(ranked_fresh))   # too few on-topic fresh papers: fill with classics
    if plan.get("spread"):
        ranked_classic = spread(ranked_classic, screens, int(plan.get("min_score", 4)))
    targets = []
    for kind, pool, n in (("fresh", ranked_fresh, n_fresh), ("classic", ranked_classic, n_classic)):
        for p in pool[:n]:
            s = screens[p["id"]]
            levels = TOPIC.get("relevance_levels") or ["none", "related", "closely related", "on topic"]
            rel = levels[min(s.topic_relevance, len(levels) - 1)]
            found = (f"found by the search “{p['query']}”; " if kind == "classic" and plan.get("spread") and p.get("query")
                     else "")
            why = (f"{'Published ' + (p.get('publication_date') or '') + ' (after 2026-08-01), ' if kind == 'fresh' else 'Classic fallback, '}"
                   f"{found}"
                   f"open-access full text ({p.get('fulltext_chars', 0):,} chars); argues for a thesis; "
                   f"topic relevance {s.topic_relevance}/3 ({rel}); argument clarity {s.argument_clarity}/3.")
            targets.append({"id": p["id"].replace(":", "-"), "paper_id": p["id"], "kind": kind,
                            "title": p["title"], "authors": p.get("authors", []),
                            "year": p.get("year"), "published": p.get("publication_date"),
                            "url": p.get("url"), "text_path": p["pdf_path"], "thesis": s.thesis,
                            "screen": s.model_dump(), "reason": why})
    targets += manual_targets()
    meta = {"generated_at": datetime.now(timezone.utc).isoformat(), "screened": len(screens),
            "eligible_fresh": len(ranked_fresh), "eligible_classic": len(ranked_classic),
            "topic": TOPIC.get("slug"),
            "note": (f"No fresh full-text paper directly on {TOPIC.get('name', 'the topic')} was available; fresh "
                     f"targets fall back to the wider area ({TOPIC.get('area', 'philosophy')})."
                     if not any(screens[t['paper_id']].topic_relevance == 3 for t in targets
                                if t['kind'] == 'fresh') else "")}
    TARGETS.write_text(json.dumps({"meta": meta, "targets": targets}, indent=2, ensure_ascii=False))
    return targets


def load_targets() -> list[dict]:
    return json.loads(TARGETS.read_text())["targets"] if TARGETS.exists() else []


def main() -> None:
    ts = asyncio.run(select())
    for t in ts:
        print(f"{t['id']} [{t['kind']}] {t['title'][:70]}\n   {t['reason']}")
