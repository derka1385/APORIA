# APORIA lab: cognitive differentiation

Five reasoners start from the same philosophical question. They share one
engine but run different cognitive policies (routing, thresholds, context
visibility, literature access, branching, adversarial pressure, sampling,
stopping). Δ scales how far apart those policies are. The lab streams every
state change to a live nebula and measures how differently they reasoned.

```bash
bash lab/run.sh        # pulls qwen2.5:3b + nomic-embed-text if missing, opens http://localhost:8740
```

Needs Ollama and Python 3.10+. No pip dependencies.

- `ARCHITECTURE.md`: design, LobBot findings, what is experimental
- `engine.py`: state, cognitive operations, controller
- `profiles.py`: policy vectors and Δ interpolation (`python3 profiles.py` self-checks)
- `metrics.py`: Δ measurements (`python3 metrics.py` self-checks)
- `server.py`: local API + SSE stream; finished runs land in `runs/`

Environment: `APORIA_MODEL` (default `qwen2.5:3b`), `APORIA_MODELS`
(comma-separated variants for the model condition), `APORIA_PORT` (8740).
