"""Build the APORIA site: the research directions finder is the front door (docs/index.html); APORIA's divergence
measurements move to docs/divergence/, its reasoner replay (docs/lab/) and particle engine (docs/engine/) stay.

    python3 directions/scripts/build_aporia_site.py      # from the APORIA repo root

The finder (directions/web) is built with base /APORIA/docs/ (Pages serves the repo root) and reads its exported data from docs/directions-data/,
so it never collides with APORIA's own docs/data/ (run replays the particle engine and the lab read).
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WEB, DOCS = ROOT / "directions" / "web", ROOT / "docs"


def move_divergence_page() -> None:
    """APORIA's measurements page, once docs/index.html, served from docs/divergence/ with paths fixed."""
    src, dst = DOCS / "index.html", DOCS / "divergence" / "index.html"
    html = src.read_text()
    if 'id="root"' in html:          # already the finder: the divergence page was moved before
        return
    html = html.replace('href="lab/', 'href="../lab/').replace("href=\"lab/?run=", "href=\"../lab/?run=")
    html = html.replace('fetch("data/index.json")', 'fetch("../data/index.json")')
    html = html.replace("`engine/?embed&replay=../data/runs/", "`../engine/?embed&replay=../data/runs/")
    html = html.replace('<a class="mark" href="#">', '<a class="mark" href="../">')
    html = re.sub(r'<nav>', '<nav><a href="../">Research directions</a>', html, count=1)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(html)


def build_finder() -> None:
    env = {**os.environ, "VITE_BASE": "/APORIA/docs/", "VITE_DATA_DIR": "directions-data"}
    subprocess.run(["npm", "run", "-s", "build"], cwd=WEB, env=env, check=True)
    dist = WEB / "dist"
    for name in ("index.html", "404.html"):
        shutil.copyfile(dist / name, DOCS / name)
    # Pages serves this repo from its root, so only a root 404.html catches deep links like /APORIA/docs/brief/<id>;
    # it is the finder itself (absolute asset paths), whose router then shows the page or its own not-found view.
    shutil.copyfile(dist / "404.html", ROOT / "404.html")
    for d in ("assets", "directions-data"):
        if (DOCS / d).exists():
            shutil.rmtree(DOCS / d)
    shutil.copytree(dist / "assets", DOCS / "assets")
    shutil.copytree(dist / "data", DOCS / "directions-data")


if __name__ == "__main__":
    move_divergence_page()
    build_finder()
    print("docs/: finder at /, APORIA divergence at /divergence/, reasoner replay at /lab/, engine at /engine/")
