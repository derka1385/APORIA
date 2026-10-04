import ast
import asyncio
import json
from pathlib import Path

from crux_lab.graph.schema import Argument, Claim
from crux_lab.lab import generators
from crux_lab.llm.client import LLMClient

FORBIDDEN = ("crux_lab.corpus", "crux_lab.graph.index", "crux_lab.graph.store", "crux_lab.lab.novelty")


def test_generators_never_import_literature():
    tree = ast.parse(Path(generators.__file__).read_text())
    mods = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)] + \
           [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    assert not [m for m in mods if m and m.startswith(FORBIDDEN)]


ARG = Argument(id="X.arg1", paper_id="oa:X", premise_ids=["X.c1", "X.c2"], conclusion_id="X.c3",
               missing_premise_id="X.arg1.mp")
OWN = {"X.c1": Claim(id="X.c1", paper_id="oa:X", kind="premise", text="If God exists, all are loved."),
       "X.c2": Claim(id="X.c2", paper_id="oa:X", kind="premise", text="Love implies openness."),
       "X.c3": Claim(id="X.c3", paper_id="oa:X", kind="conclusion", text="God is open to all."),
       "X.arg1.mp": Claim(id="X.arg1.mp", paper_id="oa:X", kind="assumption", text="Openness entails belief.")}
CASE = ("Mara, a hospice nurse, believes no one is beyond care. A patient refuses every visit, yet she leaves "
        "the door unlocked and food warm each night. Her openness is real, but the patient never comes to "
        "believe she is there, because he never looks. Openness here is a standing disposition, not a "
        "guarantee of uptake, and nothing in the case shows a failure of love on her part at all.")


def test_blind_rejects_unknown_premise_then_accepts():
    replies = iter([json.dumps({"target_premise_id": "X.c9", "objection": CASE, "premise_fails_because": "x"}),
                    json.dumps({"target_premise_id": "X.c2", "objection": CASE, "premise_fails_because": "x"})])
    seen = []

    def responder(system, messages, model):
        seen.append(system + messages[0]["content"])
        return next(replies)
    c = LLMClient.fake(responder)
    o = asyncio.run(generators.blind(c, ARG, OWN, c.generator_specs()[0]))
    assert o and o.target_premise_id == "X.c2" and o.family == "fakefam-a"
    # context holds only the argument, never literature
    assert "Openness entails belief" in seen[0] and "LITERATURE" not in seen[0]


def test_hidden_must_target_missing_premise():
    replies = iter([json.dumps({"target_premise_id": "X.c1", "objection": CASE, "premise_fails_because": "x"}),
                    json.dumps({"target_premise_id": "X.arg1.mp", "objection": CASE, "premise_fails_because": "x"})])
    c = LLMClient.fake(lambda s, m, model: next(replies))
    o = asyncio.run(generators.hidden(c, ARG, OWN, c.generator_specs()[0]))
    assert o.target_premise_id == "X.arg1.mp" and o.agent == "hidden_premise_attacker"


def test_citations_rejected():
    bad = CASE + " As Smith (2004) showed."
    replies = iter([json.dumps({"target_premise_id": "X.c1", "objection": bad, "premise_fails_because": "x"})] * 3)
    c = LLMClient.fake(lambda s, m, model: next(replies))
    assert asyncio.run(generators.blind(c, ARG, OWN, c.generator_specs()[0])) is None
