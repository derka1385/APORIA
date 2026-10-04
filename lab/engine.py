"""Cognitive engine: argument graph, metacognition, curiosity, experiments, learning, controller.

One Reasoner = one State (a typed argument graph plus scalar state) + one
policy. Each step:

  metacognition reads the graph  -> signals ("overconfident", "fragile", ...)
  controller scores every op     -> state drives + signals, x policy weight x learned value
  attention picks the branch     -> softmax over curiosity (expected information value)
  the op runs (one LLM call and/or a tool) and edits the graph
  the step's information gain updates the learned value of that op and branch

Events for visualisation are emitted as `cog` events (see STREAM.md).
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import time
import urllib.request
from pathlib import Path

import ltm
import tools

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
MODEL = os.environ.get("APORIA_MODEL", "qwen2.5:3b")
EMBED_MODEL = os.environ.get("APORIA_EMBED", "nomic-embed-text")
LITERATURE = json.loads((Path(__file__).parent / "literature.json").read_text())

ATTACK = {"objection", "counterexample", "counterfactual", "contradiction"}
SAME_IDEA = 0.88  # cosine above which two texts count as the same idea (nomic-embed-text)


# ---------------------------------------------------------------- LLM access

def _post(path: str, body: dict, timeout=180) -> dict:
    req = urllib.request.Request(OLLAMA + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def llm_json(system: str, user: str, policy: dict, model: str, seed: int) -> dict:
    body = {"model": model, "stream": False, "format": "json",
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "options": {"temperature": policy["llm_temp"], "top_p": policy["top_p"], "seed": seed,
                        "num_predict": 500, "num_ctx": 4096}}
    for attempt in range(2):
        try:
            out = json.loads(_post("/api/chat", body)["message"]["content"])
            if isinstance(out, dict):
                return out
        except (json.JSONDecodeError, KeyError):
            body["options"]["seed"] = seed + 1000 + attempt
    return {}


_embed_cache: dict[str, list[float]] = {}
_embed_ok = True


def embed(texts: list[str]) -> list[list[float]]:
    """Ollama embeddings, cached; falls back to hashed bag-of-words if the model is missing."""
    global _embed_ok
    todo = [t for t in dict.fromkeys(texts) if t not in _embed_cache]
    if todo and _embed_ok:
        try:
            vecs = _post("/api/embed", {"model": EMBED_MODEL, "input": todo})["embeddings"]
            _embed_cache.update(zip(todo, vecs))
        except Exception:
            _embed_ok = False  # ponytail: silent switch to bag-of-words for the whole process
    for t in todo:
        _embed_cache.setdefault(t, _bow(t))
    return [_embed_cache[t] for t in texts]


def _bow(text: str, dim=512) -> list[float]:
    v = [0.0] * dim
    for w in re.findall(r"[a-z]{3,}", text.lower()):
        v[hash(w) % dim] += 1
    return v


def cos(a, b) -> float:
    if len(a) != len(b):  # bow vs model vector after a fallback: incomparable
        return 0.0
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0


def clip(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, float(x)))


def num(v, default=0.5):
    try:
        return clip(float(v))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------- tools wired to engine data

def literature_search(query: str, k: int, spread: float = 0.0, rng: random.Random | None = None) -> list[dict]:
    """Nearest literature entries; with spread > 0 some slots go to deliberately distant ones."""
    if k <= 0:
        return []
    qv, *ev = embed([query] + [e["title"] + ". " + e["text"] for e in LITERATURE])
    ranked = [e for _, e in sorted(zip((cos(qv, v) for v in ev), LITERATURE), key=lambda x: -x[0])]
    n_far = int(round(k * spread * 0.5))
    far = (rng or random).sample(ranked[len(ranked) // 2:], min(n_far, len(ranked) // 2))
    return ranked[: k - n_far] + far


def ltm_search(query: str, k: int, kinds=None, min_sim=0.6) -> list[dict]:
    return ltm.search(embed([query])[0], cos, k, kinds, min_sim)


def similarity(a: str, b: str) -> float:
    va, vb = embed([a, b])
    return round(cos(va, vb), 3)


def graph_query(state: "State", kind: str, node: str | None = None):
    live = {n["id"]: n for n in state.live()}
    if kind == "weakest_assumption":
        asm = [n for n in live.values() if n["type"] == "assumption" and (node is None or n["parent"] == node)]
        return min(asm, key=lambda n: n["conf"] - 0.3 * n.get("load", 0.5), default=None)
    if kind == "dependents":
        out, todo = [], [node]
        while todo:
            cur = todo.pop()
            for n in live.values():
                if n["parent"] == cur:
                    out.append(n["id"]); todo.append(n["id"])
        return out
    if kind == "attackers":
        return [e["src"] for e in state.edges if e["dst"] == node and e["rel"] in ("attacks", "tests")
                and e["src"] in live]
    raise ValueError(kind)


tools.register_engine_tools(literature_search, ltm_search, similarity, graph_query)


# ---------------------------------------------------------------- state

class State:
    def __init__(self, question: str):
        self.question = question
        self.hypothesis = ""
        self.root: str | None = None
        self.nodes: dict[str, dict] = {}
        self.edges: list[dict] = []          # {src, dst, rel}
        self.experiments: list[dict] = []    # {id, kind, node, target, status, gain, step}
        self.confidence = 0.5
        self.uncertainty = 0.6
        self.novelty = 0.8
        self.surprise = 0.0
        self.history: list[dict] = []
        self.series: list[dict] = []
        self.step = 0
        self.conclusion: dict | None = None
        self.signals: list[dict] = []
        self.values: dict[str, float] = {}   # learned information value per op
        self.tool_log: list[dict] = []
        self.recalls: list[dict] = []

    def add(self, kind: str, text: str, parent: str | None, rel: str | None = None, conf=0.5, **extra) -> str | None:
        text = (text or "").strip()
        if not text or any(n["text"].lower() == text.lower() for n in self.nodes.values()):
            return None
        nid = f"n{len(self.nodes)}"
        self.nodes[nid] = {"id": nid, "type": kind, "text": text[:400], "parent": parent, "status": "open",
                           "conf": conf, "curiosity": 0.5, "novelty": 0.5, "yield": 1.0, "intuition": 0.5,
                           "surprise": 0.0, "step": self.step, **extra}
        if parent and rel:
            self.edges.append({"src": nid, "dst": parent, "rel": rel})
        return nid

    def live(self) -> list[dict]:
        return [n for n in self.nodes.values() if n["status"] != "rejected"]

    def pending(self) -> list[dict]:
        return [e for e in self.experiments if e["status"] == "pending"]

    def snapshot(self) -> dict:
        return {"hypothesis": self.hypothesis, "root": self.root, "nodes": list(self.nodes.values()),
                "edges": self.edges, "experiments": self.experiments, "confidence": self.confidence,
                "uncertainty": self.uncertainty, "novelty": self.novelty, "surprise": self.surprise,
                "history": self.history, "series": self.series, "step": self.step, "conclusion": self.conclusion,
                "signals": self.signals, "values": self.values, "tool_log": self.tool_log, "recalls": self.recalls,
                "curiosity": max([n["curiosity"] for n in self.live()] or [0]),
                # kept for the v1 UI: experiments still open are the unresolved conflicts
                "conflicts": [{"objection": e["node"], "target": e["target"],
                               "status": "open" if e["status"] == "pending" else "resolved"} for e in self.experiments]}


# ---------------------------------------------------------------- reasoner

SYSTEM = ("You are one module inside an explicit reasoning architecture working on a philosophical question. "
          "Do exactly the operation asked, be concrete and philosophically precise, and reply with JSON only.")


class Reasoner:
    def __init__(self, name: str, question: str, policy: dict, model: str, seed: int, emit=lambda e: None):
        self.name, self.policy, self.model, self.seed = name, policy, model, seed
        self.s = State(question)
        self.rng = random.Random(seed)
        self.budget = policy["budget"]
        self.emit = emit
        self.vec: dict[str, list[float]] = {}
        self.rejected_hyp: list[list[float]] = []
        self.s.values = {op: 0.15 for op in policy["weights"]}

    # ------------------------------------------------ events
    def cog(self, kind: str, **kw):
        self.emit({"type": "cog", "agent": self.name, "step": self.s.step, "t": round(time.time() * 1000),
                   "kind": kind, **kw})

    # ------------------------------------------------ graph edits with side effects
    def new(self, kind, text, parent, rel=None, conf=0.5, **extra) -> str | None:
        """Add a node; compute its novelty; merge recurring assumptions instead of duplicating them."""
        s = self.s
        text = str(text or "").strip()
        if not text or text.lower() in ("none", "null") or re.fullmatch(r"\[?n\d+\]?", text):
            return None  # empty, or the LLM echoed a node id instead of content
        v = embed([text])[0]
        same = [(cos(v, self.vec[n["id"]]), n) for n in s.live() if n["id"] in self.vec and n["type"] == kind]
        best = max(same, key=lambda x: x[0], default=(0, None))
        if kind == "assumption" and best[0] >= SAME_IDEA:
            n = best[1]  # the same hidden assumption surfaced again: it matters more
            n["recur"] = n.get("recur", 1) + 1
            n["load"] = clip(n.get("load", 0.5) + 0.2)
            self.cog("reinforce", node=n["id"], recur=n["recur"])
            return None
        if best[0] >= 0.95:
            return None
        nid = s.add(kind, text, parent, rel, conf, **extra)
        if not nid:
            return None
        self.vec[nid] = v
        others = [self.vec[i] for i in self.vec if i != nid]
        mem = [r["sim"] for r in ltm.search(v, cos, 1, min_sim=0)] if self.policy["ltm_k"] else []
        s.nodes[nid]["novelty"] = round(1 - max([cos(v, o) for o in others] + mem + [0]), 3)
        return nid

    def reject(self, nid: str, why: str = ""):
        s = self.s
        n = s.nodes[nid]
        if n["status"] == "rejected":
            return
        n["status"] = "rejected"
        if n["type"] == "hypothesis" and nid in self.vec:
            self.rejected_hyp.append(self.vec[nid])
        for e in s.experiments:
            if e["status"] == "pending" and nid in (e["node"], e["target"]):
                e["status"] = "moot"
        self.cog("rejection", node=nid, node_type=n["type"], why=why)
        for c in list(s.nodes.values()):
            if c["parent"] == nid and c["status"] == "open":
                self.reject(c["id"], "parent rejected")

    def experiment(self, kind: str, node: str, target: str):
        s = self.s
        s.experiments.append({"id": f"x{len(s.experiments)}", "kind": kind, "node": node, "target": target,
                              "status": "pending", "gain": 0.0, "step": s.step})
        self.cog("contradiction", node=node, target=target, experiment=s.experiments[-1]["id"], via=kind)

    def set_root_conf(self, c: float):
        s = self.s
        s.confidence = clip(c)
        if s.root:
            s.nodes[s.root]["conf"] = s.confidence
            if s.confidence < self.policy["reject_below"] and s.nodes[s.root]["status"] != "rejected":
                self.reject(s.root, "confidence collapsed")

    def use(self, name: str, *a, **kw):
        ok, out = tools.call(name, self.policy["tools"], *a, **kw)
        summary = (json.dumps(out)[:160] if ok else str(out)[:160])
        self.s.tool_log.append({"step": self.s.step, "tool": name, "ok": ok, "summary": summary})
        self.cog("tool", tool=name, ok=ok, summary=summary)
        return ok, out

    def can(self, name: str) -> bool:
        return name in self.policy["tools"]

    # ------------------------------------------------ metacognition (structured state, no LLM)
    def assess(self, nid: str) -> dict:
        s = self.s
        live = {n["id"]: n for n in s.live()}
        kids = [n for n in live.values() if n["parent"] == nid]
        support = [n for n in kids if n["type"] in ("evidence", "premise", "response")
                   and n["status"] in ("supported", "open", "stable")]
        # an unverified premise is barely evidence; retrieved, verified or defended material is
        weight = lambda n: (1.0 if n["type"] == "evidence" else 0.6 if n["type"] == "response"
                            else 0.8 if n["status"] == "supported" else 0.15)
        ev = 1 - math.exp(-sum(n["conf"] * weight(n) for n in support))
        attackers = [e["src"] for e in s.edges if e["dst"] == nid and e["rel"] in ("attacks", "tests") and e["src"] in live]
        unresolved = [e for e in s.pending() if e["target"] == nid]
        asm = [n for n in kids if n["type"] == "assumption"]
        weakest = min(asm, key=lambda n: n["conf"] - 0.3 * n.get("load", 0.5), default=None)
        sourced = [n for n in support if n.get("source")]
        c = live[nid]["conf"] if nid in live else 0
        return {"evidence": round(ev, 3), "attackers": len(attackers), "unresolved": len(unresolved),
                "assumptions": len(asm), "weakest": weakest["id"] if weakest else None,
                "weakest_conf": weakest["conf"] if weakest else 1.0, "uncertainty": round(1 - abs(2 * c - 1), 3),
                "source_quality": round(len(sourced) / len(support), 2) if support else 0.0,
                "weakest_tested": bool(weakest) and any(e["target"] == weakest["id"] for e in s.experiments),
                "objected": any(s.nodes[e["src"]]["type"] in ("objection", "counterexample") for e in s.edges
                                if e["dst"] == nid and e["rel"] == "attacks"),
                "tested": any(e["kind"] == "counterfactual" and e["target"] == nid for e in s.experiments),
                "formal": bool(live[nid].get("formalized")) if nid in live else True}

    def metacognition(self) -> list[dict]:
        """Rules over observed graph state that produce pressure on specific ops and nodes."""
        s, out = self.s, []
        root = s.root
        if not root:
            return out
        r = s.nodes[root]
        if r["status"] == "rejected":
            return [{"signal": "hypothesis rejected", "op": "revise", "node": root, "strength": 1.5}]
        a = self.assess(root)
        if r["conf"] > 0.62 and a["evidence"] < 0.4:
            out.append({"signal": "confident but weakly supported", "op": "doubt", "node": root,
                        "strength": round(r["conf"] - a["evidence"], 2)})
        if not a["objected"] and s.step >= 1:
            out.append({"signal": "no objection raised yet", "op": "doubt", "node": root, "strength": 0.6})
        if a["weakest"] and not a["weakest_tested"] and r["conf"] > 0.45 and a["weakest_conf"] < 0.55:
            w = s.nodes[a["weakest"]]
            k = round((1 - w["conf"]) * (0.5 + w.get("load", 0.5)), 2)
            out.append({"signal": "conclusion rests on a weak assumption", "op": "counterfactual", "node": w["id"], "strength": k})
            out.append({"signal": "conclusion rests on a weak assumption", "op": "reason", "node": w["id"], "strength": round(k * 0.6, 2)})
        for n in s.live():
            if n["type"] in ATTACK or n["status"] == "rejected":
                continue
            pend = sum(1 for e in s.pending() if e["target"] == n["id"])
            if pend:
                out.append({"signal": "unresolved contradiction", "op": "adjudicate", "node": n["id"],
                            "strength": round(min(1.3, 0.5 * pend + (0.3 if n["id"] == root else 0)), 2)})
        if a["uncertainty"] > 0.7 and a["evidence"] < 0.4:
            out.append({"signal": "uncertain and under-evidenced", "op": "memory", "node": root, "strength": 0.6})
            out.append({"signal": "uncertain and under-evidenced", "op": "inquire", "node": root, "strength": 0.4})
        if a["assumptions"] == 0:
            out.append({"signal": "assumptions unexamined", "op": "introspect", "node": root, "strength": 0.7})
        if not a["tested"] and s.step >= 2:
            out.append({"signal": "never tested counterfactually", "op": "counterfactual", "node": root, "strength": 0.6})
        if not a["formal"] and len([n for n in s.live() if n["parent"] == root and n["type"] == "premise"]) >= 2:
            out.append({"signal": "argument not formally checked", "op": "formalize", "node": root, "strength": 0.55})
        gains = [h.get("gain", 0) for h in s.history[-3:]]
        if len(gains) == 3 and max(gains) < 0.04:
            out.append({"signal": "stagnating: last steps produced no information", "op": "imagine", "node": None, "strength": 0.6})
            out.append({"signal": "stagnating: last steps produced no information", "op": "revise", "node": root, "strength": 0.3})
        q = [n for n in s.live() if n["type"] == "question" and n["status"] == "open"]
        if q:
            out.append({"signal": "open question", "op": "inquire", "node": q[0]["id"], "strength": 0.5})
        return out

    # ------------------------------------------------ curiosity = expected information value
    def curiosity(self):
        s = self.s
        root = s.root
        for n in s.live():
            a = self.assess(n["id"])
            depth, cur = 0, n
            while cur["parent"] and depth < 5:
                cur, depth = s.nodes[cur["parent"]], depth + 1
            importance = (1.0 if n["id"] == root else 0.8 ** depth) * (1 + 0.15 * len(graph_query(s, "dependents", n["id"])))
            on_root = n["parent"] == root or n["id"] == root
            eig = (a["uncertainty"] * importance * (1.0 if on_root else 0.6)
                   * (0.4 + 0.6 * (1 - a["evidence"])) * (0.5 + 0.5 * n["novelty"])
                   * (1 + 0.5 * a["unresolved"] + 0.2 * a["attackers"])
                   * n["yield"] * (0.7 + 0.6 * n["intuition"]))
            n["curiosity"] = round(eig, 3)
        top = max(s.live(), key=lambda n: n["curiosity"], default=None)
        if top:
            self.cog("curiosity", node=top["id"], value=top["curiosity"])

    def pick_focus(self, op: str, hint: str | None) -> str | None:
        s = self.s
        if op in ("revise", "conclude"):
            return s.root
        if hint and hint in s.nodes and s.nodes[hint]["status"] != "rejected":
            return hint
        cands = [n for n in s.live() if n["type"] not in ("evidence",) and n["status"] != "stable"]
        if op in ("doubt", "counterfactual", "reason", "formalize", "introspect"):
            cands = [n for n in cands if n["type"] not in ATTACK and n["type"] != "question"] or cands
        if op == "inquire":
            cands = [n for n in cands if n["type"] != "question" or n["status"] == "open"] or cands
        if not cands:
            return s.root
        t = self.policy["explore"]
        if t < 0.05:
            return max(cands, key=lambda n: n["curiosity"])["id"]
        m = max(n["curiosity"] for n in cands)
        w = [math.exp((n["curiosity"] - m) / (t * max(m, 0.05))) for n in cands]
        return self.rng.choices(cands, w)[0]["id"]

    # ------------------------------------------------ controller
    def multiplier(self, op: str) -> float:
        v = self.s.values
        mean = sum(v.values()) / len(v)
        return clip(1 + self.policy["learning_rate"] * (v[op] - mean) / (mean + 0.05), 0.4, 2.2)

    def drives(self, signals) -> dict[str, float]:
        s, p = self.s, self.policy
        live = s.live()
        unverified = sum(1 for n in live if n["status"] == "open") / max(1, len(live))
        d = {
            "memory": 0.4 * s.novelty * (1 - s.confidence),
            "reason": 0.4 * s.uncertainty + 0.3 * unverified,
            "imagine": 0.3 * (1 - s.novelty) + 0.2 * max([n["curiosity"] for n in live] or [0]),
            "intuit": 0.25 * (len(live) > 6) + 0.15 * (len(s.history) - max([i for i, h in enumerate(s.history) if h["op"] == "intuit"] or [0]) > 4),
            "introspect": 0.3 * s.novelty,
            "doubt": 0.3 * s.confidence,
            "counterfactual": 0.2 * s.confidence,
            "formalize": 0.1,
            "inquire": 0.2 * s.uncertainty,
            "adjudicate": 0.3 * min(2, len(s.pending())),
            "revise": 0.4 * s.surprise,
            "conclude": 0.0,
        }
        for sig in signals:
            d[sig["op"]] += sig["strength"]
        if (s.step >= p["min_steps"] and s.confidence >= p["stop_conf"] and not s.pending()
                and s.nodes[s.root]["status"] != "rejected"):
            d["conclude"] = 1.6
        # access constraints are hard: no memory op without any memory access, no formalize without logic
        if not ((p["lit_k"] and self.can("literature_search")) or (p["ltm_k"] and self.can("memory_search"))):
            d["memory"] = 0
        if not self.can("logic_check"):
            d["formalize"] = 0
        if not s.pending():
            d["adjudicate"] = 0
        last = [h["op"] for h in s.history[-2:]]
        if len(last) == 2 and last[0] == last[1]:
            d[last[0]] *= 0.3  # the same op three times in a row is damped
        return {op: p["weights"][op] * self.multiplier(op) * v for op, v in d.items()}

    def choose(self) -> tuple[str, dict, str | None]:
        s = self.s
        s.signals = self.metacognition()
        if s.step >= self.budget:
            return "conclude", {}, s.root
        sc = self.drives(s.signals)
        t = max(0.05, self.policy["ctrl_temp"])
        m = max(sc.values())
        w = {op: math.exp((v - m) / t) if v > 0 else 0.0 for op, v in sc.items()}
        z = sum(w.values()) or 1
        op = self.rng.choices(list(w), list(w.values()))[0] if sum(w.values()) else "reason"
        hint = max((g for g in s.signals if g["op"] == op), key=lambda g: g["strength"], default={}).get("node")
        return op, {k: round(v / z, 3) for k, v in w.items()}, hint

    # ------------------------------------------------ run loop
    def run(self):
        s = self.s
        self.op_start()
        while s.conclusion is None:
            self.curiosity()
            op, probs, hint = self.choose()
            focus = self.pick_focus(op, hint)
            why = [g["signal"] for g in s.signals if g["op"] == op]
            self.emit({"type": "op", "agent": self.name, "op": op, "focus": focus, "probs": probs, "why": why})
            self.cog("attention", node=focus, op=op, concentration=probs.get(op, 0))
            before = (s.confidence, s.uncertainty, len(s.nodes), sum(e["status"] != "pending" for e in s.experiments))
            t0 = time.time()
            getattr(self, "op_" + op)(focus)
            gain = self.learn(op, focus, before)
            s.step += 1
            s.surprise *= 0.75  # surprise is transient
            if s.surprise > 0.45 and self.budget < self.policy["budget"] + 3 * self.policy["surprise_bonus"]:
                self.budget += self.policy["surprise_bonus"]  # a surprising branch earns more compute
                self.cog("compute", budget=self.budget)
            s.history.append({"step": s.step, "op": op, "focus": focus, "probs": probs, "why": why,
                              "gain": gain, "ms": round((time.time() - t0) * 1000),
                              "d_conf": round(s.confidence - before[0], 3), "d_unc": round(s.uncertainty - before[1], 3)})
            self.tick()

    def learn(self, op: str, focus: str | None, before) -> float:
        """Information gain of this step -> op value (routing) and branch yield (attention)."""
        s = self.s
        resolved = sum(e["status"] != "pending" for e in s.experiments) - before[3]
        gain = (abs(s.confidence - before[0]) + 0.5 * abs(s.uncertainty - before[1])
                + 0.05 * min(3, len(s.nodes) - before[2]) + 0.1 * resolved)
        gain = round(min(1.0, gain), 3)
        old = s.values[op]
        s.values[op] = round(0.7 * old + 0.3 * gain, 4)
        if abs(self.multiplier(op) - 1) > 0.25:
            self.cog("learning", op=op, value=s.values[op], multiplier=round(self.multiplier(op), 2))
        if focus in s.nodes and gain < 0.03:
            s.nodes[focus]["yield"] = round(s.nodes[focus]["yield"] * 0.6, 3)  # dead-end branches lose priority
        return gain

    def tick(self):
        s = self.s
        s.series.append({k: round(getattr(s, k), 3) for k in ("confidence", "uncertainty", "novelty", "surprise")})
        open_x = len(s.pending())
        self.cog("levels", confidence=s.confidence, uncertainty=s.uncertainty, novelty=s.novelty,
                 surprise=round(s.surprise, 3), curiosity=max([n["curiosity"] for n in s.live()] or [0]),
                 contradiction=round(min(1, open_x / 3), 3))
        self.emit({"type": "state", "agent": self.name, "state": s.snapshot(), "budget": self.budget})

    def context(self, focus: str | None) -> str:
        s = self.s
        nodes = sorted(s.live(), key=lambda n: n["curiosity"] + (1 if n["id"] == s.root else 0), reverse=True)
        nodes = nodes[: self.policy["context"]]
        if focus and focus in s.nodes and s.nodes[focus] not in nodes:
            nodes.append(s.nodes[focus])
        lines = [f"[{n['id']}] {n['type']} ({n['status']}, conf {n['conf']:.2f}): {n['text']}" for n in nodes]
        return (f"Question: {s.question}\nCurrent hypothesis: {s.hypothesis or '(none yet)'}\n"
                "Visible argument graph:\n" + ("\n".join(lines) or "(empty)"))

    def ask(self, instruction: str, focus: str | None) -> dict:
        system = SYSTEM + (" " + self.policy["persona"] if self.policy["persona"] else "")
        return llm_json(system, self.context(focus) + "\n\n" + instruction, self.policy, self.model,
                        self.seed * 1000 + self.s.step)

    def text(self, nid):
        return self.s.nodes[nid]["text"] if nid in self.s.nodes else ""

    # ------------------------------------------------ operations
    def op_start(self):
        s = self.s
        out = self.ask('Operation START. Propose an initial answer to the question as a one-sentence hypothesis, and '
                       'the premises it rests on. JSON: {"hypothesis": str, "premises": [str, str]}', None)
        s.hypothesis = str(out.get("hypothesis") or "No initial hypothesis.")
        s.root = self.new("hypothesis", s.hypothesis, None, conf=0.5)  # same neutral prior for every reasoner
        for p in (out.get("premises") or [])[:3]:
            self.new("premise", p, s.root, "supports")
        self.recall_start()
        s.confidence = s.nodes[s.root]["conf"]
        s.history.append({"step": 0, "op": "start", "focus": None, "probs": {}, "why": [], "gain": 0, "ms": 0,
                          "d_conf": 0, "d_unc": 0})
        self.tick()

    def recall_start(self):
        """Long-term memory shapes the prior: was this explored before, and how did it end?"""
        s, p = self.s, self.policy
        if not (p["ltm_k"] and self.can("memory_search")):
            return
        ok, past_q = self.use("memory_search", s.question, 3, ["question"], 0.85)
        for q in (past_q if ok else []):
            s.recalls.append({"kind": "question", "text": q["text"], "outcome": q["outcome"], "sim": q["sim"]})
            self.cog("recall", node=s.root, memory_kind="question", outcome=q["outcome"], sim=q["sim"])
        ok, past_h = self.use("memory_search", s.hypothesis, p["ltm_k"], ["hypothesis"], 0.8)
        for h in (past_h if ok else []):
            shift = {"rejected": -0.12, "survived": 0.08}.get(h["outcome"], 0) * h["sim"]
            if shift:
                s.nodes[s.root]["conf"] = clip(s.nodes[s.root]["conf"] + shift)
                s.recalls.append({"kind": "hypothesis", "text": h["text"], "outcome": h["outcome"], "sim": h["sim"]})
                self.cog("recall", node=s.root, memory_kind="hypothesis", outcome=h["outcome"], sim=h["sim"])

    def op_memory(self, focus):
        s, p = self.s, self.policy
        query = s.question + " " + self.text(focus)
        lit = []
        if p["lit_k"] and self.can("literature_search"):
            ok, lit = self.use("literature_search", query, p["lit_k"], p["lit_spread"], self.rng)
            lit = lit if ok else []
        # long-term memory: objections that defeated similar claims before come back as live challenges
        if p["ltm_k"] and self.can("memory_search"):
            ok, past = self.use("memory_search", self.text(focus) or query, p["ltm_k"],
                                ["objection", "counterexample", "counterfactual", "unresolved"], 0.7)
            for m in (past if ok else []):
                if m["kind"] == "unresolved":
                    nid = self.new("question", m["text"], focus, "refines", source="memory")
                elif m["outcome"] == "defeated":
                    nid = self.new("objection", m["text"], focus, "attacks", 0.6, source="memory")
                    if nid:
                        self.experiment("recalled", nid, focus)
                else:
                    nid = None
                if nid:
                    s.recalls.append({"kind": m["kind"], "text": m["text"], "outcome": m["outcome"], "sim": m["sim"]})
                    self.cog("recall", node=nid, memory_kind=m["kind"], outcome=m["outcome"], sim=m["sim"])
        if lit:
            listing = "\n".join(f"<{e['id']}> {e['title']}: {e['text']}" for e in lit)
            out = self.ask(f'Operation MEMORY. Focus node: {focus}. Literature retrieved for you:\n{listing}\n\n'
                           'Extract up to 3 pieces of relevant evidence or established positions for the focus. Mark '
                           'whether each supports or undermines the focus. JSON: {"evidence": [{"text": str, "source": '
                           'source id, "supports": true|false}]}', focus)
            for e in (out.get("evidence") or [])[:3]:
                if not isinstance(e, dict):
                    continue
                supports = e.get("supports") is not False
                nid = self.new("evidence", e.get("text"), focus, "supports" if supports else "attacks", 0.7,
                               source=str(e.get("source") or "literature"))
                if not nid:
                    continue
                self.cog("association", node=nid, source=s.nodes[nid]["source"])
                if not supports and focus:
                    self.experiment("evidence", nid, focus)
        s.novelty = clip(s.novelty * 0.75)
        s.uncertainty = clip(s.uncertainty - 0.04 * len(lit))

    def op_reason(self, focus):
        s, p = self.s, self.policy
        out = self.ask(f'Operation REASON. Check whether node {focus} actually follows from, or is supported by, what '
                       'is in the graph. Name any missing premise it silently needs. JSON: {"verdict": "valid"|'
                       '"invalid"|"unsupported", "confidence": 0-1, "missing_premise": str or "", "why": str}', focus)
        n = s.nodes[focus]
        v, c = str(out.get("verdict", "unsupported")).lower(), num(out.get("confidence"))
        if v == "valid" and c >= p["accept"]:
            n["status"], n["conf"] = "supported", n["conf"] + 0.5 * max(0.0, c - n["conf"])
            s.uncertainty = clip(s.uncertainty - 0.1)
        elif v == "invalid" and focus != s.root:
            self.reject(focus, "does not follow")
            s.uncertainty = clip(s.uncertainty + 0.1)
        else:  # unsupported, invalid root, or valid below this policy's acceptance threshold
            n["conf"] = clip(n["conf"] - (0.15 if v == "invalid" else 0.08))
            s.uncertainty = clip(s.uncertainty + 0.05)
        if out.get("missing_premise"):
            self.new("assumption", out["missing_premise"], focus, "depends_on", 0.45, load=0.6)
        if focus == s.root:
            self.set_root_conf(n["conf"])
        elif n["status"] == "supported" and n["parent"] == s.root:
            self.set_root_conf(s.confidence + 0.05)
        self.prune_assumptions()

    def op_imagine(self, focus):
        s, p = self.s, self.policy
        out = self.ask(f'Operation IMAGINE. For node {focus or s.root}, invent {p["branch"]} alternative hypotheses or '
                       'thought experiments that would test it or show a different answer. JSON: {"items": [{"kind": '
                       '"thought_experiment"|"alternative", "text": str, "implication": str}]}', focus)
        for it in (out.get("items") or [])[: p["branch"]]:
            if isinstance(it, dict):
                kind = "thought_experiment" if "thought" in str(it.get("kind")) else "alternative"
                text = str(it.get("text") or "") + (f" → {it['implication']}" if it.get("implication") else "")
                if self.new(kind, text, focus or s.root, "analogous_to" if kind == "thought_experiment" else "refines", 0.4):
                    s.novelty = clip(s.novelty + 0.1)

    def op_intuit(self, _focus):
        s = self.s
        out = self.ask('Operation INTUIT. Before verifying anything, rate how promising each visible node is to explore '
                       'next (0-1), by your sense of where the deepest insight lies. JSON: {"ratings": [{"id": node id, '
                       '"value": 0-1}], "hunch": str}', None)
        for r in out.get("ratings") or []:
            if isinstance(r, dict) and r.get("id") in s.nodes:
                s.nodes[r["id"]]["intuition"] = num(r.get("value"))
        if out.get("hunch"):
            nid = self.new("alternative", "Hunch: " + str(out["hunch"]), s.root, "refines", 0.3)
            if nid:
                s.nodes[nid]["intuition"] = 0.9

    def op_introspect(self, focus):
        s = self.s
        out = self.ask(f'Operation INTROSPECT. What hidden assumptions does node {focus} depend on? Only list ones not '
                       'already in the graph. Rate how load-bearing each is (0-1) and how plausible it is (0-1). JSON: '
                       '{"assumptions": [{"text": str, "load": 0-1, "plausibility": 0-1}]}', focus)
        for a in (out.get("assumptions") or [])[:3]:
            if isinstance(a, dict):
                load = num(a.get("load"))
                if self.new("assumption", a.get("text"), focus, "depends_on", num(a.get("plausibility")), load=load):
                    s.uncertainty = clip(s.uncertainty + 0.08 * load)
        s.novelty = clip(s.novelty * 0.85)
        self.prune_assumptions()

    def prune_assumptions(self):
        """Minimal assumption sets: keep only the policy's max, cutting the least load-bearing."""
        asm = sorted((n for n in self.s.live() if n["type"] == "assumption"), key=lambda n: n.get("load", 0.5))
        for n in asm[: max(0, len(asm) - self.policy["max_assumptions"])]:
            self.reject(n["id"], "pruned: not load-bearing enough")

    def op_doubt(self, focus):
        s, p = self.s, self.policy
        out = self.ask(f'Operation DOUBT. Give the {p["objections"]} strongest ways node {focus} could be wrong: '
                       'objections or concrete counterexamples. JSON: {"objections": [{"kind": "objection"|'
                       '"counterexample", "text": str, "strength": 0-1}]}', focus)
        for o in (out.get("objections") or [])[: p["objections"]]:
            if isinstance(o, dict):
                kind = "counterexample" if "counter" in str(o.get("kind")) else "objection"
                nid = self.new(kind, o.get("text"), focus, "attacks", num(o.get("strength")))
                if nid:
                    self.experiment(kind, nid, focus)
        s.confidence = clip(s.confidence - 0.02 * len(s.pending()))

    def op_counterfactual(self, focus):
        s = self.s
        target = s.nodes[focus]
        if target["type"] == "assumption":
            mode, q = "decisive_assumption", (f'Suppose assumption [{focus}] is false. Describe the concrete world where it '
                                              'fails and say whether the current hypothesis still holds there.')
        elif target["conf"] >= 0.6:
            mode, q = "failure_world", ('Construct a possible world where all the supporting premises stay plausible but '
                                        f'node [{focus}] is false.')
        elif self.rng.random() < 0.5:
            mode, q = "minimal_change", f'What is the smallest change to one premise that would flip node [{focus}]?'
        else:
            mode, q = "opposite", f'What would need to be true for the opposite of node [{focus}] to hold? Make it concrete.'
        out = self.ask(f'Operation COUNTERFACTUAL ({mode}). {q} JSON: {{"scenario": str, "changed_element": str, '
                       '"prediction": "flips"|"holds", "why": str}', focus)
        text = f"[{mode.replace('_', ' ')}] {out.get('scenario', '')}"
        if out.get("changed_element"):
            text += f" (changes: {out['changed_element']})"
        nid = self.new("counterfactual", text, focus, "tests", 0.5, mode=mode,
                       prediction=str(out.get("prediction", "flips")))
        if nid:
            self.experiment("counterfactual", nid, focus)
            s.novelty = clip(s.novelty + 0.08)

    def op_formalize(self, focus):
        """Tool use: the LLM translates, the truth table decides."""
        s = self.s
        out = self.ask(f'Operation FORMALIZE. Translate the argument for node [{focus}] (with its premises and '
                       'assumptions) into propositional logic. Use capital-letter atoms, operators ~ & | -> <->. JSON: '
                       '{"atoms": {"P": "meaning", ...}, "premises": ["P -> Q", ...], "conclusion": "Q"}', focus)
        prem, concl, atoms = out.get("premises") or [], str(out.get("conclusion") or ""), out.get("atoms") or {}
        s.nodes[focus]["formalized"] = True  # one formal check per claim; a failed translation is also a result
        tool = "theorem_prover" if self.can("theorem_prover") else "logic_check"
        ok, res = self.use(tool, [str(x) for x in prem], concl)
        if not ok:
            return
        meaning = lambda a: atoms.get(a, a) if isinstance(atoms, dict) else a
        if not res["consistent"]:
            nid = self.new("contradiction", "Formal check: the premises are jointly inconsistent", focus, "attacks", 0.8, formal=True)
            if nid:
                self.experiment("formal", nid, focus)
            s.uncertainty = clip(s.uncertainty + 0.15)
        elif res["valid"]:
            self.new("evidence", f"Formally valid: {'; '.join(map(str, prem))} ⊢ {concl}", focus, "supports", 0.9,
                     formal=True, source="logic_check")
            self.cog("insight", node=focus, reason="formally_valid")
            if focus == s.root:
                self.set_root_conf(s.confidence + 0.06)
        else:
            cm = ", ".join(f"{meaning(a)} is {'true' if v else 'false'}" for a, v in res["countermodel"].items())
            nid = self.new("counterexample", f"As formalized, the premises do not entail the conclusion. Counter-assignment: {cm}", focus,
                           "attacks", 0.7, formal=True)
            if nid:
                self.experiment("formal", nid, focus)
            s.uncertainty = clip(s.uncertainty + 0.1)

    def op_inquire(self, focus):
        s = self.s
        n = s.nodes.get(focus)
        if n and n["type"] == "question" and n["status"] == "open":
            out = self.ask(f'Operation INQUIRE (answer). Answer question [{focus}] as precisely as you can and say '
                           f'whether the answer supports or undermines the hypothesis. JSON: {{"answer": str, "effect": '
                           '"supports"|"undermines", "confidence": 0-1}', focus)
            sup = out.get("effect") != "undermines"
            nid = self.new("premise" if sup else "objection", out.get("answer"), s.root, "supports" if sup else "attacks",
                           num(out.get("confidence")))
            n["status"] = "supported"
            if nid and not sup:
                self.experiment("objection", nid, s.root)
        else:
            out = self.ask(f'Operation INQUIRE (pose). Given node [{focus}], what single sub-question, if answered, would '
                           'most change our confidence in the hypothesis? JSON: {"question": str, "why": str}', focus)
            nid = self.new("question", out.get("question"), focus, "refines", 0.5)
            if nid:
                s.nodes[nid]["intuition"] = 0.8

    def op_adjudicate(self, _focus):
        s, p = self.s, self.policy
        pend = s.pending()
        if not pend:
            return
        x = max(pend, key=lambda e: s.nodes[e["target"]]["curiosity"] + (0.5 if e["target"] == s.root else 0))
        o, t = s.nodes[x["node"]], s.nodes[x["target"]]
        if x["kind"] == "counterfactual":
            q = (f'Run this test. Scenario [{o["id"]}]: "{o["text"]}". Claim [{t["id"]}]: "{t["text"]}". In that '
                 'scenario, does the claim fail? JSON: {"survives": true if the claim FAILS, false if it holds, '
                 '"reply": str, "damage": 0-1}')
        else:
            q = (f'Objection [{o["id"]}]: "{o["text"]}" against [{t["id"]}]: "{t["text"]}". Does the objection survive '
                 'the best available reply? JSON: {"survives": true|false, "reply": str, "damage": 0-1}')
        out = self.ask("Operation ADJUDICATE (adversarial test). " + q, o["id"])
        before = s.confidence
        if out.get("survives") is True:
            dmg = clip(num(out.get("damage")) * p["adversarial"])
            x["status"] = "defeated"
            o["status"], o["surprise"] = "supported", dmg * t["conf"]
            s.surprise = clip(s.surprise + dmg * (0.5 + t["conf"]))  # a confident belief failing is surprising
            t["conf"] = clip(t["conf"] - 0.5 * dmg)
            if t["conf"] < p["reject_below"] and t["id"] != s.root:
                self.reject(t["id"], "defeated by " + o["id"])
            if t["id"] == s.root or t["parent"] == s.root:
                self.set_root_conf(s.confidence - 0.4 * dmg)
            s.uncertainty = clip(s.uncertainty + 0.15 * dmg)
        else:
            x["status"] = "answered"
            self.reject(o["id"], "answered")
            self.new("response", out.get("reply"), t["id"], "responds_to", 0.6)
            t["conf"] = clip(t["conf"] + 0.08)
            if t["id"] == s.root:
                self.set_root_conf(t["conf"])
                if num(out.get("damage")) < 0.4 and o["conf"] > 0.6:
                    self.cog("insight", node=t["id"], reason="survived_test")
            s.uncertainty = clip(s.uncertainty - 0.06)
        x["gain"] = round(abs(s.confidence - before), 3)

    def op_revise(self, _focus):
        s = self.s
        out = self.ask('Operation REVISE. Given the surviving objections, failed tests and supported material, state the '
                       'best revised hypothesis. Say whether this is a minor refinement or a major change of position. '
                       'JSON: {"hypothesis": str, "change": "minor"|"major"}', s.root)
        h = str(out.get("hypothesis") or "").strip()
        if not h or h == s.hypothesis:
            return
        old = s.root
        major = out.get("change") == "major" or s.nodes[old]["status"] == "rejected"
        prior = 0.5
        if self.rejected_hyp:  # learning: hypotheses like ones already defeated start lower
            sim = max(cos(embed([h])[0], v) for v in self.rejected_hyp)
            if sim > 0.8:
                prior -= 0.6 * (sim - 0.7)
                self.cog("learning", op="revise", note="resembles a rejected hypothesis", sim=round(sim, 3))
        if major:
            self.reject(old, "superseded")
        new = self.new("hypothesis", h, None if major else old, None if major else "refines", clip(prior, 0.2, 0.6))
        if new:
            if major:
                s.edges.append({"src": new, "dst": old, "rel": "derived_from"})
            s.root, s.hypothesis = new, h
            s.confidence = s.nodes[new]["conf"]
            s.novelty = clip(s.novelty + (0.3 if major else 0.1))
        s.surprise = clip(s.surprise * 0.5)

    def op_conclude(self, _focus):
        s = self.s
        out = self.ask('Operation CONCLUDE. State your final position on the question. JSON: {"position": "one or two sentences", '
                       '"stance": "yes"|"no"|"qualified", "credence_yes": probability 0-1 that the answer to the '
                       'question is yes, "key_reasons": [str], "strongest_open_objection": str, '
                       '"open_questions": [str]}', s.root)
        s.conclusion = {
            "position": str(out.get("position") or s.hypothesis),
            "stance": str(out.get("stance") or "qualified").lower(),
            "credence": num(out.get("credence_yes")),
            "key_reasons": [str(x) for x in (out.get("key_reasons") or [])][:4],
            "open_objection": str(out.get("strongest_open_objection") or ""),
            "open_questions": [str(x) for x in (out.get("open_questions") or [])][:3],
        }
        if s.root and s.nodes[s.root]["status"] != "rejected":
            s.nodes[s.root]["status"] = "stable"
            self.cog("insight", node=s.root, reason="stable_conclusion")

    # ------------------------------------------------ long-term memory write-back
    def memories(self, run: str) -> list[dict]:
        s, out = self.s, []
        base = {"question": s.question, "profile": self.name, "run": run}
        xs = {e["node"]: e for e in s.experiments}
        for n in s.nodes.values():
            v = self.vec.get(n["id"])
            if v is None:
                continue
            if n["type"] == "hypothesis":
                outcome = "survived" if n["status"] == "stable" else "rejected" if n["status"] == "rejected" else "open"
                out.append({**base, "kind": "hypothesis", "text": n["text"], "vec": v, "outcome": outcome, "score": n["conf"]})
            elif n["type"] in ("objection", "counterexample", "counterfactual") and n["id"] in xs and n.get("source") != "memory":
                st = xs[n["id"]]["status"]
                outcome = "defeated" if st == "defeated" else "failed" if st == "answered" else "untested"
                out.append({**base, "kind": n["type"], "text": n["text"], "vec": v, "outcome": outcome, "score": n["conf"]})
            elif n["type"] == "assumption":
                out.append({**base, "kind": "assumption", "text": n["text"], "vec": v,
                            "outcome": n["status"], "score": n.get("recur", 1)})
        for q in (s.conclusion or {}).get("open_questions", []):
            out.append({**base, "kind": "unresolved", "text": q, "vec": embed([q])[0], "outcome": "open"})
        c = s.conclusion or {}
        out.append({**base, "kind": "question", "text": s.question, "vec": embed([s.question])[0],
                    "outcome": f"{c.get('stance', '?')} {c.get('credence', 0):.2f}: {c.get('position', '')[:200]}"})
        out.append({**base, "kind": "trajectory", "text": " ".join(h["op"] for h in s.history),
                    "vec": embed([s.question])[0], "outcome": c.get("stance", "")})
        return out
