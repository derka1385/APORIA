# Vendored from APORIA (derka1385/APORIA lab/profiles.py): cognitive profiles as policy vectors, unchanged.
"""Cognitive profiles as policy vectors, and Δ interpolation between them.

param = base + Δ · (target − base) for numbers; lists (tool access) switch to
the target at Δ ≥ 0.5. Every entry changes what the controller, attention,
learning or an operation does; nothing is a label.
"""

from __future__ import annotations

OPS = ["memory", "reason", "imagine", "intuit", "introspect", "doubt", "counterfactual", "formalize",
       "inquire", "adjudicate", "revise", "conclude"]
ALL_TOOLS = ["literature_search", "memory_search", "similarity", "graph_query", "logic_check", "theorem_prover",
             "calculator"]

BASE = {
    "weights": {op: 1.0 for op in OPS},  # multiplies each op's drive (state drive + metacognitive signals)
    "ctrl_temp": 0.35,       # softmax temperature of the controller's op choice
    "explore": 0.25,         # temperature of branch selection over curiosity scores (0 = pure exploitation)
    "learning_rate": 0.4,    # how fast in-session op values reshape the controller
    "llm_temp": 0.6,         # sampling temperature of every LLM call
    "top_p": 0.9,
    "context": 12,           # graph nodes the LLM is allowed to see
    "lit_k": 3,              # literature entries memory retrieves
    "lit_spread": 0.0,       # 0 = nearest entries, 1 = deliberately distant ones
    "ltm_k": 3,              # long-term memory items recalled per memory operation
    "branch": 2,             # alternatives per imagine
    "objections": 2,         # objections per doubt
    "adversarial": 1.0,      # scales damage of surviving objections and counterfactuals
    "accept": 0.6,           # confidence a verification needs to mark a node supported
    "stop_conf": 0.7,        # conclude once hypothesis confidence passes this with nothing pending
    "budget": 12,            # base step budget
    "min_steps": 6,          # no conclusion before this many steps
    "surprise_bonus": 2,     # extra steps granted per surprise spike
    "max_assumptions": 8,    # assumption nodes kept; extra ones are cut (least load-bearing first)
    "reject_below": 0.3,     # a hypothesis is rejected when its confidence drops under this
    "tools": ALL_TOOLS,
    "ltm_scope": ["own"],    # long-term memory of this profile's own past runs, or ["shared"] across profiles
}

TARGETS = {
    "explorer": {
        "weights": {"imagine": 2.2, "intuit": 1.8, "counterfactual": 1.6, "inquire": 1.6, "memory": 1.2,
                    "reason": 0.6, "doubt": 0.6, "formalize": 0.2},
        "ctrl_temp": 0.7, "explore": 0.9, "llm_temp": 0.95, "top_p": 0.97, "branch": 4, "accept": 0.45,
        "stop_conf": 0.6, "budget": 14, "min_steps": 8, "surprise_bonus": 4, "lit_spread": 0.5,
        "tools": ["literature_search", "memory_search", "similarity"],
    },
    "formalist": {
        "weights": {"reason": 2.2, "formalize": 2.6, "introspect": 1.3, "imagine": 0.4, "intuit": 0.3,
                    "counterfactual": 0.8},
        "ctrl_temp": 0.15, "explore": 0.05, "llm_temp": 0.2, "top_p": 0.7, "branch": 1, "accept": 0.8,
        "stop_conf": 0.8, "context": 20, "reject_below": 0.4, "learning_rate": 0.2,
    },
    "skeptic": {
        "weights": {"doubt": 2.4, "counterfactual": 2.0, "adjudicate": 1.8, "imagine": 0.6, "intuit": 0.5,
                    "revise": 1.2},
        "objections": 4, "adversarial": 1.8, "min_steps": 8, "stop_conf": 0.85, "reject_below": 0.45,
        "llm_temp": 0.5, "explore": 0.15, "ltm_k": 5,
        "tools": ["memory_search", "graph_query", "logic_check", "similarity"],
    },
    "synthesizer": {
        "weights": {"memory": 2.0, "revise": 1.6, "intuit": 1.2, "inquire": 1.4, "doubt": 0.7, "formalize": 0.4},
        "lit_k": 6, "lit_spread": 0.8, "ltm_k": 8, "context": 30, "llm_temp": 0.75, "budget": 13,
        "learning_rate": 0.7, "explore": 0.5, "ltm_scope": ["shared"],
        "tools": ["literature_search", "memory_search", "similarity", "graph_query"],
    },
    "minimalist": {
        "weights": {"introspect": 2.0, "reason": 1.3, "formalize": 1.6, "imagine": 0.4, "memory": 0.4,
                    "intuit": 0.5, "inquire": 0.6},
        "lit_k": 0, "ltm_k": 0, "context": 6, "branch": 1, "stop_conf": 0.65, "budget": 10, "min_steps": 5,
        "max_assumptions": 2, "llm_temp": 0.4, "explore": 0.1,
        "tools": ["graph_query", "logic_check", "theorem_prover", "calculator"],
    },
}

PERSONAS = {
    "explorer": "explore widely, branch into unusual hypotheses and thought experiments, tolerate uncertainty",
    "formalist": "check that every step follows logically and refuse unsupported premises",
    "skeptic": "hunt aggressively for counterexamples and ways the current belief could be wrong",
    "synthesizer": "connect distant arguments and traditions into one coherent view",
    "minimalist": "derive conclusions from the smallest possible set of assumptions",
}

INTS = {"min_steps", "context", "lit_k", "ltm_k", "branch", "objections", "budget", "surprise_bonus", "max_assumptions"}


def _lerp(a, b, d):
    if isinstance(a, dict):
        return {k: _lerp(a[k], b.get(k, a[k]), d) for k in a}
    if isinstance(a, list):
        return list(b) if d >= 0.5 else list(a)
    return a + d * (b - a)


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


if __name__ == "__main__":  # pragma: no cover
    strip = lambda p: {k: v for k, v in p.items() if k != "name"}
    assert strip(policy("skeptic", 0, "architecture")) == strip(policy("explorer", 0, "architecture"))
    assert policy("skeptic", 1, "architecture")["objections"] == 4
    assert policy("skeptic", 1, "prompt")["objections"] == 2 and policy("skeptic", 1, "prompt")["persona"]
    assert policy("explorer", 0.5, "architecture")["branch"] == 3
    assert "logic_check" not in policy("explorer", 0.6, "architecture")["tools"]
    assert "logic_check" in policy("explorer", 0.4, "architecture")["tools"]
    print("ok")
