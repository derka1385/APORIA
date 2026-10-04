from crux_lab.graph.schema import Brief, NearestMatch
from crux_lab.lab.brief import to_markdown


def test_markdown_has_every_field_and_disclaimer():
    b = Brief(id="brief-x", objection_id="o", research_question="Is P1 true?",
              argument={"id": "a", "title": "T", "paper_id": "oa:W1", "paper_title": "Paper",
                        "premises": [{"id": "W1.c001", "text": "P one", "quote": "q"}],
                        "missing_premise": {"id": "a.mp", "text": "hidden"},
                        "conclusion": {"id": "W1.c002", "text": "C"}, "skeleton": "A |- B", "valid": False},
              challenged_premise={"id": "W1.c001", "text": "P one"}, objection="A case.",
              strongest_responses=[{"defender": "Defender A", "response": "r", "why_it_failed": "w"}],
              closest_literature=[{"record_id": "W2.a1", "title": "Prior", "authors": ["X"], "year": 2001,
                                   "url": "u", "verdict": "related", "similarity": 0.4, "quote": "said so"}],
              novelty=0.6, records_searched=100, nearest=[NearestMatch(record_id="W2.a1", paper_id="oa:W2",
                                                                        verdict="related", similarity=0.4)],
              open_questions=["Q?"], paper_direction="A paper here would argue that...", outcome="standing")
    md = to_markdown(b)
    for s in ("# Research brief: Is P1 true?", "**standing**", "novelty score:* 0.60", "records searched:* 100",
              "W1.c001", "unstated, found by the Formalizer", "Defender A", "`W2.a1`", "> said so", "- Q?",
              "A paper here would argue", "**Further human review required.**"):
        assert s in md, s
