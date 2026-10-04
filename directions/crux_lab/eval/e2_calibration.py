"""E2 gauntlet calibration on the canonical hiddenness argument (fixture).

(a) 10 published objections whose published replies are in the corpus: correct = labelled
    known_answer AND a claim from the replying paper is cited and verified.
(b) 10 deliberate misreadings (a premise distorted on purpose): correct = labelled misreading."""
from __future__ import annotations

import asyncio
import random

from pydantic import BaseModel

from crux_lab.graph.schema import trial_complete
from crux_lab.agents.roles import render
from crux_lab.corpus.build import load_corpus
from crux_lab.eval.common import canonical_argument, canonical_text, model_ids, stamp, write
from crux_lab.graph.index import INDEX_DIR, HybridIndex
from crux_lab.graph.schema import Claim, Objection
from crux_lab.graph.store import Store
from crux_lab.lab.gauntlet import run_trial
from crux_lab.llm.client import LLMClient

N_KNOWN = 10
N_MISREAD = 10


class Pair(BaseModel):
    usable: bool
    objection: str = ""
    target_premise_id: str = ""


class Misread(BaseModel):
    objection: str
    distorted_claim: str


class Replies(BaseModel):
    reply_numbers: list[int]


async def build_known(client: LLMClient, store: Store, fx: dict, n: int, ix: HybridIndex) -> list[dict]:
    """Published objection (a claim from paper A) + published reply (paper B != A, found by retrieval and
    confirmed by an LLM judge). Correct later = known_answer citing a claim from one of the B papers."""
    corpus = {p["id"]: p for p in load_corpus() if not p.get("fresh")}
    cands = [c for c in store.all(Claim) if c.level == "abstract" and c.paper_id in corpus
             and c.kind in ("objection", "conclusion", "reply")]
    random.Random(11).shuffle(cands)
    text = canonical_text(fx)
    out: list[dict] = []

    async def one(c: Claim):
        system, user = render("eval_objection", argument=text, title=corpus[c.paper_id]["title"], claim=c.text)
        r, _ = await client.json("reranker", user, Pair, system,
                                 validate=lambda o: None if (not o.usable or o.target_premise_id in fx["premises"])
                                 else f"target_premise_id must be one of {list(fx['premises'])}")
        if not (r and r.usable and r.objection):
            return None
        hits = [h for h in ix.search(r.objection, k=24) if h.meta.get("paper_id") != c.paper_id][:12]
        if not hits:
            return None
        listing = "\n\n".join(f"[{i + 1}] ({h.meta.get('title', '')[:90]}) {h.text}" for i, h in enumerate(hits))
        system, user = render("eval_find_reply", argument=text, target=r.target_premise_id, objection=r.objection,
                              passages=listing)
        rep, _ = await client.json("reranker", user, Replies, system)
        idx = [k for k in (rep.reply_numbers if rep else []) if 1 <= k <= len(hits)]
        if not idx:
            return None
        replies = [hits[k - 1] for k in idx]
        return {"objection": r.objection, "target": r.target_premise_id, "objection_paper": c.paper_id,
                "objection_claim": c.id, "reply_claims": [h.id for h in replies],
                "reply_papers": sorted({h.meta["paper_id"] for h in replies})}

    for i in range(0, len(cands), 12):
        for item in await asyncio.gather(*[one(c) for c in cands[i:i + 12]]):
            if item and item["objection_paper"] not in {x["objection_paper"] for x in out}:
                out.append(item)
        if len(out) >= n or i > 120:
            break
    return out[:n]


async def build_misreadings(client: LLMClient, fx: dict, n: int) -> list[dict]:
    text = canonical_text(fx)
    pids = list(fx["premises"])
    variants = ["attack a much stronger claim than the premise states",
                "attack a different notion (e.g. a different kind of belief, love or relationship) than the premise uses"]
    jobs = [(pids[i % len(pids)], variants[(i // len(pids)) % 2]) for i in range(n)]

    async def one(pid, variant):
        system, user = render("eval_misread", argument=text, premise_id=pid, variant=variant)
        r, _ = await client.json("generator", user, Misread, system, spec=client.generator_specs()[0])
        return {"objection": r.objection, "target": pid, "distorted_claim": r.distorted_claim, "variant": variant} if r else None
    res = await asyncio.gather(*[one(p, v) for p, v in jobs])
    return [r for r in res if r]


async def run(client: LLMClient | None = None) -> dict:
    client = client or LLMClient()
    store = Store()
    fx = canonical_argument()
    text = canonical_text(fx)
    ix = HybridIndex.load(INDEX_DIR / "claims")
    known = await build_known(client, store, fx, N_KNOWN, ix)
    mis = await build_misreadings(client, fx, N_MISREAD)
    gen = client.generator_specs()[0]

    async def trial(i: int, item: dict, kind: str):
        o = Objection(id=f"E2.{kind}.{i}", argument_id=fx["id"], target_premise_id=item["target"], kind=kind,
                      text=item["objection"], agent="eval", model=gen.model, family=gen.family)
        return item, await run_trial(client, store, o, text, ix, None, f"trial-E2.{kind}.{i}", gen)

    sem = asyncio.Semaphore(4)

    async def guarded(*a):
        async with sem:
            return await trial(*a)
    res_k = await asyncio.gather(*[guarded(i, it, "known") for i, it in enumerate(known)])
    res_m = await asyncio.gather(*[guarded(i, it, "misread") for i, it in enumerate(mis)])
    items = []
    k_label = k_correct = k_gold_cited = k_done = 0
    from crux_lab.corpus.dedup import work_of
    for it, t in res_k:
        gold_works = {work_of(p) for p in it["reply_papers"]}       # any record of a gold reply paper counts
        cited_works = {work_of(c.paper_id) for cid in t.cited_claim_ids if (c := store.get(Claim, cid))}
        cited_right = bool(gold_works & cited_works)
        k_gold_cited += cited_right
        done = trial_complete(t.model_dump())          # an incomplete trial is attempted, never a success
        k_done += done
        k_label += done and t.outcome == "known_answer"
        k_correct += done and t.outcome == "known_answer" and cited_right
        items.append({"kind": "known_answer", "source_paper": ", ".join(it["reply_papers"]),
                      "objection_paper": it["objection_paper"], "reply_claims": it["reply_claims"],
                      "objection": it["objection"],
                      "target": it["target"], "outcome": t.outcome, "cited": t.cited_claim_ids,
                      "correct": done and t.outcome == "known_answer" and cited_right, "status": t.status,
                      "complete": done})
    caught = m_done = 0
    for it, t in res_m:
        done = trial_complete(t.model_dump())
        m_done += done
        caught += done and t.outcome == "misreading"
        items.append({"kind": "misreading", "source_paper": "", "objection": it["objection"], "target": it["target"],
                      "distorted_claim": it["distorted_claim"], "outcome": t.outcome,
                      "correct": done and t.outcome == "misreading", "status": t.status, "complete": done})
    data = {
        "experiment": "E2 gauntlet calibration", "n": len(items),
        "known_answer": {"n": len(res_k), "trials_completed": k_done, "labelled_known_answer": k_label,
                         "correct_reply_cited": k_correct, "gold_reply_cited_by_a_defender": k_gold_cited},
        "misreading": {"n": len(res_m), "trials_completed": m_done, "caught": caught},
        "items": items,
        "settings": {"argument": fx["title"], "fixture_note": fx["note"],
                     "known_items": ("objection: an LLM restates a corpus claim (paper A) as an objection to one premise; reply: "
                                     "hybrid retrieval over the claim index (excluding paper A), then an LLM judge keeps "
                                     "passages that answer the objection (paper B). Correct = known_answer citing a B claim."),
                     "misreading_items": "LLM-written objections that attack a distorted premise (2 variants x 4 premises, round robin)",
                     "gauntlet": "full: pre-screen, two defenders with retrieved literature, referee labels"},
        "models": model_ids(client, ["defender_a", "defender_b", "referee", "reranker"]) | {"misreading_writer": gen.label},
        "timestamp": stamp(),
        "limits": ("correct_reply_cited counts items labelled known_answer whose verified citations include a gold "
                   "reply paper; gold_reply_cited_by_a_defender counts items where a defender cited (verified) a claim "
                   "from a gold reply paper, whatever the label. Small n (10 + 10). Objections are LLM restatements of published claims, and the 'published reply' is "
                   "chosen by retrieval + an LLM judge from abstract-level claims, so both the pairing and the gold reply are "
                   "model-made. A first version of this eval paired each objection with its own source paper as the 'reply' "
                   "(0/10 correct by construction) and was discarded. "
                   "Misreadings are written by a model from the same pool as the defenders. The argument is a paraphrased "
                   "fixture, not a corpus record. No human labels."),
    }
    write("e2", data)
    return data
