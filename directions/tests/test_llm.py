import asyncio

import pytest
from pydantic import BaseModel

from crux_lab.llm.budget import Budget, BudgetExceeded
from crux_lab.llm.cache import DiskCache
from crux_lab.llm.client import LLMClient
from crux_lab.llm.providers import extract_json, flatten


class Out(BaseModel):
    answer: str
    n: int


def test_cache_hit_costs_zero(tmp_path):
    calls = []

    def responder(system, messages, model):
        calls.append(1)
        return "hello"

    client = LLMClient.fake(responder, tmp_cache=DiskCache(tmp_path))
    a = asyncio.run(client.chat("extractor", "hi"))
    b = asyncio.run(client.chat("extractor", "hi"))
    assert a.text == b.text == "hello"
    assert a.cost_usd > 0 and b.cost_usd == 0.0 and b.cached
    assert len(calls) == 1


def test_json_retries_with_validation_error():
    replies = iter(['not json', '{"answer": "x"}', '```json\n{"answer": "x", "n": 2}\n```'])
    seen = []

    def responder(system, messages, model):
        seen.append(messages[-1]["content"])
        return next(replies)

    client = LLMClient.fake(responder)
    obj, _ = asyncio.run(client.json("extractor", "give", Out))
    assert obj == Out(answer="x", n=2)
    assert "rejected" in seen[1] and "rejected" in seen[2]


def test_json_gives_up_after_two_retries():
    client = LLMClient.fake(lambda s, m, model: "nope")
    obj, c = asyncio.run(client.json("extractor", "give", Out))
    assert obj is None and client.stats["json_failures"] == 1


def test_custom_validator_feeds_back():
    replies = iter(['{"answer": "bad", "n": 1}', '{"answer": "good", "n": 1}'])
    client = LLMClient.fake(lambda s, m, model: next(replies))
    obj, _ = asyncio.run(client.json("extractor", "give", Out,
                                     validate=lambda o: "answer must be good" if o.answer != "good" else None))
    assert obj.answer == "good"


def test_budget_exceeded(tmp_path):
    b = Budget(limit_usd=0.001, cli_limit=1, ledger=tmp_path / "spend.jsonl")
    b.charge("databricks", "m", 0.01)
    with pytest.raises(BudgetExceeded):
        b.check("databricks")
    b.charge("codex_cli", "m", 0.5)
    with pytest.raises(BudgetExceeded):
        b.check("codex_cli")
    again = Budget(limit_usd=1, cli_limit=5, ledger=tmp_path / "spend.jsonl")
    assert again.cli_calls == 1 and abs(again.spent_usd - 0.01) < 1e-9


def test_extract_json_variants():
    assert extract_json('Sure! {"a": 1} done') == {"a": 1}
    assert extract_json('```json\n[1,2]\n```') == [1, 2]
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_flatten_multi_turn():
    s = flatten("SYS", [{"role": "user", "content": "q"}, {"role": "assistant", "content": "a"},
                       {"role": "user", "content": "fix"}])
    assert s.startswith("SYS") and "ASSISTANT" in s and s.rstrip().endswith("message. ===")


def test_assign_roles_family_diversity():
    from crux_lab.llm.resolve import assign_roles
    w = [{"provider": "p", "model": m, "family": f, "small": False, "rank": 0}
         for m, f in [("c", "anthropic"), ("g", "openai"), ("l", "llama")]]
    roles, fams = assign_roles(w, {})
    assert {roles["defender_a"]["family"], roles["defender_b"]["family"], roles["referee"]["family"]} == {"anthropic", "openai", "llama"}
    assert len(roles["generators"]) == 3


def test_evroc_families_give_three_family_gauntlet_and_bulk_off_claude():
    from crux_lab.llm.resolve import assign_roles
    w = [{"provider": "claude_cli", "model": m, "family": "anthropic", "small": m == "haiku", "rank": r}
         for r, m in enumerate(["sonnet", "opus", "haiku"])]
    w += [{"provider": "evroc", "model": m, "family": f, "small": False, "rank": 0}
          for m, f in [("meta-llama/Llama-3.3-70B-Instruct", "llama"), ("Qwen/Qwen3", "qwen"),
                       ("openai/gpt-oss-120b", "gpt-oss")]]
    roles, fams = assign_roles(w, {}, ["openai", "gpt-oss", "llama", "qwen"])
    assert len({roles[r]["family"] for r in ("defender_a", "defender_b", "referee")}) == 3
    assert roles["extractor"]["provider"] == "evroc" and roles["extractor"]["family"] == "gpt-oss"


def test_evroc_style_ids_match_family_patterns():
    from crux_lab.llm.resolve import _norm
    assert _norm("Llama-3.3-70B") in _norm("llama-3-3-70b-instruct-fp8-9u9p")
    assert _norm("gpt-oss-120b") in _norm("gpt-oss-120b-x1y2")
    assert _norm("Qwen3") in _norm("qwen3-235b-a22b-k3m4")
