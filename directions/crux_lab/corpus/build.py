"""`make corpus`: OpenAlex hiddenness corpus + fresh candidates + open-access full texts."""
from __future__ import annotations

import json
import logging
import re

from crux_lab.config import CORPUS, RAW, TOPIC, TOPIC_DATA
from crux_lab.corpus import openalex, pdf

log = logging.getLogger(__name__)
FRESH_FROM = str(TOPIC.get("fresh_from", "2026-08-01"))
FRESH_QUERIES: list[str] = list(TOPIC.get("fresh_queries", []))
RELEVANT = re.compile(TOPIC.get("relevant", "."), re.I)
# Fresh searches are broad (e.g. "decision theory" finds ecology too); a topic may demand more of fresh papers.
FRESH_RELEVANT = re.compile(TOPIC.get("fresh_relevant", "."), re.I)


def harvest_classic() -> list[dict]:
    papers = openalex.harvest(openalex.QUERIES, max_per_query=int(TOPIC.get("max_per_query", 400)))
    keep = [p for p in papers if len(p["abstract"]) >= 200
            and RELEVANT.search(p["title"] + " " + p["abstract"])]
    log.info("classic: %d harvested, %d kept (abstract >= 200 chars and on-topic)", len(papers), len(keep))
    return keep


def harvest_fresh() -> list[dict]:
    seen: dict[str, dict] = {}
    for q in FRESH_QUERIES:
        for w in openalex.search(q, filters={"from_publication_date": FRESH_FROM, "is_oa": "true",
                                             "has_abstract": "true"}, max_records=int(TOPIC.get("max_per_query", 200))):
            p = openalex.to_paper(w, q)
            p["fresh"] = True
            if (p["id"] not in seen and len(p["abstract"]) >= 300
                    and FRESH_RELEVANT.search(p["title"] + " " + p["abstract"])):
                seen[p["id"]] = p
    log.info("fresh: %d candidates since %s", len(seen), FRESH_FROM)
    return list(seen.values())


def mark_recent(papers: list[dict]) -> int:
    """A record published since FRESH_FROM is fresh whichever search found it (the topic's own search often finds
    the newest on-topic paper first, and used to leave it unflagged)."""
    n = 0
    for p in papers:
        if not p.get("fresh") and (p.get("publication_date") or "") >= FRESH_FROM:
            p["fresh"] = True
            n += 1
    return n


def fulltexts(papers: list[dict], limit: int = 50, fresh_share: float = 0.5) -> int:
    """Up to `limit` OA full texts, at most `fresh_share` of them fresh: fresh candidates first, then the
    most-cited on-topic papers (so a crowded fresh pool cannot leave the classic targets without text)."""
    cands = [p for p in papers if p.get("pdf_url") and not p.get("pdf_path")]
    cands.sort(key=lambda p: (not p.get("fresh"), -(p.get("cited_by_count") or 0)))
    have = [p for p in papers if p.get("pdf_path")]
    got, fresh_got = len(have), sum(1 for p in have if p.get("fresh"))
    for p in cands:
        if got >= limit:
            break
        if p.get("fresh") and fresh_got >= limit * fresh_share:
            continue
        t = pdf.get_fulltext(p["id"], p["pdf_url"])
        if t:
            p["pdf_path"] = str(pdf.text_path(p["id"]).relative_to(RAW.parent.parent))
            p["fulltext_chars"] = len(t)
            got += 1
            fresh_got += bool(p.get("fresh"))
    log.info("full texts: %d (%d fresh)", got, fresh_got)
    return got


def main(skip_fulltext: bool = False) -> None:
    classic = harvest_classic()
    (TOPIC_DATA / "fresh_candidates.json").write_text(json.dumps(fresh := harvest_fresh(), indent=1))
    by_id = {p["id"]: p for p in classic}
    for p in fresh:
        by_id.setdefault(p["id"], p)
    papers = list(by_id.values())
    mark_recent(papers)
    if not skip_fulltext:
        fulltexts(papers)
    with CORPUS.open("w", encoding="utf-8") as f:
        for p in papers:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    n_abs = sum(1 for p in papers if p["abstract"])
    n_ft = sum(1 for p in papers if p.get("pdf_path"))
    print(f"corpus: {len(papers)} records ({n_abs} with abstracts, {n_ft} full texts, "
          f"{sum(1 for p in papers if p.get('fresh'))} fresh) -> {CORPUS}")


def refine() -> None:
    """Re-apply the topic's filters and the full-text quota to an existing corpus, without new searches."""
    papers = [p for p in load_corpus()
              if not p.get("fresh") or FRESH_RELEVANT.search(p["title"] + " " + p["abstract"])]
    newly = mark_recent(papers)
    have = sum(1 for p in papers if p.get("pdf_path"))
    # room for recent papers that were not flagged before (fresh first in the queue)
    fulltexts(papers, limit=max(50, have + (10 if newly else 0)))   # texts of dropped papers stay in data/raw
    with CORPUS.open("w", encoding="utf-8") as f:
        for p in papers:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    print(f"corpus refined: {len(papers)} records, {sum(1 for p in papers if p.get('pdf_path'))} full texts "
          f"({sum(1 for p in papers if p.get('fresh') and p.get('pdf_path'))} fresh)")


def load_corpus() -> list[dict]:
    if not CORPUS.exists():
        return []
    return [json.loads(line) for line in CORPUS.read_text("utf-8").splitlines() if line.strip()]
