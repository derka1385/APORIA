"""`make run TARGET=<id>`: one full discovery loop on one target.

objections (blind / hidden-premise / tradition / naive) -> novelty -> Director picks trials ->
gauntlet -> revision_required spawns an attack on the revised premise (depth <= 2) -> briefs.
Writes data/runs/<run_id>.json (with every event, for the replay) and data/briefs/*.{json,md}.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone

import numpy as np

from crux_lab.config import RUNS
from crux_lab.corpus.build import load_corpus
from crux_lab.corpus.targets import load_targets
from crux_lab.graph.index import INDEX_DIR, HybridIndex
from crux_lab.graph.schema import SURVIVAL, Argument, Claim, Edge, Objection, Trial
from crux_lab.graph.store import Store
from crux_lab.lab import brief as brief_mod
import os

from crux_lab.lab import cognition, director, generators, novelty

COGNITIVE = os.environ.get("COGNITION", "on") != "off"   # APORIA reasoners as generators (crux_lab/lab/cognition.py)
from crux_lab.lab.gauntlet import run_trial
from crux_lab.llm.budget import BudgetExceeded
from crux_lab.llm.client import LLMClient, ModelSpec

log = logging.getLogger(__name__)
TRIALS_PER_STEP = 2
MAX_BRIEFS = 3


def _is_revised_id(cid: str) -> bool:
    tail = cid.rsplit(".", 1)[-1]
    return tail.startswith("r") and tail[1:].isdigit()


def argument_text(arg: Argument, own: dict[str, Claim], revised: dict[str, str]) -> str:
    lines = [f"{p}: {own[p].text}" for p in arg.premise_ids]
    if arg.missing_premise_id and arg.missing_premise_id in own:
        lines.append(f"{arg.missing_premise_id} (unstated premise the argument needs): {own[arg.missing_premise_id].text}")
    for rid, t in revised.items():
        lines.append(f"{rid} (revised premise adopted after an earlier trial): {t}")
    lines.append(f"Therefore {arg.conclusion_id}: {own[arg.conclusion_id].text}")
    return "\n".join(lines)


def dependence(store: Store, ix: HybridIndex, arg: Argument, own: dict[str, Claim], thr: float = 0.85) -> dict[str, float]:
    """C per premise: share of all graph arguments that use this premise (or a near-identical one)."""
    args = store.all(Argument)
    texts: dict[str, list[str]] = {}
    for a in args:
        cl = {c.id: c for c in store.all(Claim, parent=a.paper_id)}
        texts[a.id] = [cl[p].text for p in a.premise_ids + ([a.missing_premise_id] if a.missing_premise_id else [])
                       if p in cl]
    out = {}
    ids = arg.premise_ids + ([arg.missing_premise_id] if arg.missing_premise_id else [])
    for pid in ids:
        if pid not in own:
            continue
        v = ix.embedder.encode([own[pid].text])[0]
        n = 0
        for a in args:
            if a.id == arg.id:
                n += 1
                continue
            if texts[a.id] and float(np.max(ix.embedder.encode(texts[a.id]) @ v)) >= thr:
                n += 1
        out[pid] = n / max(1, len(args))
    return out


def attacker_spec(client: LLMClient, o: Objection) -> ModelSpec:
    model = o.model.split("→")[-1]
    for s in client.generator_specs():
        if s.model == model:
            return s
    return client.generator_specs()[0]


async def run_target(target: dict, client: LLMClient | None = None, on_event=None) -> dict:
    client = client or LLMClient()
    store = Store()
    papers = {p["id"]: p for p in load_corpus()}
    claims_ix = HybridIndex.load(INDEX_DIR / "claims")
    abstracts_ix = HybridIndex.load(INDEX_DIR / "abstracts", embedder=claims_ix.embedder)
    args = store.all(Argument, parent=target["paper_id"])
    if not args:
        raise RuntimeError(f"target {target['id']} has no mapped argument; run `make map` first")
    arg = args[0]
    # The paper's claims + the Formalizer's missing premise. Revised premises (".rN") from an earlier
    # attempt are dropped; this run re-creates its own and adds them as they appear.
    own = {c.id: c for c in store.all(Claim, parent=target["paper_id"])
           if not (c.level == "generated" and _is_revised_id(c.id))}
    paper = papers.get(target["paper_id"], {"title": target["title"], "id": target["paper_id"]})
    run_id = f"run-{target['id']}"
    started = datetime.now(timezone.utc).isoformat()
    events: list[dict] = []
    revised: dict[str, str] = {}

    async def emit(ev: dict):
        ev = {"t": round(time.time(), 2), **ev}
        events.append(ev)
        if on_event:
            await on_event(ev)

    await emit({"type": "run_start", "run_id": run_id, "target": target["id"], "argument_id": arg.id})
    C = dependence(store, claims_ix, arg, own)
    objections: list[Objection] = []
    nov: dict[str, dict] = {}
    trials: dict[str, Trial] = {}
    outcomes: dict[str, str] = {}
    steps: list[dict] = []
    tried_keys: set[str] = set()
    naive_log: list[dict] = []
    stop_reason = "budget per target reached"

    async def assess(new: list[Objection]):
        new = [o for o in new if o and o.id not in {x.id for x in objections}][: director.MAX_OBJECTIONS - len(objections)]
        for o in new:
            objections.append(o)
            store.put(o)
            await emit({"type": "objection", "objection": o.model_dump()})
        res = await asyncio.gather(*[
            novelty.check(client, o.id, o.text, argument_text(arg, own, revised), o.target_premise_id,
                          own[o.target_premise_id].text if o.target_premise_id in own else revised.get(o.target_premise_id, ""),
                          claims_ix, abstracts_ix, use_live=True, exclude_paper=target["paper_id"])
            for o in new])
        for o, r in zip(new, res):
            nov[o.id] = r.to_dict()
            await emit({"type": "novelty", "objection_id": o.id, "novelty": nov[o.id]["novelty"],
                        "status": nov[o.id]["status"], "reason": nov[o.id]["reason"],
                        "records_searched": nov[o.id]["records_searched"],
                        "nearest": nov[o.id]["nearest"]})

    try:
        # 1. generation, wave one
        wave = await generators.first_wave(client, arg, own, max_n=8, dependence=C)
        if len(client.families) >= 2:
            try:
                q, o = await generators.naive(client, arg, own, client.spec_for("naive_questioner"),
                                              client.generator_specs()[-1])
                naive_log.append({"question": q, "sharpened": o.id if o else None})
                await emit({"type": "naive_question", "question": q, "sharpened": bool(o)})
                if o:
                    wave.append(o)
            except Exception as e:  # noqa: BLE001
                naive_log.append({"error": repr(e)[:200]})
        await assess(wave)

        step, extra_waves = 0, 0
        while len(trials) < director.MAX_TRIALS:
            realized = {oid: SURVIVAL.get(outcomes[oid], 0) * (nov.get(oid, {}).get("novelty") or 0)
                        for oid in outcomes if outcomes[oid] != "failed"}
            learned = cognition.learned_values(objections, realized)
            rows = director.rank(objections, {k: v["novelty"] for k, v in nov.items()}, C, tried_keys, outcomes,
                                 learned=learned)
            if not rows:
                blocked = [o.id for o in objections if o.id not in outcomes and nov.get(o.id, {}).get("novelty") is None]
                why = (f"; {len(blocked)} untested objection(s) left out because their novelty could not be assessed"
                       if blocked else "")
                if len(objections) >= director.MAX_OBJECTIONS:
                    stop_reason = "objection budget used up" + why
                    break
                taken = [o.target_premise_id for o in objections]
                if COGNITIVE:   # APORIA reasoners, best-learned way of thinking first, on the next model family
                    profs = sorted(cognition.PROFILES, key=lambda p: -learned.get(p, 1.0))
                    more = await asyncio.gather(*[cognition.reasoner(client, arg, own, p, taken=taken, dependence=C,
                                                                     revised=revised, offset=extra_waves + 1)
                                                  for p in profs], return_exceptions=True)
                else:
                    more = await asyncio.gather(*[generators.blind(client, arg, own, s, taken=taken, revised=revised)
                                                  for s in client.generator_specs()], return_exceptions=True)
                more = [m for m in more if isinstance(m, Objection)]
                before = len(objections)
                if more and extra_waves < 2:
                    extra_waves += 1
                    await assess(more)
                if len(objections) == before:
                    stop_reason = "generators produced no further new objections" + why
                    break
                continue
            k = min(TRIALS_PER_STEP, director.MAX_TRIALS - len(trials), len(rows))
            picked = [r.objection_id for r in rows[:k]]
            steps.append(director.snapshot(step, rows, picked))
            await emit({"type": "queue", "step": step, "queue": steps[-1]["queue"], "picked": picked})
            by_id = {o.id: o for o in objections}
            for oid in picked:
                await emit({"type": "trial_start", "trial_id": f"trial-{oid}", "objection_id": oid})
            done = await asyncio.gather(*[
                run_trial(client, store, by_id[oid], argument_text(arg, own, revised), claims_ix, nov.get(oid),
                          f"trial-{oid}", attacker_spec(client, by_id[oid]), on_event=emit) for oid in picked])
            for t in done:
                o = by_id[t.objection_id]
                trials[o.id] = t
                outcomes[o.id] = t.outcome if t.status == "ok" and t.outcome else "failed"
                tried_keys.add(director.explore_key(o))
                store.put(t)
                if t.status == "ok" and t.outcome == "revision_required" and t.revised_premise \
                        and o.depth < director.MAX_DEPTH \
                        and len(objections) < director.MAX_OBJECTIONS:
                    rid = f"{arg.id}.r{len(revised) + 1}"
                    revised[rid] = t.revised_premise
                    rc = Claim(id=rid, paper_id=arg.paper_id, kind="premise", text=t.revised_premise, level="generated")
                    store.put(rc)
                    own[rid] = rc
                    store.put(Edge(src=rid, dst=arg.conclusion_id, relation="supports"))
                    store.put(Edge(src=o.id, dst=o.target_premise_id, relation="attacks"))
                    await emit({"type": "revised_premise", "id": rid, "text": t.revised_premise, "from_trial": t.id})
                    untried = [s for s in client.generator_specs() if f"blind_thought_experimenter|{s.family}" not in tried_keys] \
                        or client.generator_specs()
                    if COGNITIVE:   # the revised premise is attacked by the way of thinking that has learned most
                        best = max(cognition.PROFILES, key=lambda p: learned.get(p, 0.0))
                        nxt = await cognition.reasoner(client, arg, own, best, depth=o.depth + 1, dependence=C,
                                                       revised={rid: t.revised_premise}, only=rid, offset=step + 1)
                    else:
                        nxt = await generators.blind(client, arg, own, untried[0], depth=o.depth + 1,
                                                     revised={rid: t.revised_premise}, only=rid)
                    if nxt:
                        C[rid] = 1 / max(1, store.count(Argument))
                        await assess([nxt])
            step += 1
        else:
            stop_reason = "trial budget per target reached (6)"
    except BudgetExceeded as e:
        stop_reason = f"budget exceeded: {e}"
        log.warning(stop_reason)

    # briefs: surviving objections first (standing, revision_required), else the best rebutted; only complete
    # trials whose novelty was assessed can become a scored brief
    eligible = [t for t in trials.values() if t.status == "ok" and novelty.is_assessed(nov.get(t.objection_id))]
    ranked = sorted(eligible, key=lambda t: (-SURVIVAL.get(t.outcome or "misreading", 0),
                                             -nov[t.objection_id]["novelty"]))
    chosen = [t for t in ranked if t.outcome in ("standing", "revision_required")][:MAX_BRIEFS] or \
        [t for t in ranked if t.outcome == "rebutted"][:1]
    briefs = []
    by_id = {o.id: o for o in objections}
    for t in chosen:
        try:
            b = await brief_mod.write_brief(client, arg, own, by_id[t.objection_id], t, nov.get(t.objection_id, {}),
                                            paper, papers, revised)
            if b is None:
                continue
            store.put(b)
            brief_mod.save(b, by_id[t.objection_id])
            briefs.append(b.id)
            await emit({"type": "brief", "brief_id": b.id, "objection_id": t.objection_id})
        except BudgetExceeded:
            break
    await emit({"type": "run_end", "stop_reason": stop_reason})

    fams = sorted({f for o in objections for f in o.family.split("→")} |
                  {t2.family for t in trials.values() for t2 in t.rounds})
    run = {
        "run_id": run_id, "target": target, "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(), "stop_reason": stop_reason,
        "argument": arg.model_dump(), "claims": {k: v.model_dump(exclude={"embedding"}) for k, v in own.items()},
        "revised_premises": revised, "dependence": C,
        "objections": [o.model_dump() for o in objections],
        "novelty": nov, "trials": [t.model_dump() for t in trials.values()],
        "cognition": cognition.run_metrics(objections, trials, nov, briefs, claims_ix.embedder) if COGNITIVE else None,
        "director_steps": steps, "briefs": briefs, "naive_questioner": naive_log,
        "families_used": fams,
        "models": {r: (client.spec_for(r).label) for r in ("defender_a", "defender_b", "referee", "extractor", "reranker")},
        "generators": [s.label for s in client.generator_specs()],
        "diversity": client.resolved.get("diversity"),
        "llm_stats": client.stats, "budget": client.budget.summary(), "events": events,
    }
    RUNS.mkdir(parents=True, exist_ok=True)
    (RUNS / f"{run_id}.json").write_text(json.dumps(run, indent=1, ensure_ascii=False))
    return run


def find_target(tid: str) -> dict:
    for t in load_targets():
        if tid in (t["id"], t["paper_id"]) or t["id"].endswith(tid):
            return t
    raise SystemExit(f"unknown target {tid}; see data/targets.json")


async def main(tid: str) -> None:
    run = await run_target(find_target(tid))
    outs = [t["outcome"] for t in run["trials"]]
    print(f"{run['run_id']}: {len(run['objections'])} objections, {len(run['trials'])} trials {outs}, "
          f"briefs {run['briefs']}, stop: {run['stop_reason']}")


def snapshot_models(client: LLMClient) -> None:
    """Keep the model assignment a topic's runs used, so its exported /about stays true later."""
    from crux_lab.config import TOPIC_RESOLVED
    TOPIC_RESOLVED.write_text(json.dumps(client.resolved, indent=2))


async def main_all(only: list[str] | None = None, skip: list[str] | None = None) -> None:
    targets = [t for t in load_targets() if (not only or t["id"] in only) and t["id"] not in (skip or [])]
    client = LLMClient()   # one client => shared per-provider concurrency limits across targets
    snapshot_models(client)
    res = await asyncio.gather(*[run_target(t, client) for t in targets], return_exceptions=True)
    for t, r in zip(targets, res):
        if isinstance(r, Exception):
            print(f"{t['id']}: FAILED {r!r}")
        else:
            print(f"{r['run_id']}: {len(r['objections'])} objections, "
                  f"{[x['outcome'] for x in r['trials']]}, briefs {len(r['briefs'])}")
