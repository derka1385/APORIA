"""Every Makefile target also runs as: python -m crux_lab.cli <cmd>."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys


def _providers(a):
    from crux_lab.llm.resolve import main
    main()


def _targets(a):
    from crux_lab.corpus.targets import main
    main()


def _corpus(a):
    from crux_lab.corpus.build import main, refine
    refine() if a.refine else main(skip_fulltext=a.skip_fulltext)


def _map(a):
    from crux_lab.graph.build import main
    asyncio.run(main(targets_only=a.targets_only))


def _run(a):
    from crux_lab.lab.run import main
    asyncio.run(main(a.target))


def _runs(a):
    from crux_lab.lab.run import main_all
    asyncio.run(main_all(only=[x for x in a.only.split(",") if x], skip=[x for x in a.skip.split(",") if x]))


def _bridge(a):
    from crux_lab.lab.bridge import main
    d = asyncio.run(main(a.runs))
    print(json.dumps({k: d[k] for k in ("n", "by_condition", "by_profile")}, indent=1))


def _assess(a):
    from crux_lab.lab.assess import main
    asyncio.run(main())


def _revise(a):
    from crux_lab.lab.assess import main_revise
    asyncio.run(main_revise())


def _export(a):
    from crux_lab.export import main
    main()


def _eval(a):
    from crux_lab.eval.run_all import main
    asyncio.run(main(only=a.only))


def _check(a):
    from crux_lab.config import ROOT
    rc = subprocess.call([sys.executable, "-m", "pytest", "-q", "-m", "not network"], cwd=ROOT)
    if rc == 0 and (ROOT / "web" / "package.json").exists():
        rc = subprocess.call(["npm", "run", "-s", "typecheck"], cwd=ROOT / "web") or \
            subprocess.call(["npm", "run", "-s", "test"], cwd=ROOT / "web")
    sys.exit(rc)


def _demo(a):
    from crux_lab.config import ROOT
    web = ROOT / "web"
    subprocess.check_call(["npm", "run", "build"], cwd=web)
    subprocess.call(["npm", "run", "preview"], cwd=web)


def _demo_video(a):
    from crux_lab.config import ROOT
    subprocess.check_call(["npx", "playwright", "test", "demo.spec.ts"], cwd=ROOT / "web")


def _serve(a):
    import uvicorn
    uvicorn.run("crux_lab.api.server:app", host="127.0.0.1", port=a.port)


def main(argv=None):
    # --topic must be applied before crux_lab.config is imported (paths and queries are read at import).
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--topic" in argv:
        i = argv.index("--topic")
        os.environ["CRUX_LAB_TOPIC"] = argv[i + 1]
        del argv[i:i + 2]
    from crux_lab.config import TOPIC_SLUG
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="crux_lab", epilog="Global option: --topic <slug> (config/topics/<slug>.yaml)")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("providers").set_defaults(f=_providers)
    sub.add_parser("targets").set_defaults(f=_targets)
    c = sub.add_parser("corpus")
    c.add_argument("--skip-fulltext", action="store_true")
    c.add_argument("--refine", action="store_true", help="re-filter the existing corpus and top up full texts")
    c.set_defaults(f=_corpus)
    m = sub.add_parser("map")
    m.add_argument("--targets-only", action="store_true")
    m.set_defaults(f=_map)
    r = sub.add_parser("run")
    r.add_argument("target")
    r.set_defaults(f=_run)
    rs = sub.add_parser("runs")
    rs.add_argument("--only", default="")
    rs.add_argument("--skip", default="")
    rs.set_defaults(f=_runs)
    sub.add_parser("export").set_defaults(f=_export)
    br = sub.add_parser("bridge", help="check APORIA's reasoner objections against the topic's literature")
    br.add_argument("--runs", required=True, help="glob of APORIA run files, e.g. ../aporia/lab/runs/*.json")
    br.set_defaults(f=_bridge)
    sub.add_parser("assess").set_defaults(f=_assess)
    sub.add_parser("revise").set_defaults(f=_revise)
    e = sub.add_parser("eval")
    e.add_argument("--only", default="")
    e.set_defaults(f=_eval)
    sub.add_parser("check").set_defaults(f=_check)
    sub.add_parser("demo").set_defaults(f=_demo)
    sub.add_parser("demo-video").set_defaults(f=_demo_video)
    s = sub.add_parser("serve")
    s.add_argument("--port", type=int, default=8765)
    s.set_defaults(f=_serve)
    a = p.parse_args(argv)
    logging.getLogger(__name__).info("topic: %s", TOPIC_SLUG)
    a.f(a)


if __name__ == "__main__":
    main()
