"""Cognitive profiles as policy vectors, and Δ interpolation between them.

param = base + Δ · (target − base). Every number here changes what the
controller or an operation does; nothing is a label.
"""

from __future__ import annotations

OPS = ["memory", "reason", "imagine", "intuit", "introspect", "doubt", "adjudicate", "revise", "conclude"]

BASE = {
    "weights": {op: 1.0 for op in OPS},  # multiplies each op's state drive
    "ctrl_temp": 0.35,       # softmax temperature of the controller's op choice
    "llm_temp": 0.6,         # sampling temperature of every LLM call
    "top_p": 0.9,
    "context": 12,           # graph nodes the LLM is allowed to see
    "lit_k": 3,              # literature entries memory retrieves
    "lit_spread": 0.0,       # 0 = nearest entries, 1 = deliberately distant ones
    "branch": 2,             # alternatives per imagine
    "objections": 2,         # objections per doubt
    "adversarial": 1.0,      # scales damage of surviving objections
    "accept": 0.6,           # confidence a verification needs to mark a node supported
    "stop_conf": 0.7,        # conclude once root confidence passes this with no conflicts
    "budget": 10,            # base step budget
    "min_steps": 5,          # no conclusion before this many steps
    "surprise_bonus": 2,     # extra steps granted per surprise spike
    "max_assumptions": 8,    # assumption nodes kept; extra ones are cut (least load-bearing first)
    "reject_below": 0.3,     # root claim is rejected when its confidence drops under this
    "focus": {"curiosity": 0.25, "surprise": 0.25, "uncertainty": 0.25, "confidence": 0.0, "recency": 0.25},
}

TARGETS = {
    "explorer": {
        "weights": {"imagine": 2.2, "intuit": 1.8, "memory": 1.2, "reason": 0.6, "doubt": 0.6, "adjudicate": 0.8},
        "ctrl_temp": 0.7, "llm_temp": 0.95, "top_p": 0.97, "branch": 4, "accept": 0.45,
        "stop_conf": 0.6, "budget": 12, "min_steps": 7, "surprise_bonus": 4, "lit_spread": 0.5,
        "focus": {"curiosity": 0.6, "surprise": 0.3, "uncertainty": 0.05, "confidence": 0.0, "recency": 0.05},
    },
    "formalist": {
        "weights": {"reason": 2.4, "introspect": 1.3, "imagine": 0.4, "intuit": 0.3, "memory": 0.8},
        "ctrl_temp": 0.15, "llm_temp": 0.2, "top_p": 0.7, "branch": 1, "accept": 0.8,
        "stop_conf": 0.8, "context": 20, "reject_below": 0.4,
        "focus": {"curiosity": 0.0, "surprise": 0.1, "uncertainty": 0.8, "confidence": 0.0, "recency": 0.1},
    },
    "skeptic": {
        "weights": {"doubt": 2.4, "adjudicate": 1.8, "imagine": 0.7, "intuit": 0.5, "revise": 1.2},
        "objections": 4, "adversarial": 1.8, "min_steps": 7, "stop_conf": 0.85, "reject_below": 0.45, "llm_temp": 0.5,
        "focus": {"curiosity": 0.0, "surprise": 0.2, "uncertainty": 0.0, "confidence": 0.8, "recency": 0.0},
    },
    "synthesizer": {
        "weights": {"memory": 2.0, "revise": 1.6, "intuit": 1.2, "doubt": 0.7},
        "lit_k": 6, "lit_spread": 0.8, "context": 30, "llm_temp": 0.75, "budget": 11,
        "focus": {"curiosity": 0.4, "surprise": 0.3, "uncertainty": 0.2, "confidence": 0.0, "recency": 0.1},
    },
    "minimalist": {
        "weights": {"introspect": 2.0, "reason": 1.3, "imagine": 0.4, "memory": 0.4, "intuit": 0.5},
        "lit_k": 1, "context": 6, "branch": 1, "stop_conf": 0.65, "budget": 8, "min_steps": 4, "max_assumptions": 2,
        "llm_temp": 0.4,
        "focus": {"curiosity": 0.1, "surprise": 0.1, "uncertainty": 0.6, "confidence": 0.0, "recency": 0.2},
    },
}

PERSONAS = {
    "explorer": "explore widely, branch into unusual hypotheses and thought experiments, tolerate uncertainty",
    "formalist": "check that every step follows logically and refuse unsupported premises",
    "skeptic": "hunt aggressively for counterexamples and ways the current belief could be wrong",
    "synthesizer": "connect distant arguments and traditions into one coherent view",
    "minimalist": "derive conclusions from the smallest possible set of assumptions",
}

INTS = {"min_steps", "context", "lit_k", "branch", "objections", "budget", "surprise_bonus", "max_assumptions"}


def _lerp(a, b, d):
    if isinstance(a, dict):
        return {k: _lerp(a[k], b.get(k, a[k]), d) for k in a}
    v = a + d * (b - a)
    return v


def policy(name: str, delta: float, condition: str) -> dict:
    """Policy vector for one reasoner. Only the `architecture` condition moves the numbers."""
    d = max(0.0, min(1.0, delta)) if condition == "architecture" else 0.0
    p = _lerp(BASE, TARGETS[name], d)
    for k in INTS:
        p[k] = int(round(p[k]))
    p["name"] = name
    p["persona"] = persona(name, delta) if condition == "prompt" else ""
    return p


def persona(name: str, delta: float) -> str:
    if delta < 0.15:
        return ""
    strength = "slightly" if delta < 0.45 else "clearly" if delta < 0.8 else "strongly"
    return f"Your reasoning style: {strength} {PERSONAS[name]}."


if __name__ == "__main__":
    a, b = policy("skeptic", 0, "architecture"), policy("explorer", 0, "architecture")
    assert {k: v for k, v in a.items() if k != "name"} == {k: v for k, v in b.items() if k != "name"}
    assert policy("skeptic", 1, "architecture")["objections"] == 4
    assert policy("skeptic", 1, "prompt")["objections"] == 2 and policy("skeptic", 1, "prompt")["persona"]
    assert policy("explorer", 0.5, "architecture")["branch"] == 3
    print("ok")
