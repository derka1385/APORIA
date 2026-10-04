"""Same-work detection. OpenAlex often lists one paper several times (Zenodo/figshare versions,
preprint + article). A work key is the normalised title + the first author's surname; different
papers that merely share a title (e.g. several titled "Divine Hiddenness") stay distinct."""
from __future__ import annotations

import re


def _norm(t: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def work_key(paper: dict) -> str:
    first = _norm((paper.get("authors") or [""])[0]).split()
    return f"{_norm(paper.get('title'))}|{first[-1] if first else ''}"


def work_ids(corpus: list[dict]) -> dict[str, str]:
    """paper id -> canonical id of its work (the first record seen with that work key)."""
    canon: dict[str, str] = {}
    out: dict[str, str] = {}
    for p in corpus:
        out[p["id"]] = canon.setdefault(work_key(p), p["id"])
    return out


_CACHE: dict[str, object] = {}


def work_of(paper_id: str) -> str:
    """Work key for any paper id we may meet: corpus records and cached live-OpenAlex records."""
    if "map" not in _CACHE:
        import json

        from crux_lab.config import RAW
        from crux_lab.corpus.build import load_corpus

        corpus = load_corpus()
        ids = work_ids(corpus)
        keys = {p["id"]: work_key(p) for p in corpus}
        canon = {keys[pid]: ids[pid] for pid in ids}
        live = {}
        for f in (RAW / "openalex_live").glob("*.json") if (RAW / "openalex_live").exists() else []:
            for w in json.loads(f.read_text()):
                live[w["id"]] = canon.get(work_key(w), w["id"])
        _CACHE["map"] = {**live, **ids}
    return _CACHE["map"].get(paper_id, paper_id)  # type: ignore[union-attr]


def distinct_nearest(matches: list, k: int = 3, key=None) -> list:
    """First k matches (already sorted by similarity) that belong to different works."""
    key = key or (lambda m: work_of(m["paper_id"] if isinstance(m, dict) else m.paper_id))
    out, seen = [], set()
    for m in matches:
        w = key(m)
        if w in seen:
            continue
        seen.add(w)
        out.append(m)
        if len(out) == k:
            break
    return out
