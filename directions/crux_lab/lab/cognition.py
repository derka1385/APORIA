"""APORIA x Crux Lab: cognitive profiles as hypothesis generators, curiosity as the Director's learning signal.

APORIA's thesis: how an agent thinks (its cognitive policy) is an experimental variable. Here each of its five
profiles (explorer, formalist, skeptic, synthesizer, minimalist) generates objections, so the lab's hypotheses
differ by way of thinking as well as by model family. The policy vector is used, not named:
- operation weights choose the kind of move (imagine/counterfactual -> a case, doubt -> a counterexample,
  formalize -> an inference gap, memory/inquire -> a distant consideration, introspect -> a smuggled assumption);
- `context` caps how many premises the reasoner sees; `explore` decides between the most load-bearing premise
  and an unattacked one; `llm_temp` is the sampling temperature;
- Δ interpolates every number between the shared base policy and the profile (APORIA's dial): at Δ = 0 all five
  reasoners are the same policy, the noise floor.
In-session learning (APORIA): each profile's value is the mean realized survival × novelty of its finished
trials; the Director's exploration term uses it, so the lab spends its next experiments on the way of thinking
that has been finding open questions.
"""
from __future__ import annotations

import hashlib
import os

from crux_lab.agents.roles import render
from crux_lab.config import TOPIC
from crux_lab.graph.schema import Argument, Claim, Objection
from crux_lab.lab import aporia_profiles as ap
from crux_lab.lab.generators import GenOut, _avoid, _check, _oid, argument_context
from crux_lab.llm.client import LLMClient, ModelSpec

PROFILES = list(ap.TARGETS)          # explorer, formalist, skeptic, synthesizer, minimalist
DELTA = float(os.environ.get("APORIA_DELTA", TOPIC.get("delta", 1.0)))

# The move each generation-relevant operation makes against a premise.
MOVES = {
    "imagine": "construct a concrete thought experiment in which the premise fails.",
    "counterfactual": "change one background condition the premise silently relies on, and show the premise "
                      "fails once that condition changes.",
    "doubt": "hunt for the clearest counterexample to the premise as literally stated.",
    "formalize": "read the premise precisely and show that it does not deliver what the argument needs from it: "
                 "an equivocation, a scope shift, or a missing step in the inference it supports.",
    "memory": "bring a consideration from a distant field or tradition to bear on the premise, stated in your own "
              "words without names.",
    "inquire": "ask the question the premise cannot answer, and show that every answer to it costs the argument.",
    "introspect": "find the assumption the premise smuggles in, and show the argument needs it but cannot have it.",
    "intuit": "describe the case where intuition pulls hardest against the premise, and say why that intuition "
              "should count.",
    "reason": "derive an unwelcome consequence from the premise in a few explicit steps.",
}


def policy(profile: str, delta: float = DELTA) -> dict:
    return ap.policy(profile, delta, "architecture")


def move_of(pol: dict) -> str:
    """The generation-relevant operation this policy weights most (ties: the order of MOVES)."""
    w = pol["weights"]
    return max(MOVES, key=lambda op: (w.get(op, 0.0), -list(MOVES).index(op)))


def choose_premise(pol: dict, arg: Argument, taken: list[str], dependence: dict[str, float], seed: str) -> str:
    """explore < 0.5: the most load-bearing premise (dependence C); otherwise the least-attacked one."""
    ids = list(arg.premise_ids)
    h = lambda p: int(hashlib.sha1((seed + p).encode()).hexdigest(), 16)  # noqa: E731
    if pol["explore"] < 0.5:
        return max(ids, key=lambda p: (dependence.get(p, 0.0), -taken.count(p), h(p)))
    return min(ids, key=lambda p: (taken.count(p), h(p)))


def spec_for(client: LLMClient, profile: str, offset: int = 0) -> ModelSpec:
    """Reasoners rotate across model families, so profile and family vary independently over waves."""
    fams: dict[str, ModelSpec] = {}
    for g in client.generator_specs():
        fams.setdefault(g.family, g)
    pool = list(fams.values())
    return pool[(PROFILES.index(profile) + offset) % len(pool)]


async def reasoner(client: LLMClient, arg: Argument, own: dict[str, Claim], profile: str, *,
                   delta: float = DELTA, spec: ModelSpec | None = None, taken: list[str] | None = None,
                   dependence: dict[str, float] | None = None, revised: dict[str, str] | None = None,
                   only: str | None = None, depth: int = 0, offset: int = 0) -> Objection | None:
    pol = policy(profile, delta)
    spec = spec or spec_for(client, profile, offset)
    taken = taken or []
    target = only or choose_premise(pol, arg, taken, dependence or {}, f"{arg.id}|{profile}|{offset}")
    ctx = argument_context(arg, own, revised)
    lines = ctx.splitlines()
    scope = ""
    if pol["context"] < len(lines):         # a narrow reasoner sees the target and its nearest lines only
        keep = [ln for ln in lines if target in ln] + lines[: max(1, pol["context"] - 1)]
        ctx, scope = "\n".join(dict.fromkeys(keep)), " (the part of it you attend to)"
    allowed = set(arg.premise_ids) | ({arg.missing_premise_id} if arg.missing_premise_id else set()) | set(revised or {})
    system, user = render("generator_reasoner", move=MOVES[move_of(pol)], argument=ctx, scope=scope,
                          avoid=_avoid(taken))
    user += f"\n\nAttack {target}."
    o, _ = await client.json("generator", user, GenOut, system, spec=spec, temperature=pol["llm_temp"],
                             validate=_check(allowed, must_target=target))
    if not o:
        return None
    agent = f"reasoner:{profile}"
    return Objection(id=_oid(arg.id, agent, spec.model, o.objection), argument_id=arg.id,
                     target_premise_id=o.target_premise_id, kind=move_of(pol), text=o.objection.strip(),
                     agent=agent, model=spec.model, family=spec.family, depth=depth,
                     premise_fails_because=o.premise_fails_because.strip(), profile=profile, delta=delta)


def profile_of(o: Objection | dict) -> str | None:
    agent = o.agent if isinstance(o, Objection) else o.get("agent", "")
    return agent.split(":", 1)[1] if agent.startswith("reasoner:") else None


def learned_values(objections: list[Objection], realized: dict[str, float]) -> dict[str, float]:
    """APORIA's in-session learning: a profile's value = mean realized survival x novelty of its finished
    trials (realized: objection id -> S x N). Untried profiles are absent (the Director treats them as 1)."""
    by: dict[str, list[float]] = {}
    for o in objections:
        p = profile_of(o)
        if p and o.id in realized:
            by.setdefault(p, []).append(realized[o.id])
    return {p: sum(v) / len(v) for p, v in by.items()}


def run_metrics(objections: list[Objection], trials: dict, nov: dict, briefs: list[str], embedder=None) -> dict:
    """Per profile: what its objections did in the lab (Crux Lab's measures), plus APORIA's divergence measures
    across profiles: unique objections (no other profile's objection at cosine >= 0.8) and semantic diversity
    (mean cosine distance between objections of different profiles)."""
    from crux_lab.graph.schema import SURVIVAL
    rows: dict[str, dict] = {}
    for o in objections:
        p = profile_of(o)
        if not p:
            continue
        r = rows.setdefault(p, {"objections": 0, "trials": 0, "surviving": 0, "novelty": [], "realized": [],
                                "briefs": 0, "move": move_of(policy(p, o.delta if o.delta is not None else DELTA))})
        r["objections"] += 1
        n = (nov.get(o.id) or {}).get("novelty")
        if n is not None:
            r["novelty"].append(n)
        t = trials.get(o.id)
        if t is not None and t.status == "ok" and t.outcome:
            r["trials"] += 1
            r["surviving"] += t.outcome in ("standing", "revision_required")
            r["realized"].append(SURVIVAL.get(t.outcome, 0) * (n or 0))
        r["briefs"] += f"brief-{o.id}" in briefs
    for r in rows.values():
        r["mean_novelty"] = round(sum(r["novelty"]) / len(r["novelty"]), 3) if r["novelty"] else None
        r["learned_value"] = round(sum(r["realized"]) / len(r["realized"]), 3) if r["realized"] else None
        del r["novelty"], r["realized"]
    div: dict = {"unique_objections": None, "semantic_diversity": None}
    prof = [(profile_of(o), o.text) for o in objections if profile_of(o)]
    if embedder is not None and len({p for p, _ in prof}) >= 2:
        import numpy as np
        v = np.asarray(embedder.encode([t for _, t in prof]), dtype=float)
        v = v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)
        sim = v @ v.T
        ps = [p for p, _ in prof]
        other = np.array([[ps[i] != ps[j] for j in range(len(ps))] for i in range(len(ps))])
        uniq = {p: 0 for p in set(ps)}
        for i, p in enumerate(ps):
            if not (sim[i][other[i]] >= 0.8).any():
                uniq[p] += 1
        div = {"unique_objections": uniq, "semantic_diversity": round(float(1 - sim[other].mean()), 3)}
    return {"delta": DELTA, "profiles": rows, "divergence": div}
