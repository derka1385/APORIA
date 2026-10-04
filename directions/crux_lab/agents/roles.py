"""Prompt loading. Each prompt lives in prompts/<name>.md with {placeholders}.

Only the placeholders passed in are replaced, so literal JSON braces in prompts are safe.
"""
from __future__ import annotations

from functools import lru_cache

from crux_lab.config import PROMPTS


@lru_cache(maxsize=None)
def _load(name: str) -> str:
    text = (PROMPTS / f"{name}.md").read_text("utf-8")
    # Origin headers of adapted prompts are for humans, not for the model.
    return "\n".join(l for l in text.splitlines() if not l.startswith("# Adapted from Crux"))


def render(name: str, **kw) -> tuple[str, str]:
    """Return (system, user). A prompt file may split them with a line '---USER---'."""
    text = _load(name)
    for k, v in kw.items():
        text = text.replace("{" + k + "}", str(v))
    if "---USER---" in text:
        system, user = text.split("---USER---", 1)
        return system.strip(), user.strip()
    return "", text.strip()
