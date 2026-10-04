"""LobBot TaskSpecs for model-level differentiation: one compressed model per cognitive profile.

    python3 lobbot_specs.py [runs dir]     # writes lab/lobbot/<profile>.taskspec.json

LobBot (github.com/OliverVillson/LobBot) prunes the experts of Qwen3-30B-A3B that a task does not route through
(REAP), heals and quantizes. Calibrated on one profile's signature operation, each profile keeps different
experts. Seed examples are that operation's real outputs, taken verbatim from recorded runs (successful runs
only). Then on the VM: `lobbot run lab/lobbot/skeptic.taskspec.json --save`, and run the model condition with
APORIA_MODELS="skeptic=<saved model>,explorer=<saved model>,..." (see server.model_plan).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from metrics import failed

LAB = Path(__file__).parent
LIT = {e["id"]: e for e in json.loads((LAB / "literature.json").read_text())}

# profile -> (operation, node types it writes, output key, description, output format, eval criteria)
SPECS = {
    "skeptic": ("DOUBT", {"objection", "counterexample"}, "objections",
                "Give the strongest ways a philosophical claim could be wrong: objections or concrete counterexamples.",
                '{"objections": [{"kind": "objection"|"counterexample", "text": str, "strength": 0-1}]}',
                "Valid JSON in the schema. Each item attacks the given claim itself, is concrete and philosophically "
                "precise, and differs from the others; counterexamples describe a specific case."),
    "explorer": ("IMAGINE", {"thought_experiment", "alternative"}, "items",
                 "Invent thought experiments that would test a philosophical claim, or alternative hypotheses that answer "
                 "the question differently.",
                 '{"items": [{"kind": "thought_experiment"|"alternative", "text": str}]}',
                 "Valid JSON in the schema. Each item is specific and imaginable, bears on the claim, and is not a "
                 "restatement of a standard example without a new twist."),
    "minimalist": ("INTROSPECT", {"assumption"}, "assumptions",
                   "List the hidden assumptions a philosophical claim depends on, rated by how load-bearing and how "
                   "plausible each is.",
                   '{"assumptions": [{"text": str, "load": 0-1, "plausibility": 0-1}]}',
                   "Valid JSON in the schema. Each assumption is genuinely presupposed by the claim, not stated in it, "
                   "and the load rating reflects how much the claim would suffer without it."),
    "synthesizer": ("MEMORY", {"evidence"}, "evidence",
                    "Given a philosophical claim and a retrieved literature entry, extract the evidence or established "
                    "position it provides and whether it supports or undermines the claim.",
                    '{"evidence": [{"text": str, "source": source id, "supports": true|false}]}',
                    "Valid JSON in the schema. Evidence is faithful to the entry, cites its id, and the supports flag "
                    "matches the entry's bearing on the claim."),
}
# ponytail: the formalist's signature output (the propositional translation) is not stored in run traces yet;
# log op outputs in the run record before adding a formalist spec.


def build(runs: list[dict], profile: str) -> dict:
    op, kinds, key, desc, fmt, crit = SPECS[profile]
    seeds = {}
    for r in runs:
        st = r["agents"][profile]
        nodes = {n["id"]: n for n in st["nodes"]}
        for n in st["nodes"]:
            parent = nodes.get(n["parent"])
            if n["type"] not in kinds or not parent or (n.get("formal") or n.get("source") == "memory"):
                continue
            if profile == "synthesizer":
                e = LIT.get(n.get("source"))
                if not e:
                    continue
                inp = f"Question: {r['question']}\nClaim: {parent['text']}\nLiterature <{e['id']}> {e['title']}: {e['text']}"
                item = {"text": n["text"], "source": e["id"],
                        "supports": any(x["src"] == n["id"] and x["rel"] == "supports" for x in st["edges"])}
            else:
                inp = f"Question: {r['question']}\nClaim: {parent['text']}"
                if profile == "skeptic":
                    item = {"kind": n["type"], "text": n["text"], "strength": round(n["conf"], 2)}
                elif profile == "explorer":  # imagine stores "text → implication"
                    item = {"kind": n["type"], "text": n["text"]}
                else:
                    item = {"text": n["text"], "load": round(n.get("load", 0.5), 2), "plausibility": round(n["conf"], 2)}
            seeds.setdefault(inp, []).append(item)
    examples = [{"input": i, "output": json.dumps({key: items[:4]}, ensure_ascii=False)} for i, items in seeds.items()][:50]
    return {"version": 1, "task_name": f"aporia-{profile}-{op.lower()}",
            "description": f"APORIA {op} operation, as run by the {profile} profile. {desc}",
            "input_format": "A philosophical question and the claim under examination" +
                            (", plus one retrieved literature entry." if profile == "synthesizer" else "."),
            "output_format": "One JSON object: " + fmt, "seed_examples": examples, "eval_criteria": crit,
            "target": {"max_size_gb": 7, "min_tok_s": 40, "laptop_ram_gb": 16}}


def main(src: Path):
    runs = [json.loads(f.read_text()) for f in sorted(src.glob("*.json"))]
    runs = [r for r in runs if "per_agent" in r.get("metrics", {}) and not (r.get("failed") or failed(r["agents"]))]
    out = LAB / "lobbot"
    out.mkdir(exist_ok=True)
    for p in SPECS:
        spec = build(runs, p)
        assert 3 <= len(spec["seed_examples"]) <= 50, f"{p}: {len(spec['seed_examples'])} seed examples"  # LobBot's limits
        (out / f"{p}.taskspec.json").write_text(json.dumps(spec, indent=2, ensure_ascii=False))
        print(f"{p}: {len(spec['seed_examples'])} seed examples from {len(runs)} runs")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else LAB / "runs")
