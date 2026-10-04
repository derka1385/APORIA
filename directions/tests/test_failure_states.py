"""Failure states are explicit (bug report 2026-10-04): an unavailable novelty check is 'not assessed', never a
maximal score; a trial without a Referee label for both defenders is failed, never a result."""
import asyncio
import json

import pytest

from crux_lab.export import brief_eligibility, normalize_run, rank_directions
from crux_lab.graph.index import Embedder, HybridIndex
from crux_lab.graph.schema import Brief, trial_complete
from crux_lab.lab import director, novelty
from crux_lab.lab.brief import to_markdown
from crux_lab.lab.gauntlet import run_trial
from crux_lab.llm.client import LLMClient
from tests.test_gauntlet import OBJ, make_env
from tests.test_novelty import make_ix, numbers, responder

ARG = "X.c1: P\nTherefore X.c2: C"


def check(client, claims, abstracts, **kw):
    return asyncio.run(novelty.check(client, "o1", "God would make belief available to all", "arg", "X.c1",
                                     "premise", claims, abstracts, **{"use_live": False, **kw}))


def all_different(u):
    return [{"n": n, "verdict": "different", "similarity": 0.2, "quote": ""} for n in numbers(u)]


class EmptyIx:
    def __len__(self):
        return 0

    def search(self, q, k=20):
        return []


class BrokenIx(EmptyIx):
    def search(self, q, k=20):
        raise RuntimeError("index file unreadable")


# ---- novelty -------------------------------------------------------------------------------------------

def test_empty_indexes_are_not_assessed():
    r = check(LLMClient.fake(responder(all_different)), EmptyIx(), EmptyIx())
    assert r.novelty is None and r.status == "no_candidates" and r.reranked == 0
    assert "No eligible literature candidates" in r.reason


def test_all_candidates_excluded_as_the_target_paper_are_not_assessed():
    claims = HybridIndex(["P.a1", "P.a2"], ["God would make belief available.", "Belief is available to all."],
                         [{"paper_id": "oa:P"}, {"paper_id": "oa:P"}], embedder=Embedder("lsa"))
    abstracts = HybridIndex(["oa:P"], ["Paper P. God would make belief available to all."], [{"title": "P"}],
                            embedder=Embedder("lsa"))
    r = check(LLMClient.fake(responder(all_different)), claims, abstracts, exclude_paper="oa:P")
    assert r.novelty is None and r.status == "no_candidates"
    assert r.records_searched == 3      # coverage is still reported


def test_reranker_failure_after_retries_is_not_assessed():
    claims, abstracts = make_ix()
    r = check(LLMClient.fake(responder(lambda u: "not a list")), claims, abstracts)
    assert r.novelty is None and r.status == "rerank_failed" and r.reranked > 0
    d = r.to_dict()
    assert d["novelty"] is None and json.loads(json.dumps(d))["status"] == "rerank_failed"


def test_retrieval_failure_is_not_assessed():
    r = check(LLMClient.fake(responder(all_different)), BrokenIx(), BrokenIx())
    assert r.novelty is None and r.status == "retrieval_failed" and "index file unreadable" in r.reason


def test_live_openalex_unavailable_keeps_a_local_assessment(monkeypatch):
    monkeypatch.setattr(novelty, "live_openalex", lambda q, n=10: ([], "unavailable (timeout)"))
    claims, abstracts = make_ix()
    r = check(LLMClient.fake(responder(all_different)), claims, abstracts, use_live=True)
    assert r.status == "assessed" and r.novelty == pytest.approx(0.8)
    assert r.live_openalex.startswith("unavailable")


def test_all_candidates_judged_different_is_a_valid_score():
    claims, abstracts = make_ix()
    r = check(LLMClient.fake(responder(all_different)), claims, abstracts)
    assert r.status == "assessed" and r.novelty == pytest.approx(0.8) and r.matches


def test_unassessed_objection_gets_no_director_default():
    from crux_lab.graph.schema import Objection
    objs = [Objection(id=i, argument_id="a", target_premise_id="X.c1", kind="k", text="t", agent="ag",
                      model="m", family="f") for i in ("ok", "na", "new")]
    rows = director.rank(objs, {"ok": 0.6, "na": None}, {}, set())
    ids = [r.objection_id for r in rows]
    assert "na" not in ids                       # not assessed: not eligible
    assert ids == ["ok", "new"]                  # unchecked keeps the prior 0.5, below the assessed 0.6


def test_ranking_drops_directions_without_assessed_novelty():
    out = rank_directions([{"id": "a", "run_id": "r", "survival": 0.8, "novelty": None},
                           {"id": "b", "run_id": "r", "survival": 0.8, "novelty": 0.4}])
    assert [b["id"] for b in out] == ["b"] and out[0]["score"] > 0


def test_brief_markdown_accepts_unassessed_novelty():
    b = Brief(id="brief-o1", objection_id="o1", research_question="Q?",
              argument={"title": "t", "paper_title": "p", "paper_id": "oa:P", "premises": [],
                        "conclusion": {"id": "X.c2", "text": "C"}},
              challenged_premise={"id": "X.c1", "text": "P"}, objection="O", strongest_responses=[],
              closest_literature=[], novelty=None, records_searched=10, nearest=[], open_questions=[],
              paper_direction="A paper here would argue")
    assert "not assessed" in to_markdown(b)


@pytest.mark.parametrize("record,status", [
    ({"novelty": 1.0, "reranked": 0, "matches": []}, "no_candidates"),
    ({"novelty": 1.0, "reranked": 12, "matches": []}, "rerank_failed"),
    ({"novelty": 0.42, "reranked": 12, "matches": [{"similarity": 0.58}]}, "assessed"),
])
def test_legacy_novelty_records_are_screened(record, status):
    n = novelty.normalize(record)
    assert n["status"] == status
    assert novelty.is_assessed(n) == (status == "assessed")
    if status != "assessed":
        assert n["novelty"] is None and n["legacy_novelty"] == 1.0


# ---- trials -------------------------------------------------------------------------------------------

def label_responder(valid_calls: set[int], misreading: bool = False):
    """Referee label calls are numbered 1, 2, ...; only the listed ones return valid JSON. Defender A is
    labelled first (up to 3 attempts), then Defender B."""
    calls = {"label": 0}

    def r(system, messages, model):
        if "Pre-screen" in system:
            return json.dumps({"misreading": misreading, "explanation": "e",
                               "deciding_quote": "Mara leaves the door open every night"})
        if "label the dialectical outcome" in system:
            calls["label"] += 1
            if calls["label"] not in valid_calls:
                return "no json here"
            return json.dumps({"outcome": "standing", "deciding_quote": "Openness need not produce belief",
                               "rationale": "r", "revised_premise": None})
        if "defend the argument" in system:
            return json.dumps({"misreading_check": "no", "reply": "Openness need not produce belief [Y.c001].",
                               "cited_claim_ids": ["Y.c001"], "concedes": False, "revised_premise": None})
        return "Your reply misses the case."
    return r


def trial(tmp_path, valid_calls, misreading=False):
    store, ix = make_env(tmp_path)
    client = LLMClient.fake(label_responder(valid_calls, misreading))
    events = []

    async def on(ev):
        events.append(ev)
    t = asyncio.run(run_trial(client, store, OBJ, ARG, ix, None, "trial-o1", client.generator_specs()[0],
                              on_event=on))
    return t, events[-1]


def test_both_labels_valid_keeps_the_normal_result(tmp_path):
    t, end = trial(tmp_path, {1, 2})
    assert t.status == "ok" and t.outcome == "standing" and set(t.per_defender) == {"defender_a", "defender_b"}
    assert trial_complete(t.model_dump()) and end["status"] == "ok"


@pytest.mark.parametrize("valid,missing,kept", [({1}, ["defender_b"], "defender_a"),
                                                 ({4}, ["defender_a"], "defender_b")])
def test_one_missing_label_fails_the_trial_and_keeps_the_evidence(tmp_path, valid, missing, kept):
    t, end = trial(tmp_path, valid)
    assert t.status == "failed" and t.outcome is None and t.revised_premise is None
    assert t.missing_labels == missing and f"missing {missing[0]}" in t.error
    assert list(t.per_defender) == [kept]                       # the label that exists is kept
    assert t.cited_claim_ids == ["Y.c001"]                       # verified citations kept
    assert sum(r.speaker in ("defender_a", "defender_b") for r in t.rounds) >= 4   # both discussions kept
    assert not trial_complete(t.model_dump())
    assert end["status"] == "failed" and end["outcome"] is None and end["missing_labels"] == missing


def test_no_labels_fails_the_trial(tmp_path):
    t, _ = trial(tmp_path, set())
    assert t.status == "failed" and t.outcome is None and t.missing_labels == ["defender_a", "defender_b"]


def test_prescreen_misreading_is_still_a_complete_early_exit(tmp_path):
    t, end = trial(tmp_path, set(), misreading=True)
    assert t.status == "ok" and t.outcome == "misreading" and not t.per_defender
    assert trial_complete(t.model_dump()) and end["outcome"] == "misreading"


def test_stale_partial_trial_in_a_stored_run_is_failed_and_not_ranked():
    stale = {"id": "trial-o1", "objection_id": "o1", "status": "ok", "outcome": "revision_required",
             "revised_premise": "New P", "rounds": [], "cited_claim_ids": ["Y.c001"],
             "per_defender": {"defender_a": {"outcome": "revision_required"}}}
    good = {"id": "trial-o2", "objection_id": "o2", "status": "ok", "outcome": "standing", "rounds": [],
            "per_defender": {"defender_a": {"outcome": "standing"}, "defender_b": {"outcome": "standing"}}}
    early = {"id": "trial-o3", "objection_id": "o3", "status": "ok", "outcome": "misreading", "rounds": [],
             "per_defender": {}}
    run = {"trials": [stale, good, early],
           "novelty": {"o1": {"novelty": 0.5, "reranked": 5, "matches": [{"similarity": 0.5}]},
                       "o2": {"novelty": 1.0, "reranked": 0, "matches": []},
                       "o3": {"novelty": 0.3, "reranked": 5, "matches": [{"similarity": 0.7}]}},
           "events": [{"type": "trial_end", "trial_id": "trial-o1", "objection_id": "o1",
                       "outcome": "revision_required", "status": "ok"},
                      {"type": "novelty", "objection_id": "o2", "novelty": 1.0}]}
    run = normalize_run(run)
    t1 = run["trials"][0]
    assert t1["status"] == "failed" and t1["outcome"] is None and t1["revised_premise"] is None
    assert t1["legacy_outcome"] == "revision_required" and t1["missing_labels"] == ["defender_b"]
    assert t1["cited_claim_ids"] == ["Y.c001"]                   # evidence untouched
    assert run["trials"][1]["status"] == "ok" and run["trials"][2]["status"] == "ok"
    assert run["events"][0]["status"] == "failed" and run["events"][0]["outcome"] is None
    assert run["events"][1]["novelty"] is None and run["events"][1]["status"] == "no_candidates"
    why = brief_eligibility([run])
    assert why["o1"] == "trial incomplete"           # partial trial: no survivor brief
    assert why["o2"] == "novelty not assessed"       # a 1.0 from the failure path: no lead score
    assert why["o3"] == ""


# ---- APORIA fusion: cognitive profiles as generators ---------------------------------------------------

def test_profiles_differ_by_policy_and_collapse_at_delta_zero():
    from crux_lab.lab import cognition
    moves = {p: cognition.move_of(cognition.policy(p, 1.0)) for p in cognition.PROFILES}
    assert moves == {"explorer": "imagine", "formalist": "formalize", "skeptic": "doubt",
                     "synthesizer": "memory", "minimalist": "introspect"}
    base = {p: cognition.move_of(cognition.policy(p, 0.0)) for p in cognition.PROFILES}
    assert len(set(base.values())) == 1          # Δ = 0: one shared policy, the noise floor


def test_learned_value_steers_the_directors_curiosity_term():
    from crux_lab.graph.schema import Objection
    from crux_lab.lab import cognition, director
    mk = lambda i, p: Objection(id=i, argument_id="a", target_premise_id="X.c1", kind="k", text="t",  # noqa: E731
                                agent=f"reasoner:{p}", model="m", family="f")
    done, a, b = mk("d", "skeptic"), mk("a", "skeptic"), mk("b", "explorer")
    learned = cognition.learned_values([done], {"d": 0.64})
    assert learned == {"skeptic": 0.64}
    tried = {director.explore_key(done)}
    rows = {r.objection_id: r for r in director.rank([done, a, b], {"a": 0.5, "b": 0.5}, {}, tried,
                                                     {"d": "standing"}, learned=learned)}
    assert rows["a"].E == 0.64 and rows["b"].E == 1   # a tried profile earns its learned value; untried = 1
