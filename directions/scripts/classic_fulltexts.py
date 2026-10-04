"""Second full-text pass: open-access PDFs for classic (non-fresh) hiddenness papers."""
import json
import logging

from crux_lab.config import CORPUS, RAW
from crux_lab.corpus import pdf
from crux_lab.corpus.build import load_corpus

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
papers = load_corpus()
cands = [p for p in papers if not p.get("fresh") and p.get("pdf_url") and not p.get("pdf_path")]
cands.sort(key=lambda p: -(p.get("cited_by_count") or 0))
got = 0
for p in cands:
    if got >= 25:
        break
    t = pdf.get_fulltext(p["id"], p["pdf_url"])
    if t:
        p["pdf_path"] = str(pdf.text_path(p["id"]).relative_to(RAW.parent.parent))
        p["fulltext_chars"] = len(t)
        got += 1
with CORPUS.open("w", encoding="utf-8") as f:
    for p in papers:
        f.write(json.dumps(p, ensure_ascii=False) + "\n")
print(f"classic full texts added: {got} (of {len(cands)} OA candidates)")
