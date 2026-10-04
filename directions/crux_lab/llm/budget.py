"""Spend guard. API providers count estimated USD against LLM_BUDGET_USD.

Subscription CLI providers (codex_cli, claude_cli) cost no extra money, so they count calls
against CLI_CALL_BUDGET instead (their notional USD is still recorded for transparency).
Every charge is appended to cache/spend.jsonl so separate processes share one ledger.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from crux_lab.config import CACHE, settings

DEFAULT_IN_PER_M = 3.0
DEFAULT_OUT_PER_M = 15.0

# Known per-million prices (input, output). Unknown models use the defaults above.
PRICES: dict[str, tuple[float, float]] = {
    # evroc Think list prices (EUR per 1M tokens, 2026-10-04), converted to USD with a 10% margin
    "Kimi-K2.6": (1.4, 5.5), "GLM-5.2": (1.4, 5.5), "Mistral-Medium-3.5": (1.65, 6.6),
    "Qwen3.8-27B": (0.83, 3.3), "Qwen3.6-35B": (0.33, 1.32), "Llama-3.3-70B": (1.1, 1.1),
    "gpt-oss-120b": (0.22, 0.88), "gemma-4-26B": (0.14, 0.55),
}

CLI_PROVIDERS = {"codex_cli", "claude_cli", "fake"}


class BudgetExceeded(RuntimeError):
    pass


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    pin, pout = DEFAULT_IN_PER_M, DEFAULT_OUT_PER_M
    for pattern, (a, b) in PRICES.items():
        if pattern in model:
            pin, pout = a, b
            break
    return input_tokens / 1e6 * pin + output_tokens / 1e6 * pout


class Budget:
    def __init__(self, limit_usd: float | None = None, cli_limit: int | None = None,
                 ledger: Path | None | bool = None):
        """ledger: None = default cache/spend.jsonl, False = in-memory only (tests)."""
        self.limit_usd = settings.budget_usd if limit_usd is None else limit_usd
        self.cli_limit = settings.cli_call_budget if cli_limit is None else cli_limit
        self.ledger = None if ledger is False else (ledger or CACHE / "spend.jsonl")
        self._lock = threading.Lock()
        self.spent_usd = 0.0
        self.notional_usd = 0.0
        self.cli_calls = 0
        if self.ledger and self.ledger.exists():
            for line in self.ledger.read_text("utf-8").splitlines():
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                self._apply(row)

    def _apply(self, row: dict) -> None:
        if row.get("provider") in CLI_PROVIDERS:
            self.cli_calls += 1
            self.notional_usd += row.get("cost", 0.0)
        else:
            self.spent_usd += row.get("cost", 0.0)

    def check(self, provider: str) -> None:
        if provider in CLI_PROVIDERS:
            if self.cli_calls >= self.cli_limit:
                raise BudgetExceeded(f"CLI call budget reached ({self.cli_calls}/{self.cli_limit})")
        elif self.spent_usd >= self.limit_usd:
            raise BudgetExceeded(f"USD budget reached (${self.spent_usd:.2f}/${self.limit_usd:.2f})")

    def charge(self, provider: str, model: str, cost: float, role: str = "") -> None:
        row = {"t": time.time(), "provider": provider, "model": model, "cost": round(cost, 6), "role": role}
        with self._lock:
            self._apply(row)
            if self.ledger:
                self.ledger.parent.mkdir(parents=True, exist_ok=True)
                with self.ledger.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(row) + "\n")

    def summary(self) -> dict:
        return {
            "spent_usd": round(self.spent_usd, 4),
            "limit_usd": self.limit_usd,
            "cli_calls": self.cli_calls,
            "cli_limit": self.cli_limit,
            "notional_cli_usd": round(self.notional_usd, 4),
        }
