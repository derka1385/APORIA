"""LLM providers. Chain order: Databricks, OpenRouter, Anthropic API, then subscription CLIs.

The CLI providers (codex_cli = ChatGPT subscription, claude_cli = Claude subscription) run as
isolated completions: no tools, no shell, no web, no user config. They ignore temperature.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import tempfile
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx

from crux_lab.config import Settings, settings as default_settings
from crux_lab.llm.budget import estimate_cost


@dataclass
class Completion:
    text: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    provider: str
    model: str
    latency_s: float = 0.0
    cached: bool = False


class ProviderError(RuntimeError):
    pass


def approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def flatten(system: str, messages: list[dict]) -> str:
    """Render a chat as one prompt for single-turn CLIs."""
    if len(messages) == 1 and messages[0]["role"] == "user":
        body = messages[0]["content"]
    else:
        parts = []
        for m in messages:
            tag = "USER" if m["role"] == "user" else "ASSISTANT (your earlier reply)"
            parts.append(f"=== {tag} ===\n{m['content']}")
        parts.append("=== Respond now to the last USER message. ===")
        body = "\n\n".join(parts)
    return f"{system}\n\n{body}" if system else body


class Provider(ABC):
    name: str = "base"
    concurrency: int = 6

    def __init__(self) -> None:
        self._sem = asyncio.Semaphore(self.concurrency)

    @abstractmethod
    async def _complete(self, model: str, system: str, messages: list[dict],
                        temperature: float, max_tokens: int, effort: str) -> Completion: ...

    async def complete(self, model: str, system: str, messages: list[dict], *,
                       temperature: float = 0.2, max_tokens: int = 2000,
                       effort: str = "low") -> Completion:
        async with self._sem:
            t0 = time.monotonic()
            c = await self._complete(model, system, messages, temperature, max_tokens, effort)
            c.latency_s = time.monotonic() - t0
            return c

    async def list_models(self) -> list[str]:
        return []


# ---------------------------------------------------------------- OpenAI-compatible APIs
class _OpenAICompatible(Provider):
    concurrency = 8

    def __init__(self, base_url: str, api_key: str):
        super().__init__()
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=180, max_retries=2)

    async def _complete(self, model, system, messages, temperature, max_tokens, effort):
        msgs = ([{"role": "system", "content": system}] if system else []) + messages
        r = await self.client.chat.completions.create(
            model=model, messages=msgs, temperature=temperature, max_tokens=max_tokens)
        text = r.choices[0].message.content or ""
        if isinstance(text, list):  # some Databricks endpoints return content parts
            text = "".join(p.get("text", "") for p in text if isinstance(p, dict))
        it = getattr(r.usage, "prompt_tokens", None) or approx_tokens(json.dumps(msgs))
        ot = getattr(r.usage, "completion_tokens", None) or approx_tokens(text)
        return Completion(text, it, ot, estimate_cost(model, it, ot), self.name, model)


class DatabricksProvider(_OpenAICompatible):
    name = "databricks"

    def __init__(self, s: Settings = default_settings):
        self.host, self.token = s.databricks_host, s.databricks_token
        super().__init__(f"{self.host}/serving-endpoints", self.token)

    async def list_models(self) -> list[str]:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(f"{self.host}/api/2.0/serving-endpoints",
                            headers={"Authorization": f"Bearer {self.token}"})
            r.raise_for_status()
            return [e["name"] for e in r.json().get("endpoints", [])]


class OpenRouterProvider(_OpenAICompatible):
    name = "openrouter"

    def __init__(self, s: Settings = default_settings):
        super().__init__("https://openrouter.ai/api/v1", s.openrouter_key)

    async def list_models(self) -> list[str]:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get("https://openrouter.ai/api/v1/models")
            r.raise_for_status()
            return [m["id"] for m in r.json().get("data", [])]


class EvrocProvider(_OpenAICompatible):
    """evroc Think: EU-hosted open models (Llama, Qwen, Mistral, gpt-oss, Kimi, Gemma, ...) behind an
    OpenAI-compatible API. Model ids are Hugging Face handles, e.g. meta-llama/Llama-3.3-70B-Instruct."""

    name = "evroc"
    concurrency = int(os.environ.get("EVROC_CONCURRENCY", "12"))
    BASE = "https://models.think.evroc.com/v1"
    MIN_MAX_TOKENS = 8192   # reasoning models (Kimi, GLM, Qwen3, gpt-oss) spend output tokens before answering

    async def _complete(self, model, system, messages, temperature, max_tokens, effort):
        return await super()._complete(model, system, messages, temperature,
                                       max(max_tokens, self.MIN_MAX_TOKENS), effort)

    def __init__(self, s: Settings = default_settings):
        self.key = s.evroc_key
        super().__init__(self.BASE, self.key)

    async def list_models(self) -> list[str]:
        # OpenAI-style model list; if the endpoint is unavailable, fall back to ids pinned in models.yaml
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.get(f"{self.BASE}/models", headers={"Authorization": f"Bearer {self.key}"})
                r.raise_for_status()
                return [m["id"] for m in r.json().get("data", [])]
        except Exception:  # noqa: BLE001
            import yaml

            from crux_lab.config import MODELS_YAML
            return list((yaml.safe_load(MODELS_YAML.read_text()) or {}).get("evroc_ids", []))


class AnthropicProvider(Provider):
    name = "anthropic"
    concurrency = 6

    def __init__(self, s: Settings = default_settings):
        super().__init__()
        from anthropic import AsyncAnthropic

        self.client = AsyncAnthropic(api_key=s.anthropic_key, timeout=180, max_retries=2)

    async def _complete(self, model, system, messages, temperature, max_tokens, effort):
        r = await self.client.messages.create(
            model=model, system=system or None, messages=messages,
            temperature=temperature, max_tokens=max_tokens)
        text = "".join(b.text for b in r.content if getattr(b, "type", "") == "text")
        it, ot = r.usage.input_tokens, r.usage.output_tokens
        return Completion(text, it, ot, estimate_cost(model, it, ot), self.name, model)

    async def list_models(self) -> list[str]:
        page = await self.client.models.list(limit=100)
        return [m.id for m in page.data]


# ---------------------------------------------------------------- subscription CLIs
async def _run(cmd: list[str], stdin: str, env: dict, timeout: float, cwd: str | None = None):
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE, env=env, cwd=cwd)
    try:
        out, err = await asyncio.wait_for(proc.communicate(stdin.encode("utf-8")), timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise ProviderError(f"{cmd[0]} timed out after {timeout}s")
    return proc.returncode, out.decode("utf-8", "replace"), err.decode("utf-8", "replace")


class CodexCLIProvider(Provider):
    """`codex exec` on the ChatGPT subscription, as an isolated read-only completion."""

    name = "codex_cli"
    concurrency = int(os.environ.get("CODEX_CONCURRENCY", "6"))
    MODELS = ["gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"]

    def __init__(self, s: Settings = default_settings, timeout: float = 600):
        super().__init__()
        self.bin, self.timeout = s.codex_bin, timeout

    @staticmethod
    def env() -> dict:
        return {k: v for k, v in os.environ.items()
                if not (k.startswith("CODEX_") and k != "CODEX_HOME")}

    async def _complete(self, model, system, messages, temperature, max_tokens, effort):
        prompt = flatten(system, messages)
        with tempfile.TemporaryDirectory(prefix="crux-lab-codex-") as wd:
            out_path = Path(wd) / "out.txt"
            cmd = [self.bin, "exec", "--ephemeral", "--ignore-user-config", "--ignore-rules",
                   "--skip-git-repo-check", "--sandbox", "read-only",
                   "--disable", "shell_tool", "--disable", "remote_plugin",
                   "-c", 'web_search="disabled"', "-c", "tools.web_search=false",
                   "-c", 'approval_policy="never"', "-c", f'model_reasoning_effort="{effort}"',
                   "--model", model, "--color", "never", "--cd", wd,
                   "--output-last-message", str(out_path), "-"]
            code, out, err = await _run(cmd, prompt, self.env(), self.timeout)
            text = out_path.read_text("utf-8").strip() if out_path.exists() else ""
        if code != 0 or not text:
            raise ProviderError(f"codex exit {code}: {(err or out)[-400:]}")
        it, ot = approx_tokens(prompt), approx_tokens(text)
        return Completion(text, it, ot, estimate_cost(model, it, ot), self.name, model)

    async def list_models(self) -> list[str]:
        return list(self.MODELS)


class ClaudeCLIProvider(Provider):
    """`claude -p` on the Claude subscription. Never add --bare (it skips OAuth)."""

    name = "claude_cli"
    concurrency = int(os.environ.get("CLAUDE_CLI_CONCURRENCY", "4"))
    MODELS = ["opus", "sonnet", "haiku"]

    def __init__(self, s: Settings = default_settings, timeout: float = 600):
        super().__init__()
        self.bin, self.timeout = s.claude_bin, timeout

    @staticmethod
    def env() -> dict:
        drop = {"CLAUDE_EFFORT", "CLAUDE_PID", "CLAUDE_AGENT_SDK_VERSION", "CLAUDECODE"}
        return {k: v for k, v in os.environ.items()
                if k not in drop and not (k.startswith("CLAUDE_CODE_") and k != "CLAUDE_CODE_OAUTH_TOKEN")
                and k != "ANTHROPIC_API_KEY"}

    async def _complete(self, model, system, messages, temperature, max_tokens, effort):
        prompt = flatten("", messages)
        cmd = [self.bin, "-p", "--output-format", "json", "--no-session-persistence",
               "--model", model, "--setting-sources", "", "--strict-mcp-config",
               "--disable-slash-commands", "--tools", ""]
        if system:
            cmd += ["--system-prompt", system]
        if effort:
            cmd += ["--effort", effort]
        code, out, err = await _run(cmd, prompt, self.env(), self.timeout,
                                    cwd=tempfile.gettempdir())
        try:
            env = json.loads(out.strip().splitlines()[-1]) if out.strip() else {}
        except json.JSONDecodeError:
            env = {}
        if code != 0 or env.get("is_error") or not env:
            raise ProviderError(f"claude exit {code}: {(env.get('result') or err or out)[-400:]}")
        text = env.get("result", "")
        u = env.get("usage", {}) or {}
        it = (u.get("input_tokens") or 0) + (u.get("cache_read_input_tokens") or 0) \
            + (u.get("cache_creation_input_tokens") or 0) or approx_tokens(prompt)
        ot = u.get("output_tokens") or approx_tokens(text)
        cost = env.get("total_cost_usd") or estimate_cost(model, it, ot)
        return Completion(text, it, ot, cost, self.name, model)

    async def list_models(self) -> list[str]:
        return list(self.MODELS)


# ---------------------------------------------------------------- fake (tests)
class FakeProvider(Provider):
    """Canned responses for tests. `responder(system, messages, model) -> str`."""

    name = "fake"
    concurrency = 16

    def __init__(self, responder: Callable[[str, list[dict], str], str] | None = None):
        super().__init__()
        self.responder = responder or (lambda s, m, model: '{"ok": true}')
        self.calls: list[dict] = []

    async def _complete(self, model, system, messages, temperature, max_tokens, effort):
        self.calls.append({"model": model, "system": system, "messages": messages})
        text = self.responder(system, messages, model)
        it, ot = approx_tokens(system + json.dumps(messages)), approx_tokens(text)
        return Completion(text, it, ot, estimate_cost(model, it, ot), self.name, model)

    async def list_models(self) -> list[str]:
        return ["fake-strong", "fake-small"]


PROVIDER_ORDER = ["databricks", "evroc", "openrouter", "anthropic", "codex_cli", "claude_cli"]
_CLASSES = {
    "databricks": DatabricksProvider, "evroc": EvrocProvider, "openrouter": OpenRouterProvider,
    "anthropic": AnthropicProvider, "codex_cli": CodexCLIProvider, "claude_cli": ClaudeCLIProvider,
}


def build_provider(name: str, s: Settings = default_settings) -> Provider:
    return _CLASSES[name](s)


def available_providers(s: Settings = default_settings) -> list[str]:
    return [p for p in PROVIDER_ORDER if s.has(p)]


_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```")


def extract_json(text: str):
    """Parse the first JSON object/array in model text (handles code fences and preambles)."""
    t = text.strip()
    for cand in (t, *(m.group(1) for m in _FENCE.finditer(t))):
        try:
            return json.loads(cand)
        except json.JSONDecodeError:
            pass
    for open_c, close_c in (("{", "}"), ("[", "]")):
        i, j = t.find(open_c), t.rfind(close_c)
        if 0 <= i < j:
            try:
                return json.loads(t[i:j + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("no JSON object found in model output")
