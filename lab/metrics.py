"""Δ metrics: how differently did the reasoners think, and where did they end up?

Every metric is computed from what the reasoners independently produced.
`agents` maps name -> State.snapshot().
"""

from __future__ import annotations

import math
from itertools import combinations

from engine import cos, embed

ARG_TYPES = ["premise", "assumption", "objection", "counterexample", "thought_experiment", "alternative", "evidence", "claim"]
MATCH = 0.8  # cosine above which two items count as "the same idea"


def _mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def _coverage_dist(va, vb) -> float:
    """1 - symmetric mean best-match cosine: how much of each argument set the other one lacks.
    Centroids wash out (every philosophy text averages to the same point), best matches do not."""
    if not va or not vb:
        return 0.0
    best = lambda xs, ys: _mean(max(cos(x, y) for y in ys) for x in xs)
    return 1 - (best(va, vb) + best(vb, va)) / 2


def _edit(a: list, b: list) -> float:
    """Normalised Levenshtein distance between two op sequences."""
    if not a and not b:
        return 0.0
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1] / max(len(a), len(b))


def _js(p, q) -> float:
    """Jensen-Shannon distance (base 2, in [0,1])."""
    m = [(a + b) / 2 for a, b in zip(p, q)]
    kl = lambda x, y: sum(a * math.log2(a / b) for a, b in zip(x, y) if a > 0)
    return math.sqrt(max(0.0, (kl(p, m) + kl(q, m)) / 2))


def _type_dist(nodes):
    counts = [sum(1 for n in nodes if n["type"] == t) for t in ARG_TYPES]
    z = sum(counts) or 1
    return [c / z for c in counts]


def _unique(per_agent: dict[str, list[str]]) -> dict[str, list[str]]:
    """Items with no near-duplicate (cosine >= MATCH) in any other reasoner."""
    vecs = {a: embed(ts) if ts else [] for a, ts in per_agent.items()}
    out = {}
    for a, ts in per_agent.items():
        others = [v for b, vs in vecs.items() if b != a for v in vs]
        out[a] = [t for t, v in zip(ts, vecs[a]) if all(cos(v, o) < MATCH for o in others)]
    return out


def compute(agents: dict[str, dict]) -> dict:
    names = list(agents)
    pairs = list(combinations(names, 2))
    texts = {a: [n["text"] for n in s["nodes"] if n["type"] != "claim"] for a, s in agents.items()}
    vecs = {a: embed(t) if t else [] for a, t in texts.items()}
    concl = {a: (s["conclusion"] or {}).get("position", s["hypothesis"]) for a, s in agents.items()}
    cvec = dict(zip(names, embed([concl[a] for a in names])))
    ops = {a: [h["op"] for h in s["history"]] for a, s in agents.items()}
    stance = {a: (s["conclusion"] or {}) for a, s in agents.items()}

    def disagree(a, b):
        x, y = stance[a], stance[b]
        return x.get("stance") != y.get("stance") or abs(x.get("credence", .5) - y.get("credence", .5)) > 0.3

    pair = {f"{a}|{b}": {
        "semantic": round(_coverage_dist(vecs[a], vecs[b]), 3),
        "path_sim": round(1 - _edit(ops[a], ops[b]), 3),
        "concl_sim": round(cos(cvec[a], cvec[b]), 3),
        "branch": round(_js(_type_dist(agents[a]["nodes"]), _type_dist(agents[b]["nodes"])), 3),
        "disagree": disagree(a, b),
    } for a, b in pairs}

    by_type = lambda kinds: {a: [n["text"] for n in s["nodes"] if n["type"] in kinds] for a, s in agents.items()}
    uniq_asm = _unique(by_type({"assumption"}))
    uniq_obj = _unique(by_type({"objection", "counterexample"}))
    most = max(pair.items(), key=lambda kv: (kv[1]["disagree"], 1 - kv[1]["concl_sim"] + kv[1]["semantic"]),
               default=(None, None))
    return {
        "semantic_diversity": round(_mean(p["semantic"] for p in pair.values()), 3),
        "branch_diversity": round(_mean(p["branch"] for p in pair.values()), 3),
        "disagreement_rate": round(_mean(p["disagree"] for p in pair.values()), 3),
        "path_similarity": round(_mean(p["path_sim"] for p in pair.values()), 3),
        "conclusion_similarity": round(_mean(p["concl_sim"] for p in pair.values()), 3),
        "unique_assumptions": sum(len(v) for v in uniq_asm.values()),
        "unique_objections": sum(len(v) for v in uniq_obj.values()),
        "unique": {a: {"assumptions": uniq_asm[a], "objections": uniq_obj[a]} for a in names},
        "pairs": pair,
        "most_divergent": most[0],
    }


if __name__ == "__main__":
    assert _coverage_dist([[1, 0]], [[1, 0]]) == 0 and _coverage_dist([[1, 0]], [[0, 1]]) == 1
    assert _edit(list("abc"), list("abc")) == 0 and _edit(list("ab"), list("cd")) == 1
    assert _js([1, 0], [1, 0]) == 0 and abs(_js([1, 0], [0, 1]) - 1) < 1e-9
    print("ok")
