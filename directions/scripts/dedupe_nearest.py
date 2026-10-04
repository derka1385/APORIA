"""Rebuild the derived 'nearest' fields of existing runs and briefs as the 3 nearest *distinct works*
(the novelty code does this for new runs). Uses only the stored match lists: no model calls, and novelty
scores are unchanged (they are computed over all matches)."""
from __future__ import annotations

import json

from crux_lab.config import BRIEFS, RUNS
from crux_lab.corpus.build import load_corpus
from crux_lab.corpus.dedup import distinct_nearest
from crux_lab.graph.schema import Brief, NearestMatch, Objection
from crux_lab.graph.store import Store
from crux_lab.lab.brief import record_ref, to_markdown


def main() -> None:
    papers = {p["id"]: p for p in load_corpus()}
    store = Store()
    nruns = nbriefs = changed = 0
    for f in sorted(RUNS.glob("run-*.json")):
        run = json.loads(f.read_text())
        for nv in run["novelty"].values():
            new = distinct_nearest(nv.get("matches", []))
            changed += new != nv["nearest"]
            nv["nearest"] = new
        f.write_text(json.dumps(run, indent=1, ensure_ascii=False))
        nruns += 1
        for bid in run["briefs"]:
            bf = BRIEFS / f"{bid}.json"
            b = json.loads(bf.read_text())
            nv = run["novelty"].get(b["objection_id"], {})
            nearest = [NearestMatch(**m) for m in nv.get("nearest", [])]
            refs = []
            for m in nearest:
                ref = record_ref(papers.get(m.paper_id), m.record_id)
                if "title" not in ref:
                    ref.update(paper_id=m.paper_id, title=m.title,
                               url=f"https://openalex.org/{m.paper_id.split(':', 1)[-1]}")
                refs.append({**ref, "verdict": m.verdict, "similarity": m.similarity, "quote": m.quote})
            cited = [c for c in b["closest_literature"] if c.get("verdict") == "cited_in_trial"]
            b["nearest"] = [m.model_dump() for m in nearest]
            b["closest_literature"] = refs + cited
            brief = Brief.model_validate(b)
            bf.write_text(brief.model_dump_json(indent=2))
            obj = next((Objection(**o) for o in run["objections"] if o["id"] == b["objection_id"]), None)
            bf.with_suffix(".md").write_text(to_markdown(brief, obj))
            store.put(brief)
            nbriefs += 1
    print(f"rebuilt nearest for {nruns} runs ({changed} novelty panels changed) and {nbriefs} briefs")


if __name__ == "__main__":
    main()
