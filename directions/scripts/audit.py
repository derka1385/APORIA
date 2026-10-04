"""Grounding audit over every run, trial and brief. Writes docs/AUDIT.md (numbers come from the files).

Checks: (1) every target-paper claim quote is found in its source text; (2) every cited claim id in every
trial exists in the store; (3) every Referee deciding quote is found in its transcript (or objection, for a
pre-screen); (4) no objection cites anything; (5) every brief's literature entries resolve to a corpus or
live-OpenAlex record and every quote in them is found in that record's text; (6) challenged premises in
briefs match the stored claim text.
"""
from __future__ import annotations

import json
import re

_COMMON = set("""A An The This That These Those It If In On For To Of And Or But Does Do Can Could Would Should May Might
Must Is Are Was Were Be What Which Who How Why When Where Whether Defender Objector Referee God God's Christian Christians
Scripture Biblical Bible Molinist Molinism Reformed Divine Classical Paper Argument However Because Without While Within
Their They Such Even Then Thus Its Each Every Both Some Any No Not Only Whose Than Since Instead Although Though Also Most
More Less Hidden Premise Revised Open Questions Here First Second Third Many Much One Two""".split())

from crux_lab.config import BRIEFS, DEFAULT_TOPIC, ROOT, RUNS, TOPIC_SLUG
from crux_lab.corpus.build import load_corpus
from crux_lab.graph.extract import quote_found
from crux_lab.graph.schema import Claim
from crux_lab.graph.store import Store
from crux_lab.lab.debate import render_transcript
from crux_lab.graph.schema import Turn
from crux_lab.lab.generators import _CITATION

OUT = ROOT / "docs" / ("AUDIT.md" if TOPIC_SLUG == DEFAULT_TOPIC else f"AUDIT-{TOPIC_SLUG}.md")



def fold(s: str) -> str:
    """Accents folded, so 'Hajek' matches 'Hájek' and PDF text's detached 'H´ajek'; nothing else is loosened."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(c) and c not in "\u00b4`\u00a8\u02c6\u02dc")

def main() -> None:
    store = Store()
    corpus = {p["id"]: p for p in load_corpus()}
    rows, problems = [], []
    tot = {"quotes": 0, "quotes_ok": 0, "cites": 0, "cites_ok": 0, "deciding": 0, "deciding_ok": 0,
           "objections": 0, "objections_clean": 0, "lit": 0, "lit_ok": 0, "lit_quotes": 0, "lit_quotes_ok": 0}
    for f in sorted(RUNS.glob("run-*.json")):
        run = json.loads(f.read_text())
        text = (ROOT / run["target"]["text_path"]).read_text("utf-8")
        for c in run["claims"].values():
            if c["level"] != "fulltext":
                continue
            tot["quotes"] += 1
            ok = quote_found(c["quote"], text)
            tot["quotes_ok"] += ok
            if not ok:
                problems.append(f"{run['run_id']}: quote of {c['id']} not found in source")
        for o in run["objections"]:
            tot["objections"] += 1
            clean = not _CITATION.search(o["text"])
            tot["objections_clean"] += clean
            if not clean:
                problems.append(f"{run['run_id']}: objection {o['id']} contains a citation-like pattern")
        obj_text = {o["id"]: o["text"] for o in run["objections"]}
        for t in run["trials"]:
            turns = [Turn(**r) for r in t["rounds"]]
            for r in turns:
                for cid in r.cited_claim_ids:
                    tot["cites"] += 1
                    ok = store.get(Claim, cid) is not None
                    tot["cites_ok"] += ok
                    if not ok:
                        problems.append(f"{t['id']}: cited id {cid} not in store")
            if t.get("deciding_quote"):
                tot["deciding"] += 1
                pre_only = all(r.phase == "prescreen" for r in turns)
                src = obj_text.get(t["objection_id"], "") if pre_only else render_transcript(turns)
                ok = quote_found(t["deciding_quote"], src)
                tot["deciding_ok"] += ok
                if not ok:
                    problems.append(f"{t['id']}: deciding quote not found in {'objection' if pre_only else 'transcript'}")
        rows.append((run["run_id"], len(run["objections"]), len(run["trials"])))
    live = {}
    for lf in (ROOT / "data" / "raw" / "openalex_live").glob("*.json"):
        for w in json.loads(lf.read_text()):
            live[w["id"]] = w
    nbriefs = 0
    for f in sorted(BRIEFS.glob("brief-*.json")):
        b = json.loads(f.read_text())
        nbriefs += 1
        cp = b["challenged_premise"]
        c = store.get(Claim, cp["id"])
        if c and c.text != cp["text"]:
            problems.append(f"{b['id']}: challenged premise text differs from stored claim")
        for lit in b["closest_literature"]:
            tot["lit"] += 1
            pid = lit.get("paper_id")
            rec = corpus.get(pid) or live.get(pid)
            ok = rec is not None
            tot["lit_ok"] += ok
            if not ok:
                problems.append(f"{b['id']}: literature {lit['record_id']} has no record")
                continue
            if lit.get("quote"):
                tot["lit_quotes"] += 1
                rid = lit["record_id"]
                src = f"{rec.get('title', '')}. {rec.get('abstract', '')}"
                if not rid.startswith(("abs:", "live:")):
                    cl = store.get(Claim, rid)
                    src = cl.text if cl else src
                okq = quote_found(lit["quote"], src)
                tot["lit_quotes_ok"] += okq
                if not okq:
                    problems.append(f"{b['id']}: quote for {rid} not found in its record")
    # (7) proper names in brief prose must appear in the target paper or in the trial (case characters)
    runs = {json.loads(f.read_text())["run_id"]: json.loads(f.read_text()) for f in RUNS.glob("run-*.json")}
    tot["names"] = tot["names_ok"] = 0
    for f in sorted(BRIEFS.glob("brief-*.json")):
        b = json.loads(f.read_text())
        run = next((r for r in runs.values() if b["id"] in r["briefs"]), None)
        if not run:
            continue
        src = (ROOT / run["target"]["text_path"]).read_text("utf-8")
        trial = next((t for t in run["trials"] if t["objection_id"] == b["objection_id"]), {})
        src += " " + b["objection"] + " " + " ".join(r["content"] for r in trial.get("rounds", []))
        prose = " ".join([b["research_question"], b["paper_direction"], " ".join(b["open_questions"])] +
                         [r["response"] + " " + r["why_it_failed"] for r in b["strongest_responses"]])
        if b.get("revision"):     # revision prose may also draw on the referee's critique it answers
            r, q = b["revision"], b.get("assessment") or {}
            prose += " " + " ".join([r["research_question"], r["paper_direction"], r["reply_to_strongest_objection"]])
            src += " " + " ".join([q.get("strongest_objection", ""), q.get("what_it_needs", ""),
                                   " ".join((q.get("reasons") or {}).values())])
        names = set()
        for sent in re.split(r"(?<=[.?!:;])\s+|\n+", prose):        # skip each sentence's first word
            words = sent.split()
            names |= {m.group(1) for w in words[1:] if (m := re.match(r"\(?([A-Z][a-z]{3,}(?:[-'][A-Z][a-z]+)?)", w))}
        for name in names - _COMMON:
            tot["names"] += 1
            dash = str.maketrans({"\u2013": "-", "\u2014": "-"})
            src_n, name_n = fold(src.translate(dash)), fold(name.translate(dash))
            ok = name_n in src_n or name_n.removesuffix("'s") in src_n
            tot["names_ok"] += ok
            if not ok:
                problems.append(f"{b['id']}: name '{name}' not in the paper or the trial")
    pct = lambda a, b: f"{tot[a]}/{tot[b]}"  # noqa: E731
    L = ["# Grounding audit", "", "Generated by `scripts/audit.py` from data/runs, data/briefs and the claim store.", "",
         "| Check | Passed |", "| --- | --- |",
         f"| Target-paper claim quotes found verbatim in the source text (partial_ratio ≥ 90) | {pct('quotes_ok', 'quotes')} |",
         f"| Cited claim ids in trial turns that exist in the store | {pct('cites_ok', 'cites')} |",
         f"| Referee deciding quotes found in the transcript / objection | {pct('deciding_ok', 'deciding')} |",
         f"| Objections free of citations, dates and 'et al.' | {pct('objections_clean', 'objections')} |",
         f"| Brief literature entries that resolve to a corpus or live-OpenAlex record | {pct('lit_ok', 'lit')} |",
         f"| Quotes in brief literature found in the record they cite | {pct('lit_quotes_ok', 'lit_quotes')} |",
         f"| Capitalised names in brief prose found in the paper or the trial transcript | {pct('names_ok', 'names')} |",
         "", f"Runs: {len(rows)} · briefs: {nbriefs}", "", "## Problems found", ""]
    L += [f"- {p}" for p in problems] or ["None."]
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L[4:12]))
    print(f"{len(problems)} problems")


if __name__ == "__main__":
    main()
