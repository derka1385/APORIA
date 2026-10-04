"""Open-access PDF download (polite) + text extraction with PyMuPDF. Files stay in data/raw/."""
from __future__ import annotations

import logging
import re
from pathlib import Path

import pymupdf

from crux_lab.config import RAW
from crux_lab.corpus import http

log = logging.getLogger(__name__)
PDF_DIR = RAW / "pdf"
TEXT_DIR = RAW / "text"
MAX_BYTES = 40 * 1024 * 1024


def safe_name(pid: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", pid)


def text_path(pid: str) -> Path:
    return TEXT_DIR / f"{safe_name(pid)}.txt"


def fetch_pdf(pid: str, url: str) -> Path | None:
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    out = PDF_DIR / f"{safe_name(pid)}.pdf"
    if out.exists() and out.stat().st_size > 1000:
        return out
    try:
        r = http.get(url, timeout=90, retries=2, accept="application/pdf")
    except Exception as e:  # noqa: BLE001
        log.info("pdf fail %s %s: %s", pid, url, str(e)[:120])
        return None
    body = r.content
    if not body.startswith(b"%PDF") or len(body) > MAX_BYTES:
        log.info("not a pdf (or too big) %s %s ct=%s", pid, url, r.headers.get("content-type"))
        return None
    out.write_bytes(body)
    return out


def extract_text(pdf: Path) -> str:
    with pymupdf.open(pdf) as doc:
        pages = [p.get_text("text") for p in doc]
    text = "\n".join(pages)
    text = re.sub(r"-\n(?=[a-z])", "", text)        # de-hyphenate line breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def get_fulltext(pid: str, url: str, min_chars: int = 8000) -> str | None:
    tp = text_path(pid)
    if tp.exists():
        t = tp.read_text("utf-8")
        return t if len(t) >= min_chars else None
    pdf = fetch_pdf(pid, url)
    if not pdf:
        return None
    try:
        t = extract_text(pdf)
    except Exception as e:  # noqa: BLE001
        log.info("extract fail %s: %s", pid, e)
        return None
    TEXT_DIR.mkdir(parents=True, exist_ok=True)
    tp.write_text(t, "utf-8")
    return t if len(t) >= min_chars else None
