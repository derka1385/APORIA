"""Objection generators. They NEVER see literature: this module imports nothing from corpus/,
graph.index or graph.store, and its context builder takes only the argument's own claims
(tests/test_generators.py checks the imports)."""
from __future__ import annotations

import asyncio
import hashlib
import re

from pydantic import BaseModel, Field

from crux_lab.agents.roles import render
from crux_lab.graph.schema import Argument, Claim, Objection
from crux_lab.llm.client import LLMClient, ModelSpec

from crux_lab.config import TOPIC

SCHOOLS: list[str] = list(TOPIC.get("schools") or
                          ["skeptical theism", "Molinism", "open theism", "Reformed epistemology", "naturalism"])
MAX_WORDS = 200          # prompt says 180; small tolerance for counting differences
_CITATION = re.compile(r"\(\s*\d{4}[a-z]?\s*\)|\bet al\b|\b(19|20)\d\d\b|\bibid\b", re.I)


class GenOut(BaseModel):
    target_premise_id: str
    objection: str = Field(description="the concrete case, at most 180 words")
    premise_fails_because: str = Field(description="one sentence: which premise fails and why")


class TraditionOut(GenOut):
    school: str


class SharpenOut(BaseModel):
    usable: bool
    target_premise_id: str = ""
    objection: str = ""
    premise_fails_because: str = ""


def argument_context(arg: Argument, own_claims: dict[str, Claim], revised: dict[str, str] | None = None) -> str:
    """The only text a generator sees about the argument: its premises, conclusion and (if found)
    the Formalizer's missing premise. `own_claims` must be this argument's claims only."""
    lines = []
    for pid in arg.premise_ids:
        lines.append(f"{pid}: {own_claims[pid].text}")
    if arg.missing_premise_id and arg.missing_premise_id in own_claims:
        lines.append(f"{arg.missing_premise_id} (unstated, found by the Formalizer): "
                     f"{own_claims[arg.missing_premise_id].text}")
    for rid, text in (revised or {}).items():
        lines.append(f"{rid} (revised premise added after an earlier trial): {text}")
    lines.append(f"Therefore, {arg.conclusion_id}: {own_claims[arg.conclusion_id].text}")
    return "\n".join(lines)


def _check(allowed: set[str], must_target: str | None = None, school: str | None = None):
    def check(o: GenOut) -> str | None:
        if must_target and o.target_premise_id != must_target:
            return f"you must target {must_target}"
        if o.target_premise_id not in allowed:
            return f"target_premise_id must be one of {sorted(allowed)}"
        words = len(o.objection.split())
        if words > MAX_WORDS:
            return f"objection has {words} words; the limit is 180"
        if words < 40:
            return "objection is too thin; give the concrete case (who, what they believe, what happens)"
        if _CITATION.search(o.objection):
            return "no citations, dates or 'et al.': argue from the case alone"
        if school and getattr(o, "school", school).strip().lower() != school.lower():
            return f"declare the school {school}"
        return None
    return check


def _oid(arg_id: str, agent: str, model: str, text: str) -> str:
    h = hashlib.sha1(f"{agent}|{model}|{text}".encode()).hexdigest()[:6]
    return f"{arg_id}.o{h}"


def _make(arg: Argument, o: GenOut, agent: str, spec: ModelSpec, depth: int, kind: str,
          tradition: str | None = None) -> Objection:
    return Objection(id=_oid(arg.id, agent, spec.model, o.objection), argument_id=arg.id,
                     target_premise_id=o.target_premise_id, kind=kind, text=o.objection.strip(),
                     agent=agent, model=spec.model, family=spec.family, depth=depth,
                     tradition=tradition, premise_fails_because=o.premise_fails_because.strip())


def _avoid(taken: list[str]) -> str:
    if not taken:
        return ""
    return ("- Other members of the lab already attacked: " + ", ".join(sorted(set(taken))) +
            ". Prefer a different premise unless you have a much stronger case.")


async def blind(client: LLMClient, arg: Argument, own: dict[str, Claim], spec: ModelSpec,
                depth: int = 0, taken: list[str] | None = None, revised: dict[str, str] | None = None,
                only: str | None = None) -> Objection | None:
    ctx = argument_context(arg, own, revised)
    allowed = set(arg.premise_ids) | ({arg.missing_premise_id} if arg.missing_premise_id else set()) | set(revised or {})
    system, user = render("generator_blind", argument=ctx, avoid=_avoid(taken or []))
    if only:
        user += f"\n\nAttack {only}."
    o, _ = await client.json("generator", user, GenOut, system, spec=spec,
                             validate=_check(allowed, must_target=only))
    return _make(arg, o, "blind_thought_experimenter", spec, depth, "thought_experiment") if o else None


async def hidden(client: LLMClient, arg: Argument, own: dict[str, Claim], spec: ModelSpec) -> Objection | None:
    if not arg.missing_premise_id or arg.missing_premise_id not in own:
        return None
    system, user = render("generator_hidden", argument=argument_context(arg, own),
                          missing_id=arg.missing_premise_id, missing_text=own[arg.missing_premise_id].text)
    o, _ = await client.json("generator", user, GenOut, system, spec=spec,
                             validate=_check({arg.missing_premise_id}, must_target=arg.missing_premise_id))
    return _make(arg, o, "hidden_premise_attacker", spec, 0, "hidden_premise") if o else None


async def tradition(client: LLMClient, arg: Argument, own: dict[str, Claim], spec: ModelSpec,
                    school: str) -> Objection | None:
    allowed = set(arg.premise_ids) | ({arg.missing_premise_id} if arg.missing_premise_id else set())
    system, user = render("generator_tradition", argument=argument_context(arg, own),
                          schools=", ".join(SCHOOLS), school=school)
    o, _ = await client.json("generator", user, TraditionOut, system, spec=spec,
                             validate=_check(allowed, school=school))
    return _make(arg, o, "tradition_lens", spec, 0, "tradition", tradition=school) if o else None


async def naive(client: LLMClient, arg: Argument, own: dict[str, Claim], small: ModelSpec,
                sharpener: ModelSpec) -> tuple[str, Objection | None]:
    """Naive Questioner: counts only after another agent sharpens the question into an objection."""
    ctx = argument_context(arg, own)
    system, user = render("naive_question", argument=ctx)
    q = (await client.chat("naive_questioner", user, system, spec=small, max_tokens=200)).text.strip()
    allowed = set(arg.premise_ids) | ({arg.missing_premise_id} if arg.missing_premise_id else set())
    system, user = render("sharpen", argument=ctx, question=q)

    def check(o: SharpenOut) -> str | None:
        if not o.usable:
            return None
        return _check(allowed)(GenOut(target_premise_id=o.target_premise_id, objection=o.objection,
                                      premise_fails_because=o.premise_fails_because))
    o, _ = await client.json("generator", user, SharpenOut, system, spec=sharpener, validate=check)
    if not o or not o.usable:
        return q, None
    obj = _make(arg, GenOut(target_premise_id=o.target_premise_id, objection=o.objection,
                            premise_fails_because=o.premise_fails_because),
                "naive_questioner+sharpener", sharpener, 0, "naive_sharpened")
    obj = obj.model_copy(update={"model": f"{small.model}→{sharpener.model}",
                                 "family": f"{small.family}→{sharpener.family}"})
    return q, obj


async def first_wave(client: LLMClient, arg: Argument, own: dict[str, Claim], max_n: int = 8,
                     dependence: dict[str, float] | None = None) -> list[Objection]:
    """APORIA's five cognitive profiles (one reasoner each, rotating across model families), then the
    hidden-premise attacker and two tradition lenses. COGNITION=off restores the family-only blind wave."""
    import os
    if os.environ.get("COGNITION", "on") != "off":
        from crux_lab.lab import cognition
        taken: list[str] = []
        tasks = []
        for prof in cognition.PROFILES:
            pol = cognition.policy(prof)
            tgt = cognition.choose_premise(pol, arg, taken, dependence or {}, f"{arg.id}|{prof}|0")
            taken.append(tgt)
            tasks.append(cognition.reasoner(client, arg, own, prof, dependence=dependence, only=tgt))
        fams: dict[str, ModelSpec] = {}
        for g in client.generator_specs():
            fams.setdefault(g.family, g)
        rest = list(fams.values())[len(cognition.PROFILES):] or list(fams.values())
        tasks.append(hidden(client, arg, own, rest[0]))
        for i, school in enumerate(_schools_for(arg.id)):
            tasks.append(tradition(client, arg, own, rest[(i + 1) % len(rest)], school))
        res = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in res if isinstance(r, Objection)][:max_n]
    gens = client.generator_specs()
    # One model per family (first listed = strongest), so a large model pool still leaves room for the
    # Hidden-Premise Attacker and the two Tradition Lenses within max_n.
    by_family: dict[str, ModelSpec] = {}
    for g in gens:
        by_family.setdefault(g.family, g)
    fams = list(by_family.values())
    n_blind = max(1, min(len(fams), max_n - 3)) if len(fams) > 1 else len(gens)
    blind_specs = fams[:n_blind] if len(fams) > 1 else gens
    rest = fams[n_blind:] or fams
    # Blind generators run in parallel and, left alone, converge on the weakest point. A lab wants
    # coverage, so each is assigned a different stated premise (the missing premise belongs to the
    # Hidden-Premise Attacker); the Director then ranks them by novelty and survival.
    order = sorted(arg.premise_ids, key=lambda p: int(hashlib.sha1((arg.id + p).encode()).hexdigest(), 16))
    tasks = [blind(client, arg, own, s, only=order[i % len(order)]) for i, s in enumerate(blind_specs)]
    tasks.append(hidden(client, arg, own, rest[0]))
    for i, school in enumerate(_schools_for(arg.id)):
        tasks.append(tradition(client, arg, own, rest[(i + 1) % len(rest)], school))
    res = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in res if isinstance(r, Objection)][:max_n]


def _schools_for(arg_id: str) -> list[str]:
    """Two schools per argument, deterministic but varied across arguments."""
    h = int(hashlib.sha1(arg_id.encode()).hexdigest(), 16)
    a = h % len(SCHOOLS)
    b = (a + 1 + (h // 7) % (len(SCHOOLS) - 1)) % len(SCHOOLS)
    return [SCHOOLS[a], SCHOOLS[b]]
