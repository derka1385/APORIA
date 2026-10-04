"""Schema test on exported JSON (runs only when an export exists)."""
import json

import pytest

from crux_lab.config import WEB_DATA

pytestmark = pytest.mark.skipif(not (WEB_DATA / "index.json").exists(), reason="no export yet")


def test_index_shape():
    idx = json.loads((WEB_DATA / "index.json").read_text())
    assert {"generated_at", "runs", "targets", "briefs", "trials", "objections", "headline"} <= set(idx)
    for r in idx["runs"]:
        assert {"run_id", "target_id", "title", "objections", "trials", "outcomes", "briefs"} <= set(r)
        assert (WEB_DATA / "runs" / f"{r['run_id']}.json").exists()
    for h in idx["headline"]:
        assert set(h) == {"label", "value", "source"}


def test_runs_and_briefs_shape():
    for f in (WEB_DATA / "runs").glob("run-*.json"):
        run = json.loads(f.read_text())
        assert {"argument", "claims", "objections", "trials", "director_steps", "events", "novelty"} <= set(run)
        claims = run["claims"]
        for pid in run["argument"]["premise_ids"]:
            assert pid in claims
        for t in run["trials"]:
            assert t["outcome"] in (None, "misreading", "known_answer", "rebutted", "revision_required", "standing")
    briefs = json.loads((WEB_DATA / "briefs.json").read_text())
    for b in briefs:
        full = json.loads((WEB_DATA / "briefs" / f"{b['id']}.json").read_text())
        assert full["disclaimer"] == "Further human review required."
        assert 0 <= full["novelty"] <= 1 and full["records_searched"] > 0
        assert len(full["nearest"]) <= 3


def test_records_cover_citations():
    records = json.loads((WEB_DATA / "records.json").read_text())
    for f in (WEB_DATA / "briefs").glob("brief-*.json"):
        b = json.loads(f.read_text())
        for c in b["closest_literature"]:
            if c.get("paper_id"):
                assert c["paper_id"] in records
