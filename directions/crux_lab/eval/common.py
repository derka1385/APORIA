"""Shared eval helpers: results files always carry n, settings, model ids, timestamp and limits."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from crux_lab.config import RESULTS
from crux_lab.llm.client import LLMClient

FIXTURES = Path(__file__).parent / "fixtures"


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def model_ids(client: LLMClient, roles: list[str]) -> dict[str, str]:
    return {r: client.spec_for(r).label for r in roles}


def write(name: str, data: dict) -> Path:
    RESULTS.mkdir(parents=True, exist_ok=True)
    p = RESULTS / f"{name}.json"
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return p


def canonical_argument() -> dict:
    """The topic's E2 calibration argument (config/topics/<slug>.yaml: e2_fixture)."""
    from crux_lab.config import TOPIC

    name = TOPIC.get("e2_fixture")
    if not name:
        raise LookupError(f"topic {TOPIC.get('slug')!r} has no e2_fixture: E2 needs a canonical argument; skipped")
    return json.loads((FIXTURES / name).read_text())


def canonical_text(fx: dict) -> str:
    lines = [f"{k}: {v}" for k, v in fx["premises"].items()]
    (cid, ctext), = fx["conclusion"].items()
    return "\n".join(lines + [f"Therefore {cid}: {ctext}"])
