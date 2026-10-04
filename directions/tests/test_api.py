import json

from fastapi.testclient import TestClient

from crux_lab.api import server


def test_sse_replays_cached_run(tmp_path, monkeypatch):
    run = {"run_id": "run-x", "events": [{"t": 1.0, "type": "run_start", "run_id": "run-x"},
                                          {"t": 1.1, "type": "run_end", "stop_reason": "test"}]}
    (tmp_path / "run-x.json").write_text(json.dumps(run))
    monkeypatch.setattr(server, "RUNS", tmp_path)
    c = TestClient(server.app)
    with c.stream("GET", "/api/run", params={"target": "x", "speed": 0}) as r:
        body = "".join(r.iter_text())
    assert r.status_code == 200
    assert '"type": "run_start"' in body and '"type": "run_end"' in body and "event: done" in body


def test_unknown_run_404(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "RUNS", tmp_path)
    assert TestClient(server.app).get("/api/run", params={"target": "nope"}).status_code == 404
