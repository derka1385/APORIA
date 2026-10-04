"""APORIA local server: python3 server.py  ->  http://localhost:8740

Standard library only. Runs experiments in background threads and streams
every state change to the browser over Server-Sent Events.
"""

from __future__ import annotations

import json
import os
import random
import threading
import time
import traceback
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import engine
import ltm
import metrics
from profiles import TARGETS, policy

ROOT = Path(__file__).parent
RUNS = ROOT / "runs"
RUNS.mkdir(exist_ok=True)
PORT = int(os.environ.get("APORIA_PORT", 8740))
PROFILES = list(TARGETS)
PARALLEL = int(os.environ.get("APORIA_PARALLEL", 1))  # >1 runs reasoners in threads (hot laptop, faster)


class Job:
    """An event log that SSE clients replay from the start and then follow."""

    def __init__(self):
        self.events: list[dict] = []
        self.cv = threading.Condition()
        self.done = False

    def emit(self, e: dict):
        with self.cv:
            self.events.append(e)
            self.cv.notify_all()

    def finish(self):
        with self.cv:
            self.done = True
            self.cv.notify_all()


JOBS: dict[str, Job] = {}
LATEST: list[str] = []  # job ids in start order; /api/live follows the newest


def chat_models() -> list[str]:
    try:
        tags = json.loads(urllib.request.urlopen(engine.OLLAMA + "/api/tags", timeout=5).read())
        return [m["name"] for m in tags["models"] if "embed" not in m["name"]]
    except Exception:
        return []


def model_plan(condition: str, delta: float) -> list[str]:
    if condition != "model" or delta < 0.15:
        return [engine.MODEL] * len(PROFILES)
    env = [m for m in os.environ.get("APORIA_MODELS", "").split(",") if m]
    named = dict(m.split("=", 1) for m in env if "=" in m)  # profile=model, e.g. skeptic=lobbot-skeptic (lobbot_specs.py)
    if named:
        return [named.get(p, engine.MODEL) for p in PROFILES]
    variants = env or sorted(chat_models(), key=lambda m: m != engine.MODEL) or [engine.MODEL]
    return [variants[i % len(variants)] for i in range(len(PROFILES))]


def pol(name: str, delta: float, condition: str, quick: bool) -> dict:
    p = policy(name, delta, condition)
    if quick:  # half the steps: same policies, less heat
        p["budget"], p["min_steps"] = max(4, p["budget"] // 2), max(3, p["min_steps"] // 2)
    return p


def run_experiment(job: Job, question: str, condition: str, delta: float, seed: int, tag: dict, quick=False,
                   memory="readwrite") -> dict:
    models = model_plan(condition, delta)
    cfg = {"question": question, "condition": condition, "delta": delta, "seed": seed, "models": models,
           "quick": quick, "memory": memory, **tag}
    job.emit({"type": "run_start", **cfg, "profiles": PROFILES,
              "policies": {p: pol(p, delta, condition, quick) for p in PROFILES}, "quick": quick})

    def guarded(r, fn):
        try:
            fn()
        except Exception as ex:  # one reasoner failing must not kill the experiment
            traceback.print_exc()
            job.emit({"type": "error", "agent": r.name, "msg": str(ex), **tag})
            r.s.conclusion = r.s.conclusion or {"position": r.s.hypothesis, "stance": "qualified", "credence": 0.5,
                                                "key_reasons": [], "open_objection": "", "error": str(ex)}

    def go(i_name):
        i, name = i_name
        r = engine.Reasoner(name, question, pol(name, delta, condition, quick), models[i], seed + i,
                            emit=lambda e: job.emit({**e, **tag}), memory=memory)
        try:
            r.run()
        except Exception as ex:  # one reasoner failing must not kill the experiment
            traceback.print_exc()
            job.emit({"type": "error", "agent": name, "msg": str(ex), **tag})
            r.s.conclusion = r.s.conclusion or {"position": r.s.hypothesis, "stance": "qualified", "credence": 0.5,
                                                "key_reasons": [], "open_objection": "", "error": str(ex)}
        return name, r

    if PARALLEL > 1:
        with ThreadPoolExecutor(PARALLEL) as ex:
            reasoners = dict(ex.map(go, enumerate(PROFILES)))
    else:  # default: round-robin, one step per reasoner per turn, one LLM call at a time
        reasoners = {}
        for i, name in enumerate(PROFILES):
            reasoners[name] = engine.Reasoner(name, question, pol(name, delta, condition, quick), models[i], seed + i,
                                              emit=lambda e: job.emit({**e, **tag}), memory=memory)
        live = list(reasoners.values())
        for r in live:
            guarded(r, r.op_start)
        while live:
            for r in list(live):
                if r.s.conclusion is None:
                    guarded(r, r.step)
                if r.s.conclusion is not None:
                    live.remove(r)
    agents = {n: r.s.snapshot() for n, r in reasoners.items()}
    # a reasoner whose LLM calls mostly came back empty did not reason: the run is kept but flagged, never analysed
    cfg["failed"] = metrics.failed(agents)
    m = metrics.compute(agents)
    job.emit({"type": "metrics", "metrics": m, **cfg})
    rid = time.strftime("%Y%m%d-%H%M%S") + f"-{condition}-{delta:.1f}"
    for r in reasoners.values() if memory == "readwrite" else []:  # what this session learned outlives it
        try:
            ltm.write(r.memories(rid))
        except Exception:
            traceback.print_exc()
    (RUNS / f"{rid}.json").write_text(json.dumps({"id": rid, **cfg, "agents": agents, "metrics": m}, indent=1))
    return m


def start(body: dict) -> str:
    q = str(body.get("question") or "").strip()[:500] or "Is personal identity dependent on psychological continuity?"
    cond = body.get("condition") if body.get("condition") in ("base", "prompt", "architecture", "model") else "architecture"
    seed = int(body.get("seed") or random.randint(1, 10**6))
    deltas = body.get("deltas") or [float(body.get("delta", 0.6))]
    deltas = [max(0.0, min(1.0, float(d))) for d in deltas][:6]
    jid, job = uuid.uuid4().hex[:8], Job()
    JOBS[jid] = job
    LATEST.append(jid)

    def worker():
        try:
            for k, d in enumerate(deltas):
                run_experiment(job, q, cond, d, seed, {"run": k, "runs": len(deltas)}, bool(body.get("quick")),
                               body.get("memory") if body.get("memory") in ("off", "read") else "readwrite")
        except Exception as ex:
            traceback.print_exc()
            job.emit({"type": "error", "msg": str(ex)})
        job.emit({"type": "done"})
        job.finish()

    threading.Thread(target=worker, daemon=True).start()
    return jid


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(ROOT / "static"), **kw)

    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")  # a local lab: always serve the current files
        self.send_header("Access-Control-Allow-Origin", "*")  # the visual engine runs on another localhost port
        super().end_headers()

    def send_json(self, obj, code=200):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if self.path == "/api/run":
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            return self.send_json({"id": start(body)})
        self.send_error(404)

    def do_GET(self):
        if self.path.startswith("/api/events/"):
            return self.stream(self.path.rsplit("/", 1)[1])
        if self.path == "/api/live":
            return self.live()
        if self.path == "/api/memory":
            return self.send_json(ltm.stats())
        if self.path == "/api/models":
            return self.send_json({"default": engine.MODEL, "available": chat_models(), "profiles": PROFILES})
        if self.path == "/api/runs":
            rows = []
            for f in sorted(RUNS.glob("*.json")):
                d = json.loads(f.read_text())
                rows.append({k: d[k] for k in ("id", "question", "condition", "delta", "models")} |
                            {"metrics": {k: v for k, v in d["metrics"].items() if not isinstance(v, dict)}})
            return self.send_json(rows)
        if self.path.startswith("/api/runs/"):
            f = RUNS / (Path(self.path).name + ".json")
            return self.send_json(json.loads(f.read_text())) if f.exists() else self.send_error(404)
        return super().do_GET()

    def live(self):
        """Follow whatever job is newest, switching when a new one starts (for the visual engine)."""
        self.sse_headers()
        while True:
            while not LATEST:
                time.sleep(1)
                if not self.write(": waiting\n\n"):
                    return
            jid = LATEST[-1]
            if not self.stream(jid, headers=False, until_newer=True):
                return

    def sse_headers(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.end_headers()

    def write(self, payload: str) -> bool:
        try:
            self.wfile.write(payload.encode())
            self.wfile.flush()
            return True
        except (BrokenPipeError, ConnectionResetError):
            return False

    def stream(self, jid: str, headers=True, until_newer=False):
        job = JOBS.get(jid)
        if not job:
            return self.send_error(404)
        if headers:
            self.sse_headers()
        i = 0
        try:
            while True:
                with job.cv:
                    while i >= len(job.events) and not job.done:
                        job.cv.wait(15)
                        if i >= len(job.events) and not job.done:
                            break  # heartbeat
                    batch, done = job.events[i:], job.done
                i += len(batch)
                payload = "".join(f"data: {json.dumps({**e, 'job': jid})}\n\n" for e in batch) or ": ping\n\n"
                if not self.write(payload):
                    return False
                if until_newer and LATEST[-1] != jid:
                    return True
                if done and i >= len(job.events):
                    if not until_newer:
                        return True
                    while LATEST[-1] == jid:  # idle until the next job starts
                        time.sleep(1)
                        if not self.write(": idle\n\n"):
                            return False
                    return True
        except (BrokenPipeError, ConnectionResetError):
            return False


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"APORIA lab on http://localhost:{PORT}  (model {engine.MODEL})")
    srv.serve_forever()
