"""Cognitive engine: shared state, operations, controller.

One Reasoner = one State + one policy. Each step the controller scores every
operation from the state, samples one, attention picks a focus node, the
operation makes one LLM call and its result is folded back into the state.
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

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
MODEL = os.environ.get("APORIA_MODEL", "qwen2.5:3b")
EMBED_MODEL = os.environ.get("APORIA_EMBED", "nomic-embed-text")
LITERATURE = json.loads((Path(__file__).parent / "literature.json").read_text())


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


# ---------------------------------------------------------------- state

class State:
    def __init__(self, question: str):
        self.question = question
        self.hypothesis = ""
        self.root: str | None = None
        self.nodes: dict[str, dict] = {}
        self.conflicts: list[dict] = []  # {objection, target, status}
        self.confidence = 0.5
        self.uncertainty = 0.6
        self.novelty = 0.8
        self.surprise = 0.0
        self.history: list[dict] = []
        self.series: list[dict] = []
        self.step = 0
        self.conclusion: dict | None = None
        self.events: list[dict] = []  # visual events for the current step (association, rejection, ...)

    def add(self, kind: str, text: str, parent: str | None, conf=0.5, **extra) -> str | None:
        text = (text or "").strip()
        if not text or any(n["text"].lower() == text.lower() for n in self.nodes.values()):
            return None
        nid = f"n{len(self.nodes)}"
        self.nodes[nid] = {"id": nid, "type": kind, "text": text[:400], "parent": parent, "status": "open",
                           "conf": conf, "curiosity": 0.5, "surprise": 0.0, "step": self.step, **extra}
        return nid

    def reject(self, nid: str):
        n = self.nodes[nid]
        if n["status"] == "rejected":
            return
        n["status"] = "rejected"
        self.events.append({"kind": "rejected", "node": nid})
        for c in self.nodes.values():  # a rejected branch takes its open children with it
            if c["parent"] == nid and c["status"] == "open":
                self.reject(c["id"])

    def live(self) -> list[dict]:
        return [n for n in self.nodes.values() if n["status"] != "rejected"]

    def open_conflicts(self) -> list[dict]:
        return [c for c in self.conflicts if c["status"] == "open"]

    def snapshot(self) -> dict:
        return {"hypothesis": self.hypothesis, "root": self.root, "nodes": list(self.nodes.values()),
                "conflicts": self.conflicts, "confidence": self.confidence, "uncertainty": self.uncertainty,
                "novelty": self.novelty, "surprise": self.surprise, "history": self.history,
                "series": self.series, "step": self.step, "conclusion": self.conclusion,
                "curiosity": max([n["curiosity"] for n in self.live()] or [0])}


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
        self.last_ops: list[str] = []

    # --- context the LLM may see (context visibility is a policy parameter)
    def context(self, focus: str | None) -> str:
        s = self.s
        nodes = sorted(s.live(), key=lambda n: self.attention_score(n), reverse=True)[: self.policy["context"]]
        if focus and focus in s.nodes and s.nodes[focus] not in nodes:
            nodes.append(s.nodes[focus])
        lines = [f"[{n['id']}] {n['type']} ({n['status']}, conf {n['conf']:.2f}): {n['text']}" for n in nodes]
        sys_line = f"Current hypothesis: {s.hypothesis or '(none yet)'}"
        return f"Question: {s.question}\n{sys_line}\nVisible reasoning graph:\n" + ("\n".join(lines) or "(empty)")

    def ask(self, instruction: str, focus: str | None) -> dict:
        system = SYSTEM + (" " + self.policy["persona"] if self.policy["persona"] else "")
        user = self.context(focus) + "\n\n" + instruction
        return llm_json(system, user, self.policy, self.model, self.seed * 1000 + self.s.step)

    # --- attention
    def attention_score(self, n: dict) -> float:
        f, s = self.policy["focus"], self.s
        recency = n["step"] / max(1, s.step)
        return (f["curiosity"] * n["curiosity"] + f["surprise"] * n["surprise"] + f["uncertainty"] * (1 - n["conf"])
                + f["confidence"] * n["conf"] + f["recency"] * recency + (0.15 if n["id"] == s.root else 0))

    def pick_focus(self, op: str) -> str | None:
        s = self.s
        if op in ("introspect", "revise", "conclude"):
            return s.root
        if op == "adjudicate":
            return s.open_conflicts()[0]["objection"] if s.open_conflicts() else s.root
        cands = [n for n in s.live() if n["type"] != "evidence" and n["status"] != "stable"]
        if op == "reason":
            cands = [n for n in cands if n["status"] == "open"] or cands
        if op == "doubt":
            cands = [n for n in cands if n["type"] not in ("objection", "counterexample")] or cands
        return max(cands, key=self.attention_score)["id"] if cands else s.root

    # --- controller
    def drives(self) -> dict[str, float]:
        s, p = self.s, self.policy
        live = s.live()
        unverified = sum(1 for n in live if n["status"] == "open") / max(1, len(live))
        n_obj = sum(1 for n in live if n["type"] in ("objection", "counterexample"))
        n_asm = sum(1 for n in live if n["type"] == "assumption")
        mean_cur = sum(n["curiosity"] for n in live) / max(1, len(live))
        since = {op: next((i for i, h in enumerate(reversed(s.history)) if h["op"] == op), 99) for op in p["weights"]}
        d = {
            "memory": s.novelty * (1 - s.confidence) + (0.2 if since["memory"] > 4 else 0),
            "reason": s.uncertainty * 0.7 + 0.4 * unverified,
            "imagine": 0.6 * mean_cur + 0.4 * (1 - s.novelty),
            "intuit": 0.5 * (since["intuit"] > 3) + 0.3 * (len(live) > 6),
            "introspect": 0.5 * s.novelty + 0.4 * s.confidence * (n_asm == 0),
            "doubt": s.confidence * (1 - n_obj / max(1, len(live))),
            "adjudicate": min(1.2, 0.6 * len(s.open_conflicts())),
            "revise": (1.5 if s.root and s.nodes[s.root]["status"] == "rejected" else 0) + 0.5 * s.surprise,
            "conclude": 0.0,
        }
        if s.step >= p["min_steps"] and s.confidence >= p["stop_conf"] and not s.open_conflicts():
            d["conclude"] = 1.5
        if s.step >= 3:  # breaking an op loop: the same op three times in a row is damped
            if len(self.last_ops) >= 2 and self.last_ops[-1] == self.last_ops[-2]:
                d[self.last_ops[-1]] *= 0.3
        return {op: p["weights"][op] * v for op, v in d.items()}

    def choose(self) -> tuple[str, dict]:
        if self.s.step >= self.budget:
            return "conclude", {}
        sc = self.drives()
        t = max(0.05, self.policy["ctrl_temp"])
        m = max(sc.values())
        w = {op: math.exp((v - m) / t) for op, v in sc.items()}
        z = sum(w.values())
        r, acc = self.rng.random() * z, 0.0
        for op, v in w.items():
            acc += v
            if r <= acc:
                return op, {k: round(v / z, 3) for k, v in w.items()}
        return max(sc, key=sc.get), {}

    # --- run loop
    def run(self):
        s = self.s
        self.op_start()
        while s.conclusion is None:
            op, probs = self.choose()
            focus = self.pick_focus(op)
            self.emit({"type": "op", "agent": self.name, "op": op, "focus": focus, "probs": probs})
            s.events = []
            before = (s.confidence, s.uncertainty)
            getattr(self, "op_" + op)(focus)
            s.step += 1
            s.surprise *= 0.75  # surprise is transient
            if s.surprise > 0.45 and self.budget < self.policy["budget"] + 3 * self.policy["surprise_bonus"]:
                self.budget += self.policy["surprise_bonus"]  # surprising branch gets more compute
                s.events.append({"kind": "compute", "budget": self.budget})
            s.history.append({"step": s.step, "op": op, "focus": focus, "probs": probs,
                              "d_conf": round(s.confidence - before[0], 3), "d_unc": round(s.uncertainty - before[1], 3)})
            self.last_ops.append(op)
            self.tick()

    def tick(self):
        s = self.s
        s.series.append({k: round(getattr(s, k), 3) for k in ("confidence", "uncertainty", "novelty", "surprise")})
        self.emit({"type": "state", "agent": self.name, "state": s.snapshot(), "events": s.events,
                   "budget": self.budget})

    def set_root_conf(self, c: float):
        s = self.s
        s.confidence = clip(c)
        if s.root:
            s.nodes[s.root]["conf"] = s.confidence
            if s.confidence < self.policy["reject_below"]:
                s.reject(s.root)

    # --- operations
    def op_start(self):
        s = self.s
        out = self.ask('Operation START. Propose an initial answer to the question as a one-sentence hypothesis, and '
                       'the premises it rests on. JSON: {"hypothesis": str, "premises": [str, str]}',
                       None)
        s.hypothesis = str(out.get("hypothesis") or "No initial hypothesis.")
        # every reasoner starts from the same neutral prior; the LLM's self-rated confidence is too eager
        s.root = s.add("claim", s.hypothesis, None, 0.5)
        for p in (out.get("premises") or [])[:3]:
            s.add("premise", str(p), s.root)
        s.confidence = s.nodes[s.root]["conf"]
        s.history.append({"step": 0, "op": "start", "focus": None, "probs": {}, "d_conf": 0, "d_unc": 0})
        self.tick()

    def op_memory(self, focus):
        s, p = self.s, self.policy
        query = s.question + " " + (s.nodes[focus]["text"] if focus else "")
        sources = retrieve(query, p["lit_k"], p["lit_spread"], self.rng)
        lit = "\n".join(f"<{e['id']}> {e['title']}: {e['text']}" for e in sources) or "(no literature access)"
        out = self.ask(f'Operation MEMORY. Focus node: {focus}. Literature available to you:\n{lit}\n\n'
                       'Extract up to 3 pieces of relevant evidence or established positions for the focus. Mark '
                       'whether each supports or undermines the focus. JSON: {"evidence": [{"text": str, "source": '
                       'source id, "supports": true|false}]}', focus)
        found = 0
        for e in (out.get("evidence") or [])[:3]:
            if not isinstance(e, dict):
                continue
            nid = s.add("evidence", str(e.get("text")), focus, 0.7, source=str(e.get("source") or ""))
            if not nid:
                continue
            found += 1
            s.events.append({"kind": "association", "node": nid, "source": s.nodes[nid]["source"]})
            if e.get("supports") is False and focus:
                s.conflicts.append({"objection": nid, "target": focus, "status": "open"})
        s.novelty = clip(s.novelty * 0.7)
        s.uncertainty = clip(s.uncertainty - 0.05 * found)

    def op_reason(self, focus):
        s, p = self.s, self.policy
        out = self.ask(f'Operation REASON. Check whether node {focus} actually follows from, or is supported by, what '
                       'is in the graph. Name any missing premise it silently needs. JSON: {"verdict": "valid"|'
                       '"invalid"|"unsupported", "confidence": 0-1, "missing_premise": str or "", "why": str}', focus)
        n = s.nodes[focus]
        v, c = str(out.get("verdict", "unsupported")).lower(), num(out.get("confidence"))
        if v == "valid" and c >= p["accept"]:
            n["status"], n["conf"] = "supported", n["conf"] + 0.5 * max(0.0, c - n["conf"])
            s.uncertainty = clip(s.uncertainty - 0.12)
        elif v == "invalid":
            s.reject(focus)
            s.uncertainty = clip(s.uncertainty + 0.1)
        else:  # unsupported, or valid but below this policy's acceptance threshold
            n["conf"] = clip(n["conf"] - 0.1)
            s.uncertainty = clip(s.uncertainty + 0.05)
        if out.get("missing_premise"):
            s.add("assumption", str(out["missing_premise"]), focus, 0.4, load=0.6)
        if focus == s.root:
            self.set_root_conf(n["conf"] if n["status"] != "rejected" else 0.0)
        elif n["status"] == "supported" and n["parent"] == s.root:
            self.set_root_conf(s.confidence + 0.05)
        self.prune_assumptions()

    def op_imagine(self, focus):
        s, p = self.s, self.policy
        out = self.ask(f'Operation IMAGINE. For node {focus}, invent {p["branch"]} alternative hypotheses or thought '
                       'experiments that would test it or show a different answer. JSON: {"items": [{"kind": '
                       '"thought_experiment"|"alternative", "text": str, "implication": str}]}', focus)
        for it in (out.get("items") or [])[: p["branch"]]:
            if isinstance(it, dict):
                kind = "thought_experiment" if "thought" in str(it.get("kind")) else "alternative"
                text = str(it.get("text") or "") + (f" → {it['implication']}" if it.get("implication") else "")
                if s.add(kind, text, focus, 0.4):
                    s.novelty = clip(s.novelty + 0.12)

    def op_intuit(self, _focus):
        s = self.s
        out = self.ask('Operation INTUIT. Before verifying anything, rate how promising each visible node is to explore '
                       'next (0-1), by your sense of where the deepest insight lies. JSON: {"ratings": [{"id": node id, '
                       '"value": 0-1}], "hunch": str}', None)
        for r in out.get("ratings") or []:
            if isinstance(r, dict) and r.get("id") in s.nodes:
                s.nodes[r["id"]]["curiosity"] = num(r.get("value"))
        if out.get("hunch"):
            nid = s.add("alternative", "Hunch: " + str(out["hunch"]), s.root, 0.3)
            if nid:
                s.nodes[nid]["curiosity"] = 0.8

    def op_introspect(self, focus):
        s = self.s
        out = self.ask('Operation INTROSPECT. What hidden assumptions does the current hypothesis depend on? Only list '
                       'ones not already in the graph. Rate how load-bearing each is. JSON: {"assumptions": [{"text": '
                       'str, "load": 0-1}]}', focus)
        for a in (out.get("assumptions") or [])[:3]:
            if isinstance(a, dict):
                load = num(a.get("load"))
                if s.add("assumption", str(a.get("text")), s.root, 0.5, load=load):
                    s.uncertainty = clip(s.uncertainty + 0.08 * load)
        s.novelty = clip(s.novelty * 0.85)
        self.prune_assumptions()

    def prune_assumptions(self):
        """Minimal assumption sets: keep only the policy's max, cutting the least load-bearing."""
        s = self.s
        asm = sorted((n for n in s.live() if n["type"] == "assumption"), key=lambda n: n.get("load", 0.5))
        for n in asm[: max(0, len(asm) - self.policy["max_assumptions"])]:
            s.reject(n["id"])

    def op_doubt(self, focus):
        s, p = self.s, self.policy
        out = self.ask(f'Operation DOUBT. Give the {p["objections"]} strongest ways node {focus} could be wrong: '
                       'objections or concrete counterexamples. JSON: {"objections": [{"kind": "objection"|'
                       '"counterexample", "text": str, "strength": 0-1}]}', focus)
        for o in (out.get("objections") or [])[: p["objections"]]:
            if isinstance(o, dict):
                kind = "counterexample" if "counter" in str(o.get("kind")) else "objection"
                nid = s.add(kind, str(o.get("text")), focus, num(o.get("strength")))
                if nid:
                    s.conflicts.append({"objection": nid, "target": focus, "status": "open"})
                    s.events.append({"kind": "contradiction", "node": nid, "target": focus})
        s.confidence = clip(s.confidence - 0.03 * len(s.open_conflicts()))

    def op_adjudicate(self, _focus):
        s, p = self.s, self.policy
        if not s.open_conflicts():
            return
        c = s.open_conflicts()[0]
        o, t = s.nodes[c["objection"]], s.nodes[c["target"]]
        out = self.ask(f'Operation ADJUDICATE. Objection [{o["id"]}]: "{o["text"]}" against [{t["id"]}]: "{t["text"]}". '
                       'Does the objection survive the best available reply? JSON: {"survives": true|false, "reply": '
                       'str, "damage": 0-1}', o["id"])
        c["status"] = "resolved"
        if out.get("survives") is True:
            dmg = clip(num(out.get("damage")) * p["adversarial"])
            o["status"], o["surprise"] = "supported", dmg * t["conf"]
            s.surprise = clip(s.surprise + dmg * (0.5 + t["conf"]))  # a confident belief failing is surprising
            t["conf"] = clip(t["conf"] - 0.5 * dmg)
            if t["conf"] < p["reject_below"] and t["id"] != s.root:
                s.reject(t["id"])
            if t["id"] == s.root or t["parent"] == s.root:
                self.set_root_conf(s.confidence - 0.4 * dmg)
            s.uncertainty = clip(s.uncertainty + 0.15 * dmg)
        else:
            s.reject(o["id"])
            s.add("premise", "Reply: " + str(out.get("reply") or ""), t["id"], 0.6)
            t["conf"] = clip(t["conf"] + 0.08)
            if t["id"] == s.root:
                self.set_root_conf(t["conf"])
            s.uncertainty = clip(s.uncertainty - 0.06)

    def op_revise(self, _focus):
        s = self.s
        out = self.ask('Operation REVISE. Given the surviving objections and supported material, state the best '
                       'revised hypothesis. Say whether this is a minor refinement or a major change of position. '
                       'JSON: {"hypothesis": str, "change": "minor"|"major", "confidence": 0-1}', s.root)
        h = str(out.get("hypothesis") or "").strip()
        if not h or h == s.hypothesis:
            return
        old = s.root
        major = out.get("change") == "major" or (old and s.nodes[old]["status"] == "rejected")
        if major and old:
            s.reject(old)
            s.events.append({"kind": "branch", "from": old})
        new = s.add("claim", h, None if major else old, num(out.get("confidence"), 0.5))
        if new:
            s.root, s.hypothesis = new, h
            s.confidence = s.nodes[new]["conf"]
            s.novelty = clip(s.novelty + (0.3 if major else 0.1))
            for c in s.open_conflicts():  # objections aimed at the abandoned claim no longer bite
                if major and c["target"] == old:
                    c["status"] = "moot"
        s.surprise = clip(s.surprise * 0.5)

    def op_conclude(self, _focus):
        s = self.s
        out = self.ask('Operation CONCLUDE. State your final position on the question. JSON: {"position": str, '
                       '"stance": "yes"|"no"|"qualified", "credence_yes": probability 0-1 that the answer to the '
                       'question is yes, "key_reasons": [str], "strongest_open_objection": str}', s.root)
        s.conclusion = {
            "position": str(out.get("position") or s.hypothesis),
            "stance": str(out.get("stance") or "qualified").lower(),
            "credence": num(out.get("credence_yes")),
            "key_reasons": [str(x) for x in (out.get("key_reasons") or [])][:4],
            "open_objection": str(out.get("strongest_open_objection") or ""),
        }
        if s.root:
            s.nodes[s.root]["status"] = "stable"
            s.events.append({"kind": "stable", "node": s.root})


def retrieve(query: str, k: int, spread: float, rng: random.Random) -> list[dict]:
    """Nearest literature entries; with spread > 0 some slots go to deliberately distant ones."""
    if k <= 0:
        return []
    qv, *ev = embed([query] + [e["title"] + ". " + e["text"] for e in LITERATURE])
    ranked = [e for _, e in sorted(zip((cos(qv, v) for v in ev), LITERATURE), key=lambda x: -x[0])]
    n_far = int(round(k * spread * 0.5))
    near = ranked[: k - n_far]
    far = rng.sample(ranked[len(ranked) // 2:], min(n_far, len(ranked) // 2))
    return near + far
