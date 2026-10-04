"""`make providers`: discover, probe, and assign models to roles with family diversity."""
from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timezone

import yaml

from crux_lab.config import MODELS_YAML, RESOLVED_MODELS, settings
from crux_lab.llm.providers import available_providers, build_provider

# Order decides the gauntlet: 1st family -> Defender A, 2nd -> Defender B, 3rd -> Referee (strongest first).
FAMILY_PREFERENCE = ["anthropic", "openai", "kimi", "glm", "mistral", "qwen", "llama", "gpt-oss", "gemma", "deepseek"]


def _norm(x: str) -> str:
    import re
    return re.sub(r"[._/\s]+", "-", x.lower())


def family_of(model_id: str, declared: str) -> str:
    if declared != "small":
        return declared
    m = model_id.lower()
    for fam, keys in {"llama": ["llama"], "gemma": ["gemma"], "gpt-oss": ["gpt-oss"],
                      "anthropic": ["claude", "haiku"], "openai": ["gpt-5"], "qwen": ["qwen"]}.items():
        if any(k in m for k in keys):
            return fam
    return "other"


async def _probe(provider_name: str, model: str) -> tuple[bool, float, str]:
    prov = build_provider(provider_name)
    t0 = time.monotonic()
    try:
        c = await asyncio.wait_for(
            prov.complete(model, "You are a probe. Reply with the single word OK.",
                          [{"role": "user", "content": "Say OK."}], max_tokens=400, effort="low"),
            timeout=240)
        ok = "ok" in c.text.lower()
        return ok, time.monotonic() - t0, "" if ok else f"unexpected reply: {c.text[:80]}"
    except Exception as e:  # noqa: BLE001
        return False, time.monotonic() - t0, str(e)[:300]


async def resolve(write: bool = True) -> dict:
    cfg = yaml.safe_load(MODELS_YAML.read_text())
    provs = available_providers(settings)
    listed: dict[str, list[str]] = {}
    errors: dict[str, str] = {}
    for p in provs:
        try:
            listed[p] = await build_provider(p).list_models()
        except Exception as e:  # noqa: BLE001
            errors[p] = f"list failed: {str(e)[:200]}"
            listed[p] = []

    # Candidate (provider, model, family, tier_rank) from name patterns.
    candidates: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for fam, by_prov in cfg["families"].items():
        for p, patterns in by_prov.items():
            if p not in listed:
                continue
            for rank, pat in enumerate(patterns):
                # normalise separators: evroc ids look like "llama-3-3-70b-instruct-fp8-9u9p" for Llama-3.3-70B
                matches = [m for m in listed[p] if _norm(pat) in _norm(m)]
                # Prefer exact match, then shortest id (base model over variants).
                matches.sort(key=lambda m: (m.lower() != pat.lower(), len(m)))
                for m in matches[:1]:
                    if (p, m) in seen:
                        continue
                    seen.add((p, m))
                    small_pats = cfg["families"].get("small", {}).get(p, [])
                    is_small = fam == "small" or any(_norm(sp) in _norm(m) for sp in small_pats)
                    candidates.append({"provider": p, "model": m, "family": family_of(m, fam),
                                       "small": is_small, "rank": rank})

    results = await asyncio.gather(*[_probe(c["provider"], c["model"]) for c in candidates])
    models = []
    for c, (ok, lat, err) in zip(candidates, results):
        models.append({**c, "ok": ok, "latency_s": round(lat, 2), "error": err})
    working = [m for m in models if m["ok"]]

    roles, families = assign_roles(working, cfg.get("effort", {}), cfg.get("bulk_family"),
                                   cfg.get("role_preference"))
    n = len(families)
    resolved = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "providers_available": provs,
        "provider_errors": errors,
        "models": models,
        "families": families,
        "diversity": "full" if n >= 3 else f"degraded: {n} {'family' if n == 1 else 'families'}",
        "roles": roles,
    }
    if write:
        RESOLVED_MODELS.write_text(json.dumps(resolved, indent=2))
    return resolved


def assign_roles(working: list[dict], effort: dict, bulk_family: str | list | None = None,
                 role_preference: dict[str, list[str]] | None = None) -> tuple[dict, list[str]]:
    if not working:
        return {}, []
    by_fam: dict[str, list[dict]] = {}
    for m in sorted(working, key=lambda m: (m["small"], m["rank"])):  # noqa: B007
        by_fam.setdefault(m["family"], []).append(m)
    fams = sorted(by_fam, key=lambda f: FAMILY_PREFERENCE.index(f) if f in FAMILY_PREFERENCE else 99)
    strong = {f: [m for m in by_fam[f] if not m["small"]] or by_fam[f] for f in fams}

    def spec(m: dict, role: str) -> dict:
        return {"provider": m["provider"], "model": m["model"], "family": m["family"],
                "effort": effort.get(role, "low")}

    f1 = fams[0]
    f2 = fams[1] if len(fams) > 1 else f1
    f3 = fams[2] if len(fams) > 2 else (fams[1] if len(fams) > 1 else f1)
    pick = lambda f, i=0: strong[f][min(i, len(strong[f]) - 1)]  # noqa: E731
    roles = {r: spec(pick(f1), r) for r in ("formalizer", "defender_a")}
    # Bulk roles (many calls: extraction, reranking) go to `bulk_family` when it exists, so the
    # Claude plan that also runs the build session is not drained by the lab.
    prefs = bulk_family if isinstance(bulk_family, list) else [bulk_family]
    fb = next((f for f in prefs if f in strong), f1)
    for r in ("extractor", "reranker"):
        roles[r] = spec(pick(fb), r)
    # Defender B: other family; with one family, at least a different model.
    roles["defender_b"] = spec(pick(f2, 0 if f2 != f1 else 1), "defender_b")
    # Referee: third family; if it must share a family, use a different model than that defender.
    roles["referee"] = spec(pick(f3, 0 if f3 not in (f1, f2) else 1), "referee")
    gens = []
    for f in fams:
        for m in strong[f][:3 if len(fams) == 1 else 2]:
            gens.append(spec(m, "generators"))
    roles["generators"] = gens
    small = [m for m in working if m["small"]]
    roles["naive_questioner"] = spec(small[0] if small else pick(f1), "naive_questioner")
    # Judgement roles (novelty check, brief writer): the first preferred family that is available.
    for r, prefs_r in (role_preference or {}).items():
        f = next((x for x in prefs_r if x in strong), None)
        if f:
            roles[r] = spec(pick(f), r)
    return roles, fams


def main() -> None:
    r = asyncio.run(resolve())
    ok = [f"{m['provider']}:{m['model']} ({m['family']}, {m['latency_s']}s)" for m in r["models"] if m["ok"]]
    bad = [f"{m['provider']}:{m['model']} -> {m['error'][:120]}" for m in r["models"] if not m["ok"]]
    print(f"providers available: {r['providers_available']}")
    print("working:", *ok, sep="\n  ") if ok else print("working: NONE")
    if bad:
        print("failed:", *bad, sep="\n  ")
    print(f"families: {r['families']} -> diversity {r['diversity']}")
    for role, s in r["roles"].items():
        if isinstance(s, list):
            print(f"  {role}: " + ", ".join(f"{x['family']}:{x['model']}" for x in s))
        else:
            print(f"  {role}: {s['family']}:{s['model']} (effort {s['effort']})")
