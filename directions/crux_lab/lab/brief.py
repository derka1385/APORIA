"""Research brief: JSON + Markdown. References are rendered from corpus records, never model text."""
from __future__ import annotations

import logging

from pydantic import BaseModel, Field

from crux_lab.agents.roles import render
from crux_lab.config import BRIEFS
from crux_lab.graph.schema import Argument, Brief, Claim, NearestMatch, Objection, Trial
from crux_lab.lab.debate import render_transcript
from crux_lab.llm.client import LLMClient

log = logging.getLogger(__name__)


class Response(BaseModel):
    defender: str
    response: str
    why_it_failed: str


class BriefOut(BaseModel):
    research_question: str
    strongest_responses: list[Response] = Field(default_factory=list)
    open_questions: list[str]
    paper_direction: str


def record_ref(paper: dict | None, record_id: str) -> dict:
    if not paper:
        return {"record_id": record_id}
    return {"record_id": record_id, "paper_id": paper["id"], "title": paper.get("title", ""),
            "authors": paper.get("authors", [])[:4], "year": paper.get("year"), "url": paper.get("url", "")}


async def write_brief(client: LLMClient, arg: Argument, own: dict[str, Claim], objection: Objection,
                      trial: Trial, novelty: dict, paper: dict, papers: dict[str, dict],
                      revised: dict[str, str]) -> Brief | None:
    target_text = own[objection.target_premise_id].text if objection.target_premise_id in own \
        else revised.get(objection.target_premise_id, "")
    premises = "\n".join(f"{p}: {own[p].text}" for p in arg.premise_ids)
    if arg.missing_premise_id and arg.missing_premise_id in own:
        premises += f"\n{arg.missing_premise_id} (unstated): {own[arg.missing_premise_id].text}"
    argument_text = f"{premises}\nTherefore {arg.conclusion_id}: {own[arg.conclusion_id].text}"
    transcripts = render_transcript([t for t in trial.rounds if t.speaker != "referee"])
    nearest_txt = "\n".join(f"- [{m['verdict']}, {m['similarity']}] {m.get('title', '')}: {m.get('quote', '')}"
                            for m in novelty.get("nearest", [])) or "(none)"
    system, user = render("brief", paper_title=paper.get("title", ""), argument=argument_text,
                          target_id=objection.target_premise_id, target_text=target_text,
                          agent=objection.agent, family=objection.family, objection=objection.text,
                          outcome=trial.outcome or "failed", rationale=trial.rationale,
                          transcripts=transcripts[:12000], nearest=nearest_txt)
    out, _ = await client.json("brief", user, BriefOut, system, max_tokens=3000)
    if not out:     # one fallback writer outside the Assessor's family, then no brief rather than a placeholder
        out, _ = await client.json("brief", user, BriefOut, system, spec=client.spec_for("referee"), max_tokens=3000)
    if not out:
        log.warning("brief for %s not written: both writers failed validation", objection.id)
        return None
    nearest = [NearestMatch(**m) for m in novelty.get("nearest", [])]
    closest = []
    for m in nearest:
        ref = record_ref(papers.get(m.paper_id), m.record_id)
        if "title" not in ref:   # live OpenAlex record (cached in data/raw/openalex_live, exported to records)
            ref.update(paper_id=m.paper_id, title=m.title,
                       url=f"https://openalex.org/{m.paper_id.split(':', 1)[-1]}")
        closest.append({**ref, "verdict": m.verdict, "similarity": m.similarity, "quote": m.quote})
    own_short = arg.paper_id.split(":", 1)[-1] + "."
    for cid in trial.cited_claim_ids:
        if cid.startswith(own_short):
            continue            # the argument's own claims are not "literature"
        pid = cid.rsplit(".", 1)[0]
        p = next((pp for k, pp in papers.items() if k.endswith(":" + pid) or k == pid), None)
        if p and not any(c.get("record_id") == cid for c in closest):
            closest.append({**record_ref(p, cid), "verdict": "cited_in_trial"})
    return Brief(
        id=f"brief-{objection.id}", objection_id=objection.id, research_question=out.research_question,
        argument={"id": arg.id, "title": arg.title, "paper_id": arg.paper_id, "paper_title": paper.get("title", ""),
                  "premises": [{"id": p, "text": own[p].text, "quote": own[p].quote} for p in arg.premise_ids],
                  "missing_premise": ({"id": arg.missing_premise_id, "text": own[arg.missing_premise_id].text}
                                      if arg.missing_premise_id in own else None),
                  "conclusion": {"id": arg.conclusion_id, "text": own[arg.conclusion_id].text},
                  "skeleton": arg.skeleton, "valid": arg.valid},
        challenged_premise={"id": objection.target_premise_id, "text": target_text},
        objection=objection.text,
        strongest_responses=[r.model_dump() for r in out.strongest_responses],
        closest_literature=closest,
        novelty=round(novelty["novelty"], 3) if novelty.get("novelty") is not None else None,
        records_searched=novelty.get("records_searched", 0), nearest=nearest,
        open_questions=out.open_questions, paper_direction=out.paper_direction, outcome=trial.outcome or "")


def to_markdown(b: Brief, objection: Objection | None = None) -> str:
    a = b.argument
    L = [f"# Research brief: {b.research_question}", "",
         f"*Outcome in the gauntlet:* **{b.outcome}** · *novelty score:* "
         f"{f'{b.novelty:.2f}' if b.novelty is not None else 'not assessed'} · "
         f"*records searched:* {b.records_searched}", "",
         f"## Argument — {a.get('title', '')}", f"From: {a.get('paper_title', '')} (`{a.get('paper_id', '')}`)", ""]
    for p in a["premises"]:
        L.append(f"- **{p['id']}**: {p['text']}")
    if a.get("missing_premise"):
        L.append(f"- **{a['missing_premise']['id']}** *(unstated, found by the Formalizer)*: {a['missing_premise']['text']}")
    L += [f"- **Therefore {a['conclusion']['id']}**: {a['conclusion']['text']}", "",
          f"Skeleton: `{a.get('skeleton', '')}` ({'valid' if a.get('valid') else 'invalid as stated'})", "",
          "## Challenged premise", f"**{b.challenged_premise['id']}**: {b.challenged_premise['text']}", "",
          "## Objection"]
    if objection:
        L.append(f"*{objection.agent} · {objection.family}:{objection.model}*")
    L += ["", b.objection, "", "## Strongest responses and why they failed"]
    for r in b.strongest_responses:
        L.append(f"- **{r['defender']}**: {r['response']} — *{r['why_it_failed']}*")
    L += ["", "## Closest literature (from corpus records)"]
    for c in b.closest_literature:
        auth = ", ".join(c.get("authors", [])[:3])
        L.append(f"- `{c['record_id']}` — {c.get('title', '')} ({auth}{', ' + str(c['year']) if c.get('year') else ''}) "
                 f"[{c.get('verdict', '')}{', sim ' + str(c['similarity']) if 'similarity' in c else ''}] {c.get('url', '')}")
        if c.get("quote"):
            L.append(f"  > {c['quote']}")
    L += ["", "## Open questions"] + [f"- {q}" for q in b.open_questions]
    L += ["", "## Paper direction", b.paper_direction, ""]
    if b.assessment:
        s = b.assessment
        L += ["## Academic quality check (AI assessor, not peer review)",
              f"**{s['grade']}** · overall {s['overall']}/5 · " + " · ".join(f"{k} {v}/5" for k, v in s["scores"].items()),
              "", f"*{s['summary']}*", "",
              f"- Strongest objection to this direction: {s['strongest_objection']}",
              f"- A viable answer is {'available' if s['reply_available'] else 'not yet available'} in the brief or the debate.",
              f"- What the paper needs: {s['what_it_needs']}", f"- Assessor: {s['model']}", ""]
    if b.revision:
        r = b.revision
        L += ["## Revised after the quality check",
              f"*{r.get('what_changed', '')}*" + (" The thesis was narrowed." if r.get("narrowed") else ""), "",
              f"**Revised question:** {r['research_question']}", "", r["paper_direction"], "",
              f"**How the paper answers the main objection:** {r['reply_to_strongest_objection']}", ""]
        q = r.get("assessment")
        if q:
            L += [f"**Re-assessment** (fresh read, the assessor did not see its earlier critique): **{q['grade']}** · "
                  f"overall {q['overall']}/5 · " + " · ".join(f"{k} {v}/5" for k, v in q["scores"].items()),
                  "", f"*{q['summary']}*", "", f"- Strongest remaining objection: {q['strongest_objection']}",
                  f"- What it still needs: {q['what_it_needs']}", f"- Reviser: {r.get('model')}; assessor: {q['model']}", ""]
    L += [f"**{b.disclaimer}**", ""]
    return "\n".join(L)


def save(b: Brief, objection: Objection | None = None) -> None:
    BRIEFS.mkdir(parents=True, exist_ok=True)
    (BRIEFS / f"{b.id}.json").write_text(b.model_dump_json(indent=2))
    (BRIEFS / f"{b.id}.md").write_text(to_markdown(b, objection))
