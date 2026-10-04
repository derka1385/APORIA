"""E3 diversity ablation: objections to the same 5 target arguments under three conditions:
plain prompt / one model; constrained roles / one model; constrained roles / mixed families.
Metrics: distinct premises targeted, mean pairwise embedding distance, share passing the
Referee's misreading pre-screen, share surviving a full gauntlet trial, share with novelty > 0.5."""
from __future__ import annotations

import asyncio
import itertools

import numpy as np
from pydantic import BaseModel

from crux_lab.agents.roles import render
from crux_lab.eval.common import model_ids, stamp, write
from crux_lab.graph.index import INDEX_DIR, HybridIndex
from crux_lab.graph.schema import Argument, Claim, Objection
from crux_lab.graph.store import Store
from crux_lab.graph.schema import trial_complete
from crux_lab.lab import generators, novelty
from crux_lab.lab.gauntlet import PrescreenOut, run_trial
from crux_lab.lab.run import argument_text
from crux_lab.llm.client import LLMClient, ModelSpec

PER_ARG = 4
SURVIVING = ("revision_required", "standing")   # survival S >= 0.8
MIN_TRIALS_OK = 0.8                              # report survival only if >= 80% of a condition's trials completed


class Plain(BaseModel):
    target_premise_id: str
    objection: str


async def plain(client, arg, own, spec: ModelSpec) -> list[Objection]:
    allowed = set(arg.premise_ids) | ({arg.missing_premise_id} if arg.missing_premise_id else set())
    ctx = generators.argument_context(arg, own)

    async def one(k):
        system, user = render("eval_plain", argument=ctx, k=k + 1, n=PER_ARG)
        o, _ = await client.json("generator", user, Plain, system, spec=spec,
                                 validate=lambda o: None if o.target_premise_id in allowed else f"use one of {sorted(allowed)}")
        return Objection(id=f"E3.plain.{arg.id}.{k}", argument_id=arg.id, target_premise_id=o.target_premise_id,
                         kind="plain", text=o.objection, agent="plain", model=spec.model, family=spec.family) if o else None
    return [o for o in await asyncio.gather(*[one(k) for k in range(PER_ARG)]) if o]


async def constrained(client, arg, own, specs: list[ModelSpec]) -> list[Objection]:
    s = itertools.cycle(specs)
    first = await generators.blind(client, arg, own, next(s))
    tasks = [generators.blind(client, arg, own, next(s), taken=[first.target_premise_id] if first else [])]
    if arg.missing_premise_id:
        tasks.append(generators.hidden(client, arg, own, next(s)))
    else:
        tasks.append(generators.blind(client, arg, own, next(s), taken=["(any)"]))
    tasks.append(generators.tradition(client, arg, own, next(s), generators._schools_for(arg.id)[0]))
    rest = await asyncio.gather(*tasks, return_exceptions=True)
    return [o for o in [first, *rest] if isinstance(o, Objection)]


def pairwise_distance(vecs: np.ndarray) -> float:
    if len(vecs) < 2:
        return 0.0
    sims = [float(vecs[i] @ vecs[j]) for i in range(len(vecs)) for j in range(i + 1, len(vecs))]
    return 1 - float(np.mean(sims))


async def run(client: LLMClient | None = None) -> dict:
    client = client or LLMClient()
    store = Store()
    claims_ix = HybridIndex.load(INDEX_DIR / "claims")
    abstracts_ix = HybridIndex.load(INDEX_DIR / "abstracts", embedder=claims_ix.embedder)
    gens = client.generator_specs()
    one = next((g for g in gens if g.family == "openai"), gens[0])
    args = store.all(Argument)[:5]
    conds = {
        "plain prompt, one model": lambda a, own: plain(client, a, own, one),
        "constrained roles, one model": lambda a, own: constrained(client, a, own, [one]),
        "constrained roles, mixed families": lambda a, own: constrained(client, a, own, gens),
    }
    referee = client.spec_for("referee")
    trial_sem = asyncio.Semaphore(6)
    by_model = {g.model: g for g in gens}

    def attacker_for(o: Objection) -> ModelSpec:
        return by_model.get(o.model, gens[0])

    out_rows = []
    per_obj = []
    for name, fn in conds.items():
        objs_by_arg = {}
        for a in args:
            own = {c.id: c for c in store.all(Claim, parent=a.paper_id)}
            objs_by_arg[a.id] = (await fn(a, own), own, a)
        distinct, dists, pass_pre, novel, n, surv, outcomes, n_ok = [], [], 0, 0, 0, 0, {}, 0
        n_nov = 0          # novelty checks that completed: the denominator for share_novelty_gt_05
        for aid, (objs, own, a) in objs_by_arg.items():
            if not objs:
                continue
            distinct.append(len({o.target_premise_id for o in objs}))
            dists.append(pairwise_distance(claims_ix.embedder.encode([o.text for o in objs])))
            atext = argument_text(a, own, {})

            async def assess(o, atext=atext, own=own, a=a):   # bind this iteration's argument explicitly
                system, user = render("referee_prescreen", argument=atext, objection=o.text,
                                      target_id=o.target_premise_id)
                pre, _ = await client.json("referee", user, PrescreenOut, system, spec=referee)
                nv = await novelty.check(client, o.id, o.text, atext, o.target_premise_id,
                                         own[o.target_premise_id].text if o.target_premise_id in own else "",
                                         claims_ix, abstracts_ix, use_live=False, exclude_paper=a.paper_id)
                async with trial_sem:
                    t = await run_trial(client, store, o, atext, claims_ix, nv.to_dict(), f"trial-{o.id}",
                                        attacker_for(o))
                return o, pre, nv, t
            for o, pre, nv, t in await asyncio.gather(*[assess(o) for o in objs]):
                n += 1
                ok_pre = bool(pre and not pre.misreading)
                pass_pre += ok_pre
                done = trial_complete(t.model_dump())
                if nv.novelty is not None:
                    n_nov += 1
                    novel += nv.novelty > 0.5
                surv += done and t.outcome in SURVIVING
                n_ok += done
                k_out = t.outcome if done else "failed"
                outcomes[k_out] = outcomes.get(k_out, 0) + 1
                per_obj.append({"condition": name, "objection_id": o.id, "argument_id": aid, "target": o.target_premise_id,
                                "family": o.family, "model": o.model, "passes_prescreen": ok_pre,
                                "outcome": t.outcome, "trial_status": t.status,
                                "novelty": round(nv.novelty, 3) if nv.novelty is not None else None,
                                "novelty_status": nv.status, "text": o.text})
        out_rows.append({"name": name, "n": n,
                         "distinct_premises": round(float(np.mean(distinct)), 2) if distinct else 0,
                         "mean_pairwise_distance": round(float(np.mean(dists)), 3) if dists else 0,
                         "share_surviving": (round(surv / max(1, n_ok), 3)
                                             if n and n_ok / n >= MIN_TRIALS_OK else None),
                         "trials_completed": n_ok, "outcomes": outcomes,
                         "share_passing_prescreen": round(pass_pre / max(1, n), 3),
                         "novelty_assessed": n_nov, "novelty_unavailable": n - n_nov,
                         # denominator: completed novelty checks only; None when none completed
                         "share_novelty_gt_05": round(novel / n_nov, 3) if n_nov else None})
    incomplete = [r["name"] for r in out_rows if r["share_surviving"] is None]
    counts = "; ".join("%s: %d/%d" % (r["name"], r["trials_completed"], r["n"]) for r in out_rows)
    trial_note = ("" if not incomplete else
                  f" Full trials were attempted for every objection, but fewer than {MIN_TRIALS_OK:.0%} completed in "
                  f"{len(incomplete)} condition(s) ({counts} trials completed) because the OpenAI/Codex provider hit its ChatGPT workspace spend cap during the run; "
                  "share_surviving is therefore reported as not available for those conditions rather than computed on a "
                  "biased remainder.")
    data = {
        "experiment": "E3 diversity ablation", "conditions": out_rows, "objections": per_obj,
        "settings": {"arguments": [a.id for a in args], "objections_per_argument": PER_ARG,
                     "one_model": one.label, "mixed": [g.label for g in gens],
                     "distinct_premises": "mean per argument of distinct premise ids targeted (out of 4 objections)",
                     "embedder": claims_ix.embedder.name, "novelty": "lab novelty check without live OpenAlex",
                     "share_novelty_gt_05": "share of completed novelty checks scoring above 0.5 "
                                            "(checks that could not be assessed are counted in novelty_unavailable)"},
        "models": model_ids(client, ["referee", "reranker"]) | {"one_model": one.label},
        "timestamp": stamp(),
        "limits": ("Only 2 model families were available (anthropic, openai), so 'mixed families' means 2 families. "
                   "share_surviving = share of objections whose full gauntlet trial (pre-screen, two defenders, Referee) "
                   "ended in revision_required or standing (S >= 0.8); trials use the lab's gauntlet without updating "
                   "the argument between trials. "
                   "CLI providers ignore temperature, so 'plain' variation comes from the 'objection k of n' prompt. "
                   "5 arguments x 4 objections per condition." + trial_note),
    }
    write("e3", data)
    return data
