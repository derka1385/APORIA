"""MLflow tracing for every LLM call. Databricks experiment if creds exist, else local mlruns/.

Tracing must never break the lab: any MLflow failure disables tracing and is logged once.
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Any

from crux_lab.config import ROOT, settings

log = logging.getLogger(__name__)
os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

_state: dict[str, Any] = {"ready": None, "target": None}
_lock = threading.Lock()


def _setup() -> bool:
    if _state["ready"] is not None:
        return _state["ready"]
    with _lock:
        if _state["ready"] is not None:
            return _state["ready"]
        if os.environ.get("CRUX_LAB_TRACING", "1") in ("0", "false"):
            _state["ready"] = False
            return False
        try:
            import mlflow

            if settings.has("databricks"):
                os.environ.setdefault("DATABRICKS_HOST", settings.databricks_host)
                os.environ.setdefault("DATABRICKS_TOKEN", settings.databricks_token)
                mlflow.set_tracking_uri("databricks")
                mlflow.set_experiment(os.environ.get("MLFLOW_EXPERIMENT_NAME", "/Shared/crux-lab"))
                _state["target"] = "databricks"
            else:
                (ROOT / "mlruns").mkdir(exist_ok=True)
                mlflow.set_tracking_uri(f"sqlite:///{ROOT / 'mlruns' / 'mlflow.db'}")
                mlflow.set_experiment("crux-lab")
                _state["target"] = "local"
            _state["ready"] = True
        except Exception as e:  # noqa: BLE001
            log.warning("MLflow tracing disabled: %s", e)
            _state["ready"] = False
    return _state["ready"]


def trace_call(*, role: str, provider: str, model: str, family: str, messages: list[dict],
               output: str, input_tokens: int, output_tokens: int, cost: float,
               latency_s: float, cached: bool) -> None:
    """Record one finished LLM call as an MLflow trace (one LLM span)."""
    if cached or not _setup():
        return
    try:
        import mlflow

        with _lock:
            with mlflow.start_span(name=f"llm:{role}", span_type="LLM") as span:
                span.set_inputs({"messages": messages})
                span.set_outputs({"text": output})
                span.set_attributes({
                    "role": role, "provider": provider, "model": model, "family": family,
                    "input_tokens": input_tokens, "output_tokens": output_tokens,
                    "cost_usd": round(cost, 6), "latency_s": round(latency_s, 3),
                })
    except Exception as e:  # noqa: BLE001
        log.warning("MLflow trace failed, disabling tracing: %s", e)
        _state["ready"] = False


def tracing_target() -> str | None:
    _setup()
    return _state["target"]
