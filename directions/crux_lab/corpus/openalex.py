"""OpenAlex harvester. Abstracts are rebuilt from `abstract_inverted_index`."""
from __future__ import annotations

import logging
from typing import Iterator

from crux_lab.corpus import http

log = logging.getLogger(__name__)
BASE = "https://api.openalex.org/works"
SELECT = ("id,doi,display_name,publication_year,publication_date,created_date,authorships,"
          "abstract_inverted_index,primary_location,best_oa_location,open_access,type,"
          "cited_by_count,primary_topic,language")

# Queries come from the topic (config/topics/<slug>.yaml): label -> OpenAlex search string.
# Quoted = phrase match; unquoted title_and_abstract.search is stemmed and very broad.
from crux_lab.config import TOPIC

SEARCH_STRINGS: dict[str, str] = dict(TOPIC.get("queries", {}))
QUERIES = list(SEARCH_STRINGS)
# OpenAlex without an API key: ~$0.10/day = ~100 list requests; from_created_date is premium-only.


def rebuild_abstract(inv: dict | None) -> str:
    if not inv:
        return ""
    pos = [(i, w) for w, idxs in inv.items() for i in idxs]
    return " ".join(w for _, w in sorted(pos))


def to_paper(w: dict, query: str = "") -> dict:
    wid = w["id"].rsplit("/", 1)[-1]
    oa = w.get("best_oa_location") or {}
    prim = w.get("primary_location") or {}
    src = (prim.get("source") or {}).get("display_name")
    url = (w.get("doi") or prim.get("landing_page_url") or w["id"])
    return {
        "id": f"oa:{wid}", "source": "openalex", "title": w.get("display_name") or "",
        "authors": [a["author"]["display_name"] for a in (w.get("authorships") or [])
                    if a.get("author") and a["author"].get("display_name")],
        "year": w.get("publication_year"), "abstract": rebuild_abstract(w.get("abstract_inverted_index")),
        "url": url, "doi": w.get("doi"), "venue": src,
        "pdf_url": oa.get("pdf_url"), "pdf_path": None,
        "deposited_at": w.get("created_date"), "publication_date": w.get("publication_date"),
        "type": w.get("type"), "cited_by_count": w.get("cited_by_count", 0),
        "topic": ((w.get("primary_topic") or {}).get("display_name")),
        "language": w.get("language"), "query": query,
    }


def search(query: str | None = None, filters: dict | None = None, max_records: int = 400,
           per_page: int = 200, field: str = "title_and_abstract.search") -> Iterator[dict]:
    flt = dict(filters or {})
    params: dict = {"per_page": per_page, "select": SELECT, "cursor": "*"}
    if query and field == "search":
        params["search"] = query          # relevance-ranked full search; no filter-syntax pitfalls
    elif query:
        flt[field] = SEARCH_STRINGS.get(query, query)
    if flt:
        params["filter"] = ",".join(f"{k}:{v}" for k, v in flt.items())
    n = 0
    while n < max_records:
        r = http.get(BASE, params=params, timeout=60)
        data = r.json()
        results = data.get("results", [])
        if not results:
            break
        for w in results:
            yield w
            n += 1
            if n >= max_records:
                break
        cur = data.get("meta", {}).get("next_cursor")
        if not cur:
            break
        params["cursor"] = cur


def harvest(queries: list[str] = QUERIES, max_per_query: int = 400) -> list[dict]:
    seen: dict[str, dict] = {}
    for q in queries:
        k = 0
        for w in search(q, max_records=max_per_query):
            p = to_paper(w, q)
            if p["id"] not in seen:
                seen[p["id"]] = p
                k += 1
        log.info("OpenAlex %r: %d new", q, k)
    return list(seen.values())
