"""PhilArchive OAI-PMH client: Identify, ListRecords (oai_dc, from/until, resumptionToken), GetRecord.

Base URL: CLAUDE.md names https://api.philpapers.org/oai.pl, which now answers data queries with
"Data queries only allowed with valid api key". PhilArchive's own Identify response advertises
https://philarchive.org/oai.pl as its baseURL, which serves ListRecords openly, so that is used
first and the api host is kept as a fallback. Raw XML pages are kept in data/raw/oai/.
"""
from __future__ import annotations

import hashlib
import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterator

from crux_lab.config import RAW
from crux_lab.corpus import http

log = logging.getLogger(__name__)
BASE_URLS = ["https://philarchive.org/oai.pl", "https://api.philpapers.org/oai.pl"]
NS = {"oai": "http://www.openarchives.org/OAI/2.0/", "dc": "http://purl.org/dc/elements/1.1/",
      "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/"}
RAW_OAI = RAW / "oai"


def _call(params: dict, base: str | None = None) -> str:
    # Tried 2026-10-04 with a PhilPapers API key (apiId/apiKey, the documented parameter names): the key is
    # accepted by api.philpapers.org but that host answers "Not found" for OAI verbs; PhilPapers' terms (§9)
    # name philarchive.org/oai.pl as the OAI channel, and it blocks automated clients (Cloudflare 403). The key
    # is therefore not sent here. Access needs PhilPapers to allow the harvester (they ask to be contacted).
    errors = []
    for b in ([base] if base else BASE_URLS):
        try:
            r = http.get(b, params=params, timeout=180)
            if "<OAI-PMH" not in r.text[:2000]:
                errors.append(f"{b}: non-OAI response {r.text[:120]!r}")
                continue
            return r.text
        except Exception as e:  # noqa: BLE001
            errors.append(f"{b}: {e}")
    raise RuntimeError("; ".join(errors))


def identify() -> str:
    return _call({"verb": "Identify"})


def parse_records(xml_text: str) -> tuple[list[dict], str | None]:
    root = ET.fromstring(xml_text.encode("utf-8"))
    err = root.find("oai:error", NS)
    if err is not None:
        if err.get("code") == "noRecordsMatch":
            return [], None
        raise RuntimeError(f"OAI error {err.get('code')}: {err.text}")
    out = []
    for rec in root.iter(f"{{{NS['oai']}}}record"):
        h = rec.find("oai:header", NS)
        ident = h.findtext("oai:identifier", default="", namespaces=NS)
        datestamp = h.findtext("oai:datestamp", default="", namespaces=NS)
        deleted = h.get("status") == "deleted"
        dc = rec.find(".//oai_dc:dc", NS)
        f = lambda tag, dc=dc: [e.text.strip() for e in dc.findall(f"dc:{tag}", NS) if e.text] if dc is not None else []  # noqa: E731
        out.append({
            "oai_id": ident, "datestamp": datestamp, "deleted": deleted,
            "title": " ".join(f("title")), "creators": f("creator"), "subjects": f("subject"),
            "description": "\n".join(f("description")), "date": " ".join(f("date")),
            "identifiers": f("identifier"), "types": f("type"), "language": " ".join(f("language")),
        })
    tok = root.find(".//oai:resumptionToken", NS)
    token = tok.text.strip() if tok is not None and tok.text else None
    return out, token


def list_records(frm: str, until: str | None = None, max_pages: int = 200,
                 save_raw: bool = True) -> Iterator[dict]:
    RAW_OAI.mkdir(parents=True, exist_ok=True)
    params = {"verb": "ListRecords", "metadataPrefix": "oai_dc", "from": frm}
    if until:
        params["until"] = until
    page = 0
    while page < max_pages:
        key = hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()[:12]
        raw_path = RAW_OAI / f"list_{frm}_{page:04d}_{key}.xml"
        if raw_path.exists():
            text = raw_path.read_text("utf-8")
        else:
            text = _call(params)
            if save_raw:
                raw_path.write_text(text, "utf-8")
        recs, token = parse_records(text)
        log.info("OAI page %d: %d records, token=%s", page, len(recs), bool(token))
        yield from recs
        if not token:
            break
        params = {"verb": "ListRecords", "resumptionToken": token}
        page += 1


def get_record(oai_id: str) -> dict | None:
    text = _call({"verb": "GetRecord", "identifier": oai_id, "metadataPrefix": "oai_dc"})
    recs, _ = parse_records(text)
    return recs[0] if recs else None


def rec_id(oai_id: str) -> str:
    """oai:philarchive.org/rec/BRADR -> BRADR"""
    return oai_id.rsplit("/", 1)[-1]


def to_paper(r: dict) -> dict:
    rid = rec_id(r["oai_id"])
    url = next((i for i in r["identifiers"] if i.startswith("http")), f"https://philarchive.org/rec/{rid}")
    year = None
    for tok in r["date"].split():
        if tok[:4].isdigit():
            year = int(tok[:4])
            break
    return {
        "id": f"pa:{rid}", "source": "philarchive", "title": r["title"],
        "authors": r["creators"], "year": year, "abstract": r["description"],
        "url": url, "pdf_url": f"https://philarchive.org/archive/{rid}", "pdf_path": None,
        "deposited_at": r["datestamp"], "subjects": r["subjects"], "date_field": r["date"],
    }


def main_harvest(frm: str = "2026-08-01", out: Path | None = None) -> int:
    out = out or (RAW / "oai_records.jsonl")
    n = 0
    with out.open("w", encoding="utf-8") as f:
        for r in list_records(frm):
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            n += 1
    log.info("harvested %d OAI records since %s -> %s", n, frm, out)
    return n


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    main_harvest()
