"""Live mode: FastAPI + SSE. The static site replays files by default; this server is optional.

GET /api/run?target=<id>        server-sent events, one RunEvent per message (same shape as run.events).
                                If a finished run file exists and `fresh` is not set, it is replayed from
                                disk (fast, no LLM calls); otherwise a new run executes and streams live.
GET /api/prior-art?q=<text>     hybrid search over the claim index ("Has this move been made?").
GET /api/health
"""
from __future__ import annotations

import asyncio
import json

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from crux_lab.config import RUNS
from crux_lab.graph.index import INDEX_DIR, HybridIndex

app = FastAPI(title="Crux Lab API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])
_ix: dict[str, HybridIndex] = {}


def claims_index() -> HybridIndex:
    if "claims" not in _ix:
        _ix["claims"] = HybridIndex.load(INDEX_DIR / "claims")
    return _ix["claims"]


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "runs": sorted(p.stem for p in RUNS.glob("run-*.json"))}


@app.get("/api/prior-art")
def prior_art(q: str = Query(..., min_length=3, max_length=2000), k: int = 10) -> dict:
    from crux_lab.corpus.dedup import work_of

    ix = claims_index()
    k = min(k, 30)
    hits, seen = [], set()
    for h in ix.search(q, k=k * 4):        # collapse duplicate records of one work
        w = work_of(h.meta.get("paper_id", h.id))
        if w in seen:
            continue
        seen.add(w)
        hits.append(h)
        if len(hits) == k:
            break
    return {"query": q, "records_searched": len(ix),
            "hits": [{"claim_id": h.id, "text": h.text, "score": round(h.score, 4), **h.meta} for h in hits]}


async def _replay(run_file, speed: float):
    run = json.loads(run_file.read_text())
    prev = None
    for ev in run.get("events", []):
        if prev is not None and speed > 0:
            await asyncio.sleep(min(2.0, max(0.0, (ev["t"] - prev) / speed)))
        prev = ev["t"]
        yield {"event": "message", "data": json.dumps(ev, ensure_ascii=False)}
    yield {"event": "done", "data": json.dumps({"run_id": run["run_id"]})}


async def _live(target_id: str):
    from crux_lab.lab.run import find_target, run_target

    q: asyncio.Queue = asyncio.Queue()

    async def on_event(ev: dict):
        await q.put(ev)

    async def go():
        try:
            await run_target(find_target(target_id), on_event=on_event)
        except BaseException as e:  # noqa: BLE001 - surfaced to the client as an error event
            await q.put({"type": "error", "error": repr(e)[:300]})
        finally:
            await q.put(None)

    task = asyncio.create_task(go())
    try:
        while (ev := await q.get()) is not None:
            yield {"event": "message", "data": json.dumps(ev, ensure_ascii=False)}
        yield {"event": "done", "data": "{}"}
    finally:
        if not task.done():
            task.cancel()


@app.get("/api/run")
async def run(target: str, fresh: bool = False, speed: float = 20.0):
    f = RUNS / f"run-{target}.json"
    if not f.exists():
        f = RUNS / f"{target}.json"
    if f.exists() and not fresh:
        return EventSourceResponse(_replay(f, speed))
    if fresh:
        return EventSourceResponse(_live(target))
    raise HTTPException(404, f"no run for {target}; pass fresh=true to start one")
