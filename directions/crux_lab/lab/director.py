"""The Director: plain code, no LLM. Picks the next experiment by
    priority = S * N * (0.5 + 0.5*C) + 0.1*E
S = survival (0.5 before any trial), N = novelty, C = share of graph arguments depending on the
target premise, E = 1 if this agent/family has not yet been tried (in a trial) on this argument."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from crux_lab.graph.schema import SURVIVAL, Objection

PRIOR_SURVIVAL = 0.5
MAX_DEPTH = 2
MAX_OBJECTIONS = 12
MAX_TRIALS = 6


def priority(S: float, N: float, C: float, E: float) -> float:
    return S * N * (0.5 + 0.5 * C) + 0.1 * E


@dataclass
class QueueRow:
    objection_id: str
    target_premise_id: str
    agent: str
    family: str
    depth: int
    S: float
    N: float
    C: float
    E: float
    priority: float


def explore_key(o: Objection) -> str:
    return f"{o.agent}|{o.family}"


def rank(objections: list[Objection], novelty: dict[str, float | None], dependence: dict[str, float],
         tried_keys: set[str], outcomes: dict[str, str] | None = None,
         learned: dict[str, float] | None = None) -> list[QueueRow]:
    """Rows for untried objections, highest priority first. Ties: shallower depth, then id.

    Eligibility: an objection whose novelty check could not be completed (novelty None) is not ranked at
    all; it never borrows a default score. An objection with no entry yet keeps the prior 0.5."""
    outcomes = outcomes or {}
    rows = []
    for o in objections:
        if o.id in outcomes:
            continue
        if o.id in novelty and novelty[o.id] is None:
            continue                     # not assessed: not eligible for a scored trial
        S = PRIOR_SURVIVAL
        N = novelty.get(o.id, 0.5)
        C = dependence.get(o.target_premise_id, 0.0)
        # E: curiosity. An untried agent/family is worth exploring (1). For an APORIA reasoner whose profile
        # has finished trials, E is that profile's learned value (mean realized S x N): in-session learning.
        prof = o.agent.split(":", 1)[1] if o.agent.startswith("reasoner:") else None
        E = 1 if explore_key(o) not in tried_keys else (round(learned[prof], 4) if learned and prof in learned else 0)
        rows.append(QueueRow(o.id, o.target_premise_id, o.agent, o.family, o.depth, S, round(N, 3),
                             round(C, 3), E, round(priority(S, N, C, E), 4)))
    rows.sort(key=lambda r: (-r.priority, r.depth, r.objection_id))
    return rows


def realized(outcome: str, novelty: float, C: float) -> float:
    """Priority an objection earned after its trial (for reporting the ranking of results)."""
    return round(SURVIVAL[outcome] * novelty * (0.5 + 0.5 * C), 4)


def snapshot(step: int, rows: list[QueueRow], picked: list[str], note: str = "") -> dict:
    return {"step": step, "queue": [asdict(r) for r in rows], "picked": picked, "note": note}
