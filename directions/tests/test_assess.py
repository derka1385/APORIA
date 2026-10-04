import asyncio
import json

from crux_lab.graph.schema import Brief
from crux_lab.lab import assess
from crux_lab.lab.brief import to_markdown
from crux_lab.llm.client import LLMClient

BRIEF = Brief(id="brief-x", objection_id="o", research_question="Is P1 true?",
              argument={"id": "a", "title": "T", "paper_id": "oa:W1", "paper_title": "Paper",
                        "premises": [{"id": "W1.c001", "text": "P one", "quote": "q"}], "missing_premise": None,
                        "conclusion": {"id": "W1.c002", "text": "C"}, "skeleton": "A |- B", "valid": False},
              challenged_premise={"id": "W1.c001", "text": "P one"}, objection="A case.",
              strongest_responses=[{"defender": "Defender A", "response": "r", "why_it_failed": "w"}],
              closest_literature=[], novelty=0.5, records_searched=10, nearest=[], open_questions=["Q?"],
              paper_direction="A paper here would argue that...", outcome="revision_required")


def test_grade_rule_robustness_is_decisive():
    assert assess.grade({"coherence": 5, "robustness": 2, "significance": 5, "specificity": 5})[0] == "not yet defensible"
    assert assess.grade({"coherence": 4, "robustness": 4, "significance": 3, "specificity": 4}) == ("promising", 3.75)
    assert assess.grade({"coherence": 4, "robustness": 3, "significance": 4, "specificity": 4})[0] == "needs work"


def test_assess_brief_validates_and_grades():
    replies = iter([
        json.dumps({"coherence": 4, "robustness": 4, "significance": 4, "specificity": 4, "strongest_objection": "short",
                    "reply_available": True, "what_it_needs": "x", "reasons": {}, "summary": "s"}),
        json.dumps({"coherence": 4, "robustness": 5, "significance": 3, "specificity": 4,
                    "strongest_objection": "A referee would say the case equivocates between two senses of openness to relationship.",
                    "reply_available": True, "what_it_needs": "Fix the sense of openness.",
                    "reasons": {c: "because" for c in assess.CRITERIA}, "summary": "A real paper."}),
    ])
    client = LLMClient.fake(lambda s, m, model: next(replies))
    res = asyncio.run(assess.assess_brief(client, client.spec_for("referee"), BRIEF))
    assert res["grade"] == "promising" and res["overall"] == 4.0 and res["scores"]["robustness"] == 5
    md = to_markdown(BRIEF.model_copy(update={"assessment": res}))
    assert "Academic quality check" in md and "**promising**" in md


def test_revise_brief_requires_a_real_answer():
    revise_replies = iter([
        json.dumps({"research_question": "Q2", "paper_direction": "This paper argues...", "what_changed": "x",
                    "reply_to_strongest_objection": "short", "narrowed": False}),
        json.dumps({"research_question": "Q2", "paper_direction": "A paper here would argue that P1 holds only in a narrower form.",
                    "what_changed": "Narrowed to the modal claim.", "narrowed": True,
                    "reply_to_strongest_objection": " ".join(["The paper distinguishes possibility from actuality and"] * 4)}),
    ])
    client = LLMClient.fake(lambda s, m, model: next(revise_replies))
    brief = BRIEF.model_copy(update={"assessment": {"strongest_objection": "o", "reasons": {}, "what_it_needs": "n"}})
    rev = asyncio.run(assess.revise_brief(client, client.spec_for("referee"), brief))
    assert rev and rev["paper_direction"].startswith("A paper here would argue") and rev["narrowed"]
