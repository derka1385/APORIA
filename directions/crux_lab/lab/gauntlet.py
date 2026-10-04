"""The gauntlet: Referee pre-screen -> quick prior art -> Defender A and B exchanges -> Referee labels.

The objection keeps the outcome most favourable to the original argument (lowest survival): it
must survive both defenders. Citations are corpus claim ids only; the Referee step verifies each
id (exists in the store AND was in the literature the defender was shown) and strikes the rest.
"""
from __future__ import annotations

import asyncio
import logging

from pydantic import BaseModel

from crux_lab.agents.roles import render
from crux_lab.graph.extract import quote_found
from crux_lab.graph.index import HybridIndex
from crux_lab.graph.schema import OUTCOME_ORDER, SURVIVAL, Claim, Objection, Trial, Turn
from crux_lab.graph.store import Store
from crux_lab.lab.debate import EventFn, render_transcript, run_exchange
from crux_lab.llm.client import LLMClient, ModelSpec

log = logging.getLogger(__name__)


class PrescreenOut(BaseModel):
    misreading: bool
    explanation: str
    deciding_quote: str


class LabelOut(BaseModel):
    outcome: str
    deciding_quote: str
    rationale: str
    revised_premise: str | None = None


def literature_for(objection: Objection, novelty: dict | None, claims_ix: HybridIndex, store: Store,
                   k: int = 10) -> tuple[str, set[str]]:
    """Retrieved corpus claims for the defenders: prior-art matches first, then hybrid search."""
    ids: list[str] = []
    for m in (novelty or {}).get("matches", []):
        if m["verdict"] in ("same_move", "related") and m["record_id"] in claims_ix.ids:
            ids.append(m["record_id"])
    for h in claims_ix.search(objection.text, k=k * 2):
        if h.id not in ids:
            ids.append(h.id)
    ids = ids[:k]
    lines, allowed = [], set()
    for cid in ids:
        c = store.get(Claim, cid)
        if not c:
            continue
        i = claims_ix.ids.index(cid)
        title = claims_ix.metas[i].get("title", "")
        lines.append(f"{cid}: [{c.kind}] {c.text} — {title[:100]}")
        allowed.add(cid)
    return "\n".join(lines), allowed


def own_prefix(objection: Objection) -> str:
    """Claim ids of the target paper itself start with its short id (e.g. 'W7203761940.')."""
    return objection.argument_id.split(".", 1)[0] + "."


def verify_citations(turns: list[Turn], allowed: set[str], store: Store,
                     own: str = "\0") -> tuple[list[str], list[str]]:
    """A cited id survives if it exists in the store and was either in the literature the defender
    was shown or belongs to the argument's own paper (the defender saw those ids in the argument)."""
    verified, struck = [], []
    for t in turns:
        good, bad = [], []
        for cid in t.cited_claim_ids:
            ok = (cid in allowed or cid.startswith(own)) and store.get(Claim, cid) is not None
            (good if ok else bad).append(cid)
        t.cited_claim_ids, t.struck_claim_ids = good, bad
        verified += good
        struck += bad
    return list(dict.fromkeys(verified)), list(dict.fromkeys(struck))


async def label(client: LLMClient, referee: ModelSpec, argument: str, objection: Objection,
                turns: list[Turn], verified: list[str], struck: list[str]) -> LabelOut | None:
    transcript = render_transcript(turns)
    system, user = render("referee_label", argument=argument, objection=objection.text,
                          target_id=objection.target_premise_id, verified=", ".join(verified) or "none",
                          struck=", ".join(struck) or "none", transcript=transcript)

    def check(o: LabelOut) -> str | None:
        if o.outcome not in SURVIVAL:
            return f"outcome must be one of {list(SURVIVAL)}"
        if o.outcome == "known_answer" and not verified:
            return "known_answer requires a verified cited literature id; none exists here, choose another outcome"
        if not quote_found(o.deciding_quote, transcript):
            return "deciding_quote must be copied verbatim from the transcript"
        if o.outcome == "revision_required" and not o.revised_premise:
            return "give the revised premise for revision_required"
        return None
    out, _ = await client.json("referee", user, LabelOut, system, spec=referee, validate=check)
    return out


async def run_trial(client: LLMClient, store: Store, objection: Objection, argument_text: str,
                    claims_ix: HybridIndex, novelty: dict | None, trial_id: str,
                    attacker: ModelSpec, on_event: EventFn = None) -> Trial:
    referee = client.spec_for("referee")
    trial = Trial(id=trial_id, objection_id=objection.id)

    async def emit(ev: dict):
        if on_event:
            await on_event({**ev, "trial_id": trial_id, "objection_id": objection.id})

    try:
        # 1. pre-screen for misreading
        system, user = render("referee_prescreen", argument=argument_text, objection=objection.text,
                              target_id=objection.target_premise_id)
        pre, _ = await client.json("referee", user, PrescreenOut, system, spec=referee,
                                   validate=lambda o: None if quote_found(o.deciding_quote, objection.text)
                                   else "deciding_quote must be copied verbatim from the objection")
        if pre:
            t = Turn(exchange=0, speaker="referee", phase="prescreen", model=referee.model, family=referee.family,
                     content=f"{'Misreading' if pre.misreading else 'Not a misreading'}: {pre.explanation}")
            trial.rounds.append(t)
            await emit({"type": "turn", "turn": t.model_dump()})
            if pre.misreading:
                trial.outcome, trial.rationale, trial.deciding_quote = "misreading", pre.explanation, pre.deciding_quote
                return trial
        # 2. quick prior art -> literature for the defenders
        literature, allowed = literature_for(objection, novelty, claims_ix, store)
        # 3. two independent exchanges
        specs = {"defender_a": client.spec_for("defender_a"), "defender_b": client.spec_for("defender_b")}
        ex = await asyncio.gather(*[
            run_exchange(client, speaker=s, defender=specs[s], attacker=attacker, argument=argument_text,
                         objection=objection.text, target_id=objection.target_premise_id,
                         literature=literature, exchange=i + 1, on_event=emit)
            for i, s in enumerate(specs)])
        # 4. referee labels each defense, citations verified first
        per = {}
        all_verified: list[str] = []
        own = own_prefix(objection)
        from crux_lab.corpus.dedup import work_of
        own_work = work_of("oa:" + own.rstrip("."))

        def is_own(cid: str) -> bool:
            if cid.startswith(own):
                return True
            c = store.get(Claim, cid)       # another record of the same work is still the argument's own paper
            return bool(c) and work_of(c.paper_id) == own_work

        for s, turns in zip(specs, ex):
            verified, struck = verify_citations(turns, allowed, store, own)
            all_verified += verified
            literature = [c for c in verified if not is_own(c)]   # only these can make a known_answer
            lab = await label(client, referee, argument_text, objection, turns, literature, struck)
            trial.rounds += turns
            if lab:
                per[s] = {"outcome": lab.outcome, "rationale": lab.rationale, "deciding_quote": lab.deciding_quote,
                          "revised_premise": lab.revised_premise, "verified": verified, "struck": struck,
                          "model": specs[s].model, "family": specs[s].family}
                lt = Turn(exchange=turns[0].exchange if turns else 0, speaker="referee", phase="label",
                          model=referee.model, family=referee.family,
                          content=f"{lab.outcome}: {lab.rationale}")
                trial.rounds.append(lt)
                await emit({"type": "turn", "turn": lt.model_dump()})
        trial.per_defender = per
        trial.cited_claim_ids = list(dict.fromkeys(all_verified))     # evidence kept even if incomplete
        missing = [s for s in specs if s not in per]
        if missing:
            # the outcome must survive *both* defenders: with a label missing there is no combined outcome
            trial.missing_labels = missing
            trial.status = "failed"
            trial.error = f"incomplete defender assessment: missing {', '.join(missing)}"
            return trial
        best = min(per.values(), key=lambda d: OUTCOME_ORDER.index(d["outcome"]))
        trial.outcome = best["outcome"]
        trial.rationale, trial.deciding_quote = best["rationale"], best["deciding_quote"]
        trial.revised_premise = best["revised_premise"] if best["outcome"] == "revision_required" else None
    except Exception as e:  # noqa: BLE001 - a failed trial is recorded and shown as failed
        log.exception("trial %s failed", trial_id)
        trial.status, trial.error = "failed", repr(e)[:300]
    finally:
        await emit({"type": "trial_end", "outcome": trial.outcome if trial.status == "ok" else None,
                    "status": trial.status, "error": trial.error, "missing_labels": trial.missing_labels})
    return trial
