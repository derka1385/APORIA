"""`make eval`: E1, E2, E3 (each writes results/<name>.json)."""
from __future__ import annotations

import logging

from crux_lab.eval import e1_prior_art, e2_calibration, e3_diversity

log = logging.getLogger(__name__)


async def main(only: str = "") -> None:
    todo = [x.strip() for x in only.split(",") if x.strip()] or ["e1", "e2", "e3"]
    for name, mod in (("e1", e1_prior_art), ("e2", e2_calibration), ("e3", e3_diversity)):
        if name not in todo:
            continue
        try:
            r = await mod.run()
            log.info("%s done: n=%s", name, r.get("n", r.get("conditions")))
        except LookupError as e:          # e.g. a topic without an E2 fixture
            log.warning("%s skipped: %s", name, e)
        except Exception:  # noqa: BLE001 - a failed eval must not stop the others
            log.exception("%s failed", name)
