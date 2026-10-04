import asyncio
import json

from crux_lab.graph.index import Embedder, HybridIndex
from crux_lab.lab import novelty
from crux_lab.llm.client import LLMClient

TEXTS = ["A loving God would make belief available to every nonresistant person.",
         "Hidden providence can work through free choices without a visible pattern.",
         "Bananas are rich in potassium and grow in tropical climates."]


def make_ix():
    emb = Embedder("lsa")
    claims = HybridIndex(["P.a1", "Q.a1", "R.a1"], TEXTS,
                         [{"paper_id": f"oa:{x}", "title": f"Paper {x}"} for x in "PQR"], embedder=emb)
    abstracts = HybridIndex(["oa:P"], ["Paper P. " + TEXTS[0]], [{"title": "Paper P"}], embedder=emb)
    return claims, abstracts


def responder(judgments):
    def r(system, messages, model):
        u = messages[-1]["content"]
        if "Restate the objection" in system:
            return json.dumps({"paper_vocabulary": "loving God belief nonresistant", "plain_english": "God would make belief available",
                               "neighboring_tradition": "providence free choices"})
        if "Prior-Art Hunter" in system:
            return json.dumps({"judgments": judgments(u)})
        return "{}"
    return r


def numbers(u):
    import re
    return [int(x) for x in re.findall(r"^\[(\d+)\]", u, re.M)]


def test_novelty_uses_same_move_and_verified_quotes():
    claims, abstracts = make_ix()

    def judge(u):
        out = []
        for n in numbers(u):
            if "make belief available to every nonresistant person" in u.split(f"[{n}]")[1].split("\n[")[0]:
                out.append({"n": n, "verdict": "same_move", "similarity": 1.5 if False else 0.95,
                            "quote": "A loving God would make belief available to every nonresistant person."})
            else:
                out.append({"n": n, "verdict": "related", "similarity": 0.9, "quote": "not in the passage at all"})
        return out
    c = LLMClient.fake(responder(judge))
    r = asyncio.run(novelty.check(c, "o1", "God would make belief available to all", "arg", "X.c1", "premise",
                                  claims, abstracts, use_live=False))
    assert abs(r.novelty - 0.05) < 1e-6
    assert r.records_searched == len(claims) + len(abstracts)
    assert r.nearest[0].verdict == "same_move"
    # an unverifiable quote cannot keep a high 'related' similarity
    assert all(m.similarity <= 0.69 for m in r.matches if m.verdict == "related")


def test_no_hits_gives_novelty_from_best_different_passage():
    claims, abstracts = make_ix()
    c = LLMClient.fake(responder(lambda u: [{"n": n, "verdict": "different", "similarity": 0.2, "quote": ""}
                                            for n in numbers(u)]))
    r = asyncio.run(novelty.check(c, "o1", "something unrelated about potassium", "arg", "X.c1", "premise",
                                  claims, abstracts, use_live=False))
    assert abs(r.novelty - 0.8) < 1e-6


def test_target_paper_excluded():
    claims, abstracts = make_ix()
    c = LLMClient.fake(responder(lambda u: [{"n": n, "verdict": "different", "similarity": 0.1, "quote": ""}
                                            for n in numbers(u)]))
    r = asyncio.run(novelty.check(c, "o1", "loving God belief", "arg", "X.c1", "p", claims, abstracts,
                                  use_live=False, exclude_paper="oa:P"))
    assert all(m.paper_id != "oa:P" for m in r.matches)


def test_keywords():
    assert novelty.keywords("The loving God, would it hide? Yes, God would.") == "loving god hide yes"   # stopwords (would) dropped


def test_duplicate_record_of_target_is_excluded(monkeypatch):
    from crux_lab.corpus import dedup
    claims, abstracts = make_ix()
    # pretend oa:Q is another record of the target paper oa:P
    monkeypatch.setattr(dedup, "work_of", lambda pid: "oa:P" if pid in ("oa:P", "oa:Q") else pid)
    c = LLMClient.fake(responder(lambda u: [{"n": n, "verdict": "different", "similarity": 0.1, "quote": ""}
                                            for n in numbers(u)]))
    r = asyncio.run(novelty.check(c, "o1", "loving God belief providence", "arg", "X.c1", "p", claims, abstracts,
                                  use_live=False, exclude_paper="oa:P"))
    assert all(m.paper_id not in ("oa:P", "oa:Q") for m in r.matches)
