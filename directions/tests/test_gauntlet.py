import asyncio
import json

from crux_lab.graph.index import Embedder, HybridIndex
from crux_lab.graph.schema import Claim, Objection
from crux_lab.graph.store import Store
from crux_lab.lab.gauntlet import run_trial
from crux_lab.llm.client import LLMClient

OBJ = Objection(id="o1", argument_id="arg", target_premise_id="X.c1", kind="k",
                text="Mara leaves the door open every night, yet the patient never comes to believe she is there.",
                agent="blind_thought_experimenter", model="fake-fakefam-a", family="fakefam-a")


def make_env(tmp_path):
    store = Store(tmp_path / "s.sqlite")
    lit = Claim(id="Y.c001", paper_id="oa:Y", kind="reply", text="Openness need not produce belief.", quote="q")
    store.put(lit)
    emb = Embedder("lsa")
    ix = HybridIndex(["Y.c001"], [lit.text], [{"paper_id": "oa:Y", "title": "Paper Y"}], embedder=emb)
    return store, ix


def responder_factory(label_outcomes):
    labels = iter(label_outcomes)

    def responder(system, messages, model):
        if "Pre-screen" in system:
            return json.dumps({"misreading": False, "explanation": "attacks the premise as stated",
                               "deciding_quote": "Mara leaves the door open every night"})
        if "label the dialectical outcome" in system:
            o = next(labels)
            return json.dumps({"outcome": o, "deciding_quote": "Openness need not produce belief",
                               "rationale": "r", "revised_premise": "New P" if o == "revision_required" else None})
        if "defend the argument" in system:
            return json.dumps({"misreading_check": "no", "reply": "Openness need not produce belief [Y.c001] [Z.c999].",
                               "cited_claim_ids": ["Y.c001", "Z.c999"], "concedes": False, "revised_premise": None})
        return "Your reply misses the case."
    return responder


def test_trial_keeps_outcome_most_favourable_to_argument_and_strikes_bad_ids(tmp_path):
    store, ix = make_env(tmp_path)
    client = LLMClient.fake(responder_factory(["standing", "rebutted"]))
    t = asyncio.run(run_trial(client, store, OBJ, "X.c1: P\nTherefore X.c2: C", ix, None, "trial-o1",
                              client.generator_specs()[0]))
    assert t.status == "ok" and t.outcome == "rebutted"
    assert t.cited_claim_ids == ["Y.c001"]
    assert any("Z.c999" in turn.struck_claim_ids for turn in t.rounds)
    speakers = [r.speaker for r in t.rounds]
    assert speakers.count("attacker") == 2 and speakers[0] == "referee"


def test_known_answer_needs_verified_citation(tmp_path):
    store, ix = make_env(tmp_path)
    client = LLMClient.fake(responder_factory(["known_answer", "known_answer"]))
    t = asyncio.run(run_trial(client, store, OBJ, "X.c1: P\nTherefore X.c2: C", ix, None, "trial-o1",
                              client.generator_specs()[0]))
    assert t.outcome == "known_answer" and "Y.c001" in t.cited_claim_ids
