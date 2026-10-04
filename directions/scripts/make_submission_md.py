"""Draft hackathon submission text -> docs/SUBMISSION.md (numbers read from web/public/data)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "web" / "public" / "data"


def load(name):
    return json.loads((D / name).read_text())


def assessor_line(briefs: list[dict]) -> str:
    graded = [b for b in briefs if b.get("assessment")]
    if not graded:
        return "No Assessor grades exported yet."
    tally: dict[str, int] = {}
    for b in graded:
        tally[b["assessment"]["grade"]] = tally.get(b["assessment"]["grade"], 0) + 1
    return ("An Assessor agent (a different model family from the brief writer) reads every research direction like a "
            "journal referee and grades coherence, robustness, significance and specificity; the grade is computed in "
            "code. Result: " + ", ".join(f"{v} {k}" for k, v in sorted(tally.items(), key=lambda kv: -kv[1]))
            + f" of {len(graded)}. The lab shows each direction's strongest objection and what a paper would need, "
            "rather than overselling its leads." + revision_sentence(graded))


def revision_sentence(graded: list[dict]) -> str:
    rev = [b for b in graded if (b.get("revision") or {}).get("assessment")]
    if not rev:
        return ""
    better = [b for b in rev if b["revision"]["assessment"]["grade"] != b["assessment"]["grade"]
              and b["revision"]["assessment"]["overall"] > b["assessment"]["overall"]]
    return (f" A revision round then rewrote each direction to answer its strongest objection and re-graded it in a "
            f"fresh read: {len(better)} of {len(rev)} moved up a grade (to "
            + ", ".join(sorted({b['revision']['assessment']['grade'] for b in better})) + ") and the rest stayed "
            "not yet defensible, each with the next objection it must meet.") if better else (
            f" A revision round rewrote each direction to answer its strongest objection; none moved up a grade.")


def replication() -> str:
    """E1 on the other explored topics, if it was run there."""
    out = []
    for p in sorted((D / "topics").glob("*/results.json")):
        e1 = (json.loads(p.read_text()).get("e1") or {})
        if not e1.get("methods"):
            continue
        best = max(e1["methods"], key=lambda m: m.get("recall_at_5", 0))
        kw = next((m for m in e1["methods"] if m["name"].startswith("BM25")), {})
        about = json.loads((p.parent / "about.json").read_text())
        out.append(f" E1 replicated on {about.get('topic', {}).get('name', p.parent.name)} (n={e1['n']}): "
                   f"{best['recall_at_5']:.0%} ({best['name']}) vs {kw.get('recall_at_5', 0):.0%} for keyword search.")
    return "".join(out)


def diversity_line(about: dict) -> str:
    try:
        topics = [t for t in load("topics.json")["topics"] if t.get("families")]
    except (OSError, KeyError):
        topics = []
    if len(topics) < 2:
        return str(about.get("diversity"))
    return "; ".join(f"{t['name']} ran on {len(t['families'])} model families" for t in topics)


def topics_lines() -> list[str]:
    """One line per configured topic, from topics.json: what was run, on which model families."""
    try:
        topics = load("topics.json")["topics"]
    except (OSError, KeyError):
        return []
    out = ["## Topics",
           "The lab is topic-configurable (`config/topics/<slug>.yaml`); the site switches between topics on `/topics`."]
    for x in topics:
        if x.get("status") == "ready" and x.get("counts"):
            k = x["counts"]
            fam = x.get("families") or []
            out.append(f"- **{x['name']}**: {k['papers']} papers, {k['objections']} objections, {k['trials']} trials, "
                       f"{k['briefs']} research directions" + (f"; {len(fam)} model families ({', '.join(fam)})" if fam else ""))
        else:
            out.append(f"- **{x['name']}**: configured, not run (the site shows the commands to run it).")
    return out + [""]


def main() -> None:
    idx, briefs, res, about = load("index.json"), load("briefs.json"), load("results.json"), load("about.json")
    e1, e2, e3 = res.get("e1") or {}, res.get("e2") or {}, res.get("e3") or {}
    best = max(e1.get("methods", [{}]), key=lambda m: m.get("recall_at_5", 0)) if e1 else {}
    bm25 = next((m for m in e1.get("methods", []) if m["name"].startswith("BM25")), {})
    c = about.get("corpus", {})
    surv = sum(r["outcomes"].get("revision_required", 0) + r["outcomes"].get("standing", 0) for r in idx["runs"])
    top = briefs[0] if briefs else {}
    e3rows = "; ".join(f"{x['name']}: {x['distinct_premises']} distinct premises/argument, spread {x['mean_pairwise_distance']}"
                       + (f", {x['share_surviving']:.0%} survive" if x.get("share_surviving") is not None else "")
                       for x in e3.get("conditions", []))
    L = [
        "# Submission draft — Crux Lab", "",
        "Generated by `scripts/make_submission_md.py`; numbers come from `web/public/data`. Edit freely before submitting.", "",
        "**Challenge:** 3 — Agentic Scientific Discovery (Databricks)", "",
        "## One-liner",
        "Crux Lab is an autonomous research lab for philosophy: AI agents reconstruct the argument of a new paper, "
        "attack single premises, defend them, check the literature, and hand a philosopher the open questions worth writing about.", "",
        "## Short description (≈100 words)",
        f"In philosophy the debate is the experiment. Crux Lab runs it: it reads recent papers (OpenAlex, {c.get('fresh')} published "
        f"since 2026-08-01), extracts arguments with verbatim quotes, formalizes them (a truth table finds the hidden premise), "
        f"and lets constrained agents attack one premise at a time. Two defenders from different model families answer with cited "
        f"corpus records; a Referee labels the dialectical outcome; a plain-code Director picks the next experiment. "
        f"Across {len(idx['runs'])} papers it ran {idx['trials']} trials; {surv} objections forced a premise revision or stood. "
        f"Every survivor becomes a research brief with a novelty score, the nearest prior art, and 'Further human review required.'", "",
        "## What is new",
        "- **The loop is an experiment loop, not a chat:** hypothesis (objection) → test (adversarial trial against two defenders) → "
        "measurement (outcome label + survival S) → prior-art check (novelty N) → Director chooses the next test by S·N·(0.5+0.5C)+0.1E; "
        "a forced revision becomes a new premise that is attacked in turn.",
        "- **Grounding enforced in code:** quotes verified against source text, citations are corpus ids verified by code, "
        "generators cannot see literature, validity is decided by a truth table, novelty is never claimed.",
        f"- **Measured:** prior-art recall@5 {best.get('recall_at_5', 0):.0%} for the lab's pipeline vs {bm25.get('recall_at_5', 0):.0%} "
        f"for keyword search (n={e1.get('n')}); the Referee caught {e2.get('misreading', {}).get('caught')}/"
        f"{e2.get('misreading', {}).get('n')} deliberate misreadings; a defender cited the published reply in "
        f"{e2.get('known_answer', {}).get('gold_reply_cited_by_a_defender')}/{e2.get('known_answer', {}).get('n')} known-answer cases "
        f"(the Referee still labelled only {e2.get('known_answer', {}).get('labelled_known_answer')}/{e2.get('known_answer', {}).get('n')} as known_answer); "
        f"diversity ablation — {e3rows}." + replication(), "",
        "## Quality control",
        assessor_line(briefs), "",
        "## Example output",
        f"Top research direction (highest lead score = survival × novelty × Assessor quality): "
        f"*{top.get('research_question', '')}* — {top.get('outcome', '')}, novelty {top.get('novelty', 0):.2f}, "
        f"{top.get('records_searched', 0)} records searched"
        + (f", lead score {top['score']:.3f}" if top.get("score") is not None else "") + ".", "",
        *topics_lines(),
        "## Databricks",
        "Model Serving / Foundation Model APIs are first in the provider chain; MLflow traces every LLM call "
        f"({about.get('tracing', {}).get('traces')} traced in this build, locally because no workspace token was available); "
        "a claims Delta table + AI Search (Vector Search) Delta Sync index and a Databricks App config are wired (`make databricks`, `app.yaml`).", "",
        "## Honest limits",
        f"Model diversity: {diversity_line(about)}; PhilArchive's OAI API was unavailable; evals are small and have no human labels; "
        "outcome labels are model judgements about the state of a debate, never verdicts on truth.", "",
        "## Links to fill in",
        "- Live demo: https://univerdread.github.io/crux-lab/",
        "- Video: <record from docs/DEMO.md; docs/demo.webm is a silent 76 s walkthrough, both topics>",
        "- Repo: https://github.com/univerdread/crux-lab (public)", "",
    ]
    (ROOT / "docs" / "SUBMISSION.md").write_text("\n".join(L))
    print("wrote docs/SUBMISSION.md")


if __name__ == "__main__":
    main()
