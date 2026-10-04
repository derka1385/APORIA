"""Formalizer: argument -> propositional skeleton; truth table decides validity; a proposed missing
premise must make the argument valid on re-check (enforced in code, fed back on failure)."""
from __future__ import annotations

import logging

from pydantic import BaseModel

from crux_lab.agents.roles import render
from crux_lab.graph import logic
from crux_lab.graph.schema import Argument, Claim
from crux_lab.llm.client import LLMClient

log = logging.getLogger(__name__)


class MissingPremise(BaseModel):
    text: str
    formula: str


class FormalOut(BaseModel):
    atoms: dict[str, str]
    premise_formulas: dict[str, str]
    conclusion_formula: str
    missing_premise: MissingPremise | None = None


def skeleton_of(out: FormalOut, premise_ids: list[str]) -> str:
    prem = "; ".join(out.premise_formulas[p] for p in premise_ids)
    return f"{prem} |- {out.conclusion_formula}"


def validator(premise_ids: list[str]):
    def check(out: FormalOut) -> str | None:
        bad_atoms = [a for a in out.atoms if a not in logic.ATOMS or len(a) != 1]
        if bad_atoms:
            return f"atoms must be single letters A-H, got {bad_atoms}"
        missing = [p for p in premise_ids if p not in out.premise_formulas]
        if missing:
            return f"give a formula for every premise id; missing {missing}"
        formulas = [out.premise_formulas[p] for p in premise_ids] + [out.conclusion_formula]
        if out.missing_premise:
            formulas.append(out.missing_premise.formula)
        for f in formulas:
            try:
                node = logic.parse(f)
            except logic.ParseError as e:
                return f"formula {f!r} does not parse: {e}"
            undeclared = node.atoms() - set(out.atoms)
            if undeclared:
                return f"formula {f!r} uses undeclared atoms {sorted(undeclared)}"
        sk = skeleton_of(out, premise_ids)
        if logic.check_skeleton(sk):
            return None   # valid as stated; any proposed missing premise is simply dropped
        if not out.missing_premise:
            cx = logic.counterexample(*logic.split_skeleton(sk))
            return (f"the stated premises do NOT entail the conclusion (truth-table counterexample: {cx}); "
                    "propose the missing premise")
        if not logic.missing_premise_fixes(sk, out.missing_premise.formula):
            return (f"your missing premise {out.missing_premise.formula!r} does not make the argument valid "
                    "(or makes the premises inconsistent); propose one that does")
        return None
    return check


async def formalize(client: LLMClient, arg: Argument, claims: dict[str, Claim]) -> tuple[Argument, Claim | None]:
    premises = "\n".join(f"{pid}: {claims[pid].text}" for pid in arg.premise_ids)
    system, user = render("formalizer", title=arg.title, premises=premises,
                          conclusion_id=arg.conclusion_id, conclusion=claims[arg.conclusion_id].text)
    out, _ = await client.json("formalizer", user, FormalOut, system, validate=validator(arg.premise_ids),
                               max_tokens=2500)
    if not out:
        log.warning("formalizer failed for %s", arg.id)
        return arg, None
    sk = skeleton_of(out, arg.premise_ids)
    valid = logic.check_skeleton(sk)
    upd: dict = {"skeleton": sk, "atoms": out.atoms, "valid": valid}
    mp_claim = None
    if not valid and out.missing_premise:
        mp_id = f"{arg.id}.mp"
        mp_claim = Claim(id=mp_id, paper_id=arg.paper_id, kind="assumption", text=out.missing_premise.text,
                         quote="", level="generated")
        upd.update(missing_premise=f"{out.missing_premise.text} [{out.missing_premise.formula}]",
                   missing_premise_id=mp_id)
    return arg.model_copy(update=upd), mp_claim

