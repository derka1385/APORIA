"""Environment loading, paths and budget settings. The only module that reads `.env`."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env", override=False)

DATA = ROOT / "data"
RAW = DATA / "raw"                      # shared: PDFs and texts are keyed by paper id
CACHE = ROOT / "cache"
LLM_CACHE = CACHE / "llm"               # shared across topics
LOGS = ROOT / "logs"
CONFIG = ROOT / "config"
MODELS_YAML = CONFIG / "models.yaml"
RESOLVED_MODELS = CONFIG / "resolved_models.json"
WEB_DATA_ROOT = ROOT / "web" / "public" / "data"

# --- topics -------------------------------------------------------------------------------------
# A topic is config/topics/<slug>.yaml (queries, relevance filter, screening scale, tradition lenses).
# Select one with CRUX_LAB_TOPIC=<slug> (`make ... TOPIC=<slug>` / `python -m crux_lab.cli --topic <slug>`).
# The default topic keeps the original paths (data/, results/, web/public/data/); others live under
# data/topics/<slug>/, results/topics/<slug>/, cache/index/<slug>/ and web/public/data/topics/<slug>/.
TOPICS_DIR = CONFIG / "topics"


def load_topics() -> dict[str, dict]:
    import yaml

    out = {}
    for f in sorted(TOPICS_DIR.glob("*.yaml")):
        t = yaml.safe_load(f.read_text())
        out[t["slug"]] = t
    return out


TOPICS = load_topics()
DEFAULT_TOPIC = next((s for s, t in TOPICS.items() if t.get("default")), next(iter(TOPICS), "divine-hiddenness"))
TOPIC_SLUG = (os.environ.get("CRUX_LAB_TOPIC") or DEFAULT_TOPIC).strip()
if TOPICS and TOPIC_SLUG not in TOPICS:
    raise SystemExit(f"unknown topic {TOPIC_SLUG!r}; available: {', '.join(TOPICS)} (config/topics/*.yaml)")
TOPIC: dict = TOPICS.get(TOPIC_SLUG, {})
IS_DEFAULT_TOPIC = TOPIC_SLUG == DEFAULT_TOPIC


def topic_paths(slug: str) -> dict[str, Path]:
    default = slug == DEFAULT_TOPIC
    base = DATA if default else DATA / "topics" / slug
    return {
        "data": base, "corpus": base / "corpus.jsonl", "targets": base / "targets.json", "runs": base / "runs",
        "briefs": base / "briefs", "db": base / "crux.sqlite", "manual": base / "manual_targets",
        "map_stats": base / "map_stats.json",
        "results": ROOT / "results" if default else ROOT / "results" / "topics" / slug,
        "index": CACHE / "index" if default else CACHE / "index" / slug,
        "web": WEB_DATA_ROOT if default else WEB_DATA_ROOT / "topics" / slug,
    }


_P = topic_paths(TOPIC_SLUG)
TOPIC_DATA = _P["data"]
CORPUS = _P["corpus"]
TARGETS = _P["targets"]
RUNS = _P["runs"]
BRIEFS = _P["briefs"]
DB_PATH = _P["db"]
MANUAL_TARGETS = _P["manual"]
MAP_STATS = _P["map_stats"]
TOPIC_RESOLVED = TOPIC_DATA / "resolved_models.json"   # snapshot of the model assignment this topic ran with
RESULTS = _P["results"]
INDEX_DIR = _P["index"]
WEB_DATA = _P["web"]
PROMPTS = Path(__file__).resolve().parent / "agents" / "prompts"


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


@dataclass(frozen=True)
class Settings:
    databricks_host: str
    databricks_token: str
    openrouter_key: str
    evroc_key: str
    anthropic_key: str
    budget_usd: float
    cli_call_budget: int
    contact_email: str
    codex_bin: str
    claude_bin: str
    enable_cli: bool
    disabled: tuple[str, ...] = ()
    philpapers_api_id: str = ""
    philpapers_api_key: str = ""

    @property
    def user_agent(self) -> str:
        mail = self.contact_email or "unset"
        return f"crux-lab-hackathon (mailto:{mail})"

    def has(self, provider: str) -> bool:
        if provider in self.disabled:
            return False
        return {
            "databricks": bool(self.databricks_host and self.databricks_token),
            "openrouter": bool(self.openrouter_key),
            "evroc": bool(self.evroc_key),
            "anthropic": bool(self.anthropic_key),
            "codex_cli": self.enable_cli,
            "claude_cli": self.enable_cli,
        }.get(provider, False)


def _codex_default() -> str:
    app = "/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex"
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if d and (Path(d) / "codex").exists():
            return str(Path(d) / "codex")
    return app if Path(app).exists() else "codex"


def load_settings() -> Settings:
    host = _env("DATABRICKS_HOST").rstrip("/")
    if host and not host.startswith("http"):
        host = "https://" + host
    return Settings(
        databricks_host=host,
        databricks_token=_env("DATABRICKS_TOKEN"),
        openrouter_key=_env("OPENROUTER_API_KEY"),
        evroc_key=_env("EVROC_API_KEY"),
        anthropic_key=_env("ANTHROPIC_API_KEY"),
        budget_usd=float(_env("LLM_BUDGET_USD", "20") or 20),
        cli_call_budget=int(_env("CLI_CALL_BUDGET", "4000") or 4000),
        contact_email=_env("CONTACT_EMAIL"),
        codex_bin=_env("CODEX_BIN") or _codex_default(),
        claude_bin=_env("CLAUDE_BIN", "claude"),
        enable_cli=_env("ENABLE_CLI_PROVIDERS", "1") not in ("0", "false", "no"),
        # e.g. DISABLE_PROVIDERS=codex_cli after a provider hits a spend cap
        disabled=tuple(x.strip() for x in _env("DISABLE_PROVIDERS").split(",") if x.strip()),
        philpapers_api_id=_env("PHILPAPERS_API_ID"),
        philpapers_api_key=_env("PHILPAPERS_API_KEY"),
    )


settings = load_settings()

for _d in (DATA, RAW, TOPIC_DATA, RUNS, BRIEFS, RESULTS, LLM_CACHE, LOGS):
    _d.mkdir(parents=True, exist_ok=True)
