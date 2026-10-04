"""Long-term memory: a SQLite store that survives across research sessions.

Items are what a session learned (hypotheses and whether they survived,
objections and whether they defeated their target, assumptions and how often
they recur, counterfactual outcomes, unresolved questions, trajectories).
Recall is by embedding similarity, so the system can notice "I have explored
this before" and let the outcome shape the new run.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

DB = Path(__file__).parent / "memory.db"
_lock = threading.Lock()
_cache: list[dict] | None = None  # all rows with vectors; small enough to scan


def _conn():
    c = sqlite3.connect(DB, timeout=10)
    c.execute("""CREATE TABLE IF NOT EXISTS memory (
        id INTEGER PRIMARY KEY, kind TEXT, text TEXT, vec TEXT, question TEXT, profile TEXT,
        outcome TEXT, score REAL, run TEXT, ts REAL)""")
    return c


def rows() -> list[dict]:
    global _cache
    with _lock:
        if _cache is None:
            with _conn() as c:
                _cache = [{"id": r[0], "kind": r[1], "text": r[2], "vec": json.loads(r[3]), "question": r[4],
                           "profile": r[5], "outcome": r[6], "score": r[7], "run": r[8], "ts": r[9]}
                          for r in c.execute("SELECT id, kind, text, vec, question, profile, outcome, score, run, ts FROM memory")]
        return _cache


def write(items: list[dict]):
    """items: {kind, text, vec, question, profile, outcome, score, run}"""
    global _cache
    if not items:
        return
    with _lock, _conn() as c:
        c.executemany("INSERT INTO memory (kind, text, vec, question, profile, outcome, score, run, ts) VALUES (?,?,?,?,?,?,?,?,?)",
                      [(i["kind"], i["text"], json.dumps(i["vec"]), i.get("question", ""), i.get("profile", ""),
                        i.get("outcome", ""), i.get("score", 0.0), i.get("run", ""), time.time()) for i in items])
        _cache = None


def search(vec: list[float], cos, k=5, kinds=None, min_sim=0.0, exclude_run=None, profile=None) -> list[dict]:
    """Nearest items by cosine; ponytail: linear scan, fine to ~50k items, add an ANN index past that."""
    scored = [(cos(vec, r["vec"]), r) for r in rows()
              if (kinds is None or r["kind"] in kinds) and r["run"] != exclude_run
              and (profile is None or r["profile"] == profile)]
    scored = [(s, r) for s, r in scored if s >= min_sim]
    scored.sort(key=lambda x: -x[0])
    return [{**{k2: v for k2, v in r.items() if k2 != "vec"}, "sim": round(s, 3)} for s, r in scored[:k]]


def stats() -> dict:
    out: dict[str, int] = {}
    for r in rows():
        out[r["kind"]] = out.get(r["kind"], 0) + 1
    return out
