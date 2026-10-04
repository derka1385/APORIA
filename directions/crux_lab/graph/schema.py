"""Pydantic models for every stored object (CLAUDE.md "Data model")."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ClaimKind = Literal["premise", "conclusion", "assumption", "objection", "reply", "open_question"]
Relation = Literal["supports", "attacks", "replies_to", "same_move", "presupposes"]
Outcome = Literal["misreading", "known_answer", "rebutted", "revision_required", "standing"]
SURVIVAL: dict[str, float] = {"misreading": 0.0, "known_answer": 0.1, "rebutted": 0.3,
                              "revision_required": 0.8, "standing": 1.0}
# Most favourable to the original argument first (lowest survival).
OUTCOME_ORDER: list[str] = ["misreading", "known_answer", "rebutted", "revision_required", "standing"]


class Paper(BaseModel):
    id: str
    source: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    abstract: str = ""
    url: str = ""
    pdf_path: str | None = None
    deposited_at: str | None = None


class Claim(BaseModel):
    id: str
    paper_id: str
    kind: ClaimKind
    text: str
    quote: str = ""
    embedding: list[float] | None = None
    level: Literal["fulltext", "abstract", "generated"] = "fulltext"


class Argument(BaseModel):
    id: str
    paper_id: str
    title: str = ""
    premise_ids: list[str]
    conclusion_id: str
    skeleton: str = ""
    atoms: dict[str, str] = Field(default_factory=dict)
    valid: bool | None = None
    missing_premise: str | None = None
    missing_premise_id: str | None = None


class Edge(BaseModel):
    src: str
    dst: str
    relation: Relation


class Objection(BaseModel):
    id: str
    argument_id: str
    target_premise_id: str
    kind: str
    text: str
    agent: str
    model: str
    family: str
    depth: int = 0
    tradition: str | None = None
    premise_fails_because: str = ""
    profile: str | None = None            # APORIA cognitive profile that generated it (crux_lab/lab/cognition.py)
    delta: float | None = None            # APORIA's Δ for that profile


class Turn(BaseModel):
    exchange: int
    speaker: str             # "defender_a" | "defender_b" | "attacker" | "referee"
    phase: str               # "reply" | "rejoinder" | "close" | "prescreen" | "label"
    model: str
    family: str
    content: str
    cited_claim_ids: list[str] = Field(default_factory=list)
    struck_claim_ids: list[str] = Field(default_factory=list)
    concedes: bool = False
    revised_premise: str | None = None


class Trial(BaseModel):
    id: str
    objection_id: str
    rounds: list[Turn] = Field(default_factory=list)
    outcome: Outcome | None = None
    rationale: str = ""
    deciding_quote: str = ""
    cited_claim_ids: list[str] = Field(default_factory=list)
    revised_premise: str | None = None
    per_defender: dict[str, dict] = Field(default_factory=dict)
    status: Literal["ok", "failed"] = "ok"
    error: str | None = None
    missing_labels: list[str] = Field(default_factory=list)   # defenders the Referee could not label


DEFENDERS = ("defender_a", "defender_b")


def trial_complete(t: dict) -> bool:
    """A trial that counts: status ok, and either a pre-screen misreading exit or a Referee label for both
    defenders. Checked on stored records too, so an older partial trial saved as 'ok' never counts."""
    if t.get("status", "ok") != "ok" or not t.get("outcome"):
        return False
    per = t.get("per_defender") or {}
    if not per:
        return t["outcome"] == "misreading"      # the pre-screen exit runs no defenders
    return all(per.get(d, {}).get("outcome") for d in DEFENDERS)


class NearestMatch(BaseModel):
    record_id: str
    paper_id: str
    verdict: Literal["same_move", "related", "different"]
    similarity: float
    quote: str = ""
    title: str = ""


class Brief(BaseModel):
    id: str
    objection_id: str
    research_question: str
    argument: dict
    challenged_premise: dict
    objection: str
    strongest_responses: list[dict]
    closest_literature: list[dict]
    novelty: float | None                 # None only for a diagnostic brief whose novelty was not assessed
    records_searched: int
    nearest: list[NearestMatch]
    open_questions: list[str]
    paper_direction: str
    outcome: str = ""
    assessment: dict | None = None        # the Assessor's academic-quality grade (crux_lab/lab/assess.py)
    revision: dict | None = None          # revision round: rewritten direction + its fresh re-assessment
    disclaimer: str = "Further human review required."
