"""The one door every agent goes through: role -> model, cache, budget, tracing, JSON validation."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from typing import Callable, TypeVar

from pydantic import BaseModel, ValidationError

from crux_lab.config import LOGS, RESOLVED_MODELS, settings
from crux_lab.llm.budget import Budget, BudgetExceeded
from crux_lab.llm.cache import DiskCache, cache_key
from crux_lab.llm.providers import (Completion, FakeProvider, Provider, ProviderError,
                                    build_provider, extract_json)
from crux_lab.llm.tracing import trace_call

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

ROLE_TEMPERATURE = {
    "generator": 0.9, "naive_questioner": 0.9,
    "defender_a": 0.5, "defender_b": 0.5, "attacker": 0.9,
    "extractor": 0.2, "formalizer": 0.2, "referee": 0.2, "reranker": 0.2,
    "restater": 0.2, "gap_scout": 0.2, "brief": 0.2, "eval": 0.2, "assessor": 0.2, "reviser": 0.5,
}


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model: str
    family: str
    effort: str = "low"

    @property
    def label(self) -> str:
        return f"{self.family}:{self.model}"


class LLMClient:
    def __init__(self, resolved: dict | None = None, providers: dict[str, Provider] | None = None,
                 cache: DiskCache | None = None, budget: Budget | None = None):
        if resolved is None:
            if not RESOLVED_MODELS.exists():
                raise RuntimeError("config/resolved_models.json missing: run `make providers`")
            resolved = json.loads(RESOLVED_MODELS.read_text())
        self.resolved = resolved
        self.providers: dict[str, Provider] = providers or {}
        self.cache = cache or DiskCache()
        self.budget = budget or Budget()
        self.stats = {"calls": 0, "cache_hits": 0, "json_failures": 0, "errors": 0}

    # ---------------------------------------------------------------- construction helpers
    @classmethod
    def fake(cls, responder: Callable[[str, list[dict], str], str], tmp_cache=None,
             families: tuple[str, ...] = ("fakefam-a", "fakefam-b", "fakefam-c")) -> "LLMClient":
        prov = FakeProvider(responder)
        spec = lambda fam: {"provider": "fake", "model": f"fake-{fam}", "family": fam, "effort": "low"}  # noqa: E731
        roles = {r: spec(families[0]) for r in ("extractor", "formalizer", "reranker", "defender_a",
                                                 "restater", "gap_scout", "brief", "eval")}
        roles["defender_b"] = spec(families[1 % len(families)])
        roles["referee"] = spec(families[2 % len(families)])
        roles["naive_questioner"] = spec(families[0])
        roles["generators"] = [spec(f) for f in families]
        resolved = {"roles": roles, "families": list(families), "models": []}
        return cls(resolved, providers={"fake": prov},
                   cache=tmp_cache or DiskCache(enabled=False),
                   budget=Budget(limit_usd=1e9, cli_limit=10**9, ledger=False))

    def provider(self, name: str) -> Provider:
        if name not in self.providers:
            self.providers[name] = build_provider(name)
        return self.providers[name]

    def spec_for(self, role: str) -> ModelSpec:
        roles = self.resolved["roles"]
        key = role if role in roles else {"attacker": "generators", "restater": "reranker",
                                           "gap_scout": "extractor", "brief": "extractor",
                                           "eval": "reranker"}.get(role, "extractor")
        val = roles[key]
        if isinstance(val, list):
            val = val[0]
        return ModelSpec(**val)

    def generator_specs(self) -> list[ModelSpec]:
        return [ModelSpec(**g) for g in self.resolved["roles"]["generators"]]

    @property
    def families(self) -> list[str]:
        return list(self.resolved.get("families", []))

    # ---------------------------------------------------------------- calls
    async def chat(self, role: str, user: str, system: str = "", *, spec: ModelSpec | None = None,
                   history: list[dict] | None = None, max_tokens: int = 2000,
                   temperature: float | None = None, use_cache: bool = True) -> Completion:
        spec = spec or self.spec_for(role)
        temp = ROLE_TEMPERATURE.get(role.split(":")[0], 0.2) if temperature is None else temperature
        messages = list(history or []) + [{"role": "user", "content": user}]
        params = {"system": system, "temperature": temp, "max_tokens": max_tokens, "effort": spec.effort}
        key = cache_key(spec.provider, spec.model, messages, params)
        self.stats["calls"] += 1
        if use_cache and (hit := self.cache.get(key)):
            self.stats["cache_hits"] += 1
            return Completion(hit["text"], hit["input_tokens"], hit["output_tokens"], 0.0,
                              spec.provider, spec.model, 0.0, cached=True)
        self.budget.check(spec.provider)
        if spec.provider in settings.disabled:
            raise ProviderError(f"provider {spec.provider} is disabled (DISABLE_PROVIDERS); cache miss for {spec.label}")
        prov = self.provider(spec.provider)
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                c = await prov.complete(spec.model, system, messages, temperature=temp,
                                        max_tokens=max_tokens, effort=spec.effort)
                break
            except BudgetExceeded:
                raise
            except Exception as e:  # noqa: BLE001 - provider errors are varied
                last_err = e
                self.stats["errors"] += 1
                _log_jsonl("llm_errors.jsonl", {"role": role, "spec": asdict(spec), "attempt": attempt,
                                                "error": str(e)[:500]})
                await asyncio.sleep(2 * (attempt + 1))
        else:
            raise ProviderError(f"{spec.label} failed 3 times: {last_err}")
        self.budget.charge(spec.provider, spec.model, c.cost_usd, role)
        self.cache.put(key, {"text": c.text, "input_tokens": c.input_tokens,
                             "output_tokens": c.output_tokens, "model": spec.model,
                             "provider": spec.provider, "t": time.time()})
        trace_call(role=role, provider=spec.provider, model=spec.model, family=spec.family,
                   messages=([{"role": "system", "content": system}] if system else []) + messages,
                   output=c.text, input_tokens=c.input_tokens, output_tokens=c.output_tokens,
                   cost=c.cost_usd, latency_s=c.latency_s, cached=False)
        return c

    async def json(self, role: str, user: str, schema: type[T], system: str = "", *,
                   spec: ModelSpec | None = None, max_tokens: int = 3000,
                   temperature: float | None = None,
                   validate: Callable[[T], str | None] | None = None) -> tuple[T | None, Completion | None]:
        """Ask for JSON, validate with Pydantic (+ optional extra check), retry twice with the error.

        `validate` returns an error message (string) when a schema-valid object still breaks a
        code-enforced constraint; that message is fed back like a validation error.
        Returns (None, last_completion) when all three attempts fail; the item is logged.
        """
        schema_txt = json.dumps(_compact_schema(schema), ensure_ascii=False)
        prompt = (f"{user}\n\nReturn ONLY one JSON object, no prose, no code fences. "
                  f"It must match this JSON schema:\n{schema_txt}")
        history: list[dict] = []
        c: Completion | None = None
        err = ""
        for attempt in range(3):
            c = await self.chat(role, prompt, system, spec=spec, history=history,
                                max_tokens=max_tokens, temperature=temperature,
                                use_cache=True)
            try:
                obj = schema.model_validate(extract_json(c.text))
                problem = validate(obj) if validate else None
                if not problem:
                    return obj, c
                err = problem
            except (ValueError, ValidationError) as e:
                err = str(e)[:1500]
            history = history + [{"role": "user", "content": prompt},
                                 {"role": "assistant", "content": c.text}]
            prompt = (f"Your previous reply was rejected: {err}\n"
                      "Fix it and return ONLY the corrected JSON object.")
        self.stats["json_failures"] += 1
        _log_jsonl("json_failures.jsonl", {"role": role, "schema": schema.__name__, "error": err,
                                           "last": (c.text if c else "")[:2000]})
        return None, c


def _compact_schema(schema: type[BaseModel]) -> dict:
    s = schema.model_json_schema()

    def strip(node):
        if isinstance(node, dict):
            return {k: strip(v) for k, v in node.items() if k not in ("title",)}
        if isinstance(node, list):
            return [strip(v) for v in node]
        return node

    return strip(s)


def _log_jsonl(name: str, row: dict) -> None:
    if os.environ.get("CRUX_LAB_TEST_LOGS") == "0":
        return
    try:
        LOGS.mkdir(exist_ok=True)
        with (LOGS / name).open("a", encoding="utf-8") as f:
            f.write(json.dumps({"t": time.time(), **row}, ensure_ascii=False) + "\n")
    except OSError:
        pass
