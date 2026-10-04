"""Disk cache for LLM calls, keyed on sha256(provider, model, messages, params)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from crux_lab.config import LLM_CACHE


def cache_key(provider: str, model: str, messages: list[dict], params: dict[str, Any]) -> str:
    blob = json.dumps(
        {"provider": provider, "model": model, "messages": messages, "params": params},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class DiskCache:
    def __init__(self, root: Path = LLM_CACHE, enabled: bool = True):
        self.root = Path(root)
        self.enabled = enabled
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}.json"

    def get(self, key: str) -> dict | None:
        if not self.enabled:
            return None
        p = self._path(key)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def put(self, key: str, value: dict) -> None:
        if not self.enabled:
            return
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(value, ensure_ascii=False), "utf-8")
        tmp.replace(p)
