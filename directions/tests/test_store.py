from crux_lab.graph.schema import Argument, Brief, Claim, Edge, NearestMatch, Objection, Paper, Trial, Turn
from crux_lab.graph.store import Store


def test_round_trip_every_kind(tmp_path):
    s = Store(tmp_path / "t.sqlite")
    p = Paper(id="oa:W1", source="openalex", title="T", authors=["A"], year=2020, abstract="x")
    c = Claim(id="c1", paper_id="oa:W1", kind="premise", text="P", quote="q", embedding=[0.1, 0.2])
    a = Argument(id="a1", paper_id="oa:W1", premise_ids=["c1"], conclusion_id="c2", skeleton="A -> B",
                 atoms={"A": "x"}, valid=False, missing_premise="A")
    o = Objection(id="o1", argument_id="a1", target_premise_id="c1", kind="thought_experiment",
                  text="case", agent="blind", model="m", family="f")
    t = Trial(id="t1", objection_id="o1", outcome="rebutted",
              rounds=[Turn(exchange=1, speaker="defender_a", phase="reply", model="m", family="f",
                           content="hi", cited_claim_ids=["c1"])])
    b = Brief(id="b1", objection_id="o1", research_question="q", argument={}, challenged_premise={},
              objection="o", strongest_responses=[], closest_literature=[], novelty=0.5,
              records_searched=10, nearest=[NearestMatch(record_id="c1", paper_id="oa:W1",
                                                         verdict="related", similarity=0.4)],
              open_questions=[], paper_direction="A paper here would argue...")
    s.put_many([p, c, a, o, t, b, Edge(src="c1", dst="c2", relation="supports")])
    assert s.get(Paper, "oa:W1") == p
    assert s.get(Claim, "c1") == c
    assert s.get(Argument, "a1") == a
    assert s.get(Objection, "o1") == o
    assert s.get(Trial, "t1") == t
    assert s.get(Brief, "b1") == b
    assert s.all(Claim, parent="oa:W1") == [c]
    assert s.edges(src="c1")[0].relation == "supports"
    s.put(c.model_copy(update={"text": "P2"}))
    assert s.get(Claim, "c1").text == "P2" and s.count(Claim) == 1
