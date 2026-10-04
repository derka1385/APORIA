"""Extractor: chunked claim extraction with verbatim-quote verification, argument reconstruction,
and abstract-level claims for the whole corpus."""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field

from pydantic import BaseModel, Field
from rapidfuzz import fuzz

from crux_lab.agents.roles import render
from crux_lab.graph.schema import Argument, Claim, ClaimKind
from crux_lab.llm.client import LLMClient

log = logging.getLogger(__name__)
QUOTE_THRESHOLD = 90
CHUNK = 14000
OVERLAP = 600
MAX_CHUNKS = 8


class XClaim(BaseModel):
    kind: ClaimKind
    text: str
    quote: str


class ChunkOut(BaseModel):
    claims: list[XClaim] = Field(default_factory=list)


class AbstractClaims(BaseModel):
    paper_id: str
    claims: list[XClaim] = Field(default_factory=list)


class AbstractBatch(BaseModel):
    papers: list[AbstractClaims] = Field(default_factory=list)


class XArgument(BaseModel):
    title: str
    premise_ids: list[str]
    conclusion_id: str
    summary: str = ""


class ArgumentsOut(BaseModel):
    arguments: list[XArgument]


@dataclass
class ExtractStats:
    proposed: int = 0
    kept: int = 0
    dropped: list[dict] = field(default_factory=list)

    @property
    def drop_rate(self) -> float:
        return 0.0 if not self.proposed else 1 - self.kept / self.proposed


def short_id(paper_id: str) -> str:
    return paper_id.split(":", 1)[-1]


def normalize(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    s = s.replace("–", "-").replace("—", "-").replace("­", "")
    s = re.sub(r"-\s*\n\s*", "", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def quote_found(quote: str, source: str, threshold: int = QUOTE_THRESHOLD) -> bool:
    q, src = normalize(quote), normalize(source)
    if len(q) < 15:
        return False
    if q in src:
        return True
    return fuzz.partial_ratio(q, src) >= threshold


def sentence_count(quote: str) -> int:
    return len([s for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\"'(])", quote.strip()) if s])


def strip_references(text: str) -> str:
    cut = len(text)
    for m in re.finditer(r"\n\s*(References|REFERENCES|Bibliography|BIBLIOGRAPHY|Works Cited)\s*\n", text):
        if m.start() > len(text) * 0.55:
            cut = min(cut, m.start())
    return text[:cut]


def chunk_text(text: str, size: int = CHUNK, overlap: int = OVERLAP, max_chunks: int = MAX_CHUNKS) -> list[str]:
    text = strip_references(text)
    chunks, i = [], 0
    while i < len(text) and len(chunks) < max_chunks:
        end = min(len(text), i + size)
        if end < len(text):
            para = text.rfind("\n\n", i + size // 2, end)
            end = para if para > 0 else end
        chunks.append(text[i:end])
        i = max(end - overlap, i + 1)
    return chunks


async def extract_paper_claims(client: LLMClient, paper_id: str, title: str, text: str,
                               stats: ExtractStats, max_claims: int = 14) -> list[Claim]:
    chunks = chunk_text(text)
    sid = short_id(paper_id)

    async def one(i, ch):
        system, user = render("extractor", title=title, chunk=ch, chunk_no=i + 1,
                              n_chunks=len(chunks), max_claims=max_claims)
        obj, _ = await client.json("extractor", user, ChunkOut, system, max_tokens=4000)
        return i, ch, obj

    results = await asyncio.gather(*[one(i, ch) for i, ch in enumerate(chunks)])
    claims: list[Claim] = []
    seen_text: set[str] = set()
    n = 0
    for i, ch, obj in sorted(results, key=lambda r: r[0]):
        if not obj:
            continue
        for xc in obj.claims:
            stats.proposed += 1
            ok = quote_found(xc.quote, ch) and sentence_count(xc.quote) <= 2
            if not ok:
                stats.dropped.append({"paper_id": paper_id, "quote": xc.quote[:200], "reason": "quote not found"
                                      if not quote_found(xc.quote, ch) else "quote > 2 sentences"})
                continue
            key = normalize(xc.text)
            if key in seen_text:
                continue
            seen_text.add(key)
            n += 1
            stats.kept += 1
            claims.append(Claim(id=f"{sid}.c{n:03d}", paper_id=paper_id, kind=xc.kind, text=xc.text,
                                quote=xc.quote.strip(), level="fulltext"))
    return claims


def _validate_args(claim_ids: set[str]):
    def check(out: ArgumentsOut) -> str | None:
        if not out.arguments:
            return "give at least one argument"
        for a in out.arguments:
            bad = [x for x in a.premise_ids + [a.conclusion_id] if x not in claim_ids]
            if bad:
                return f"unknown claim ids {bad}; use only ids from the list"
            if not 2 <= len(a.premise_ids) <= 6:
                return f"argument '{a.title}' needs 2 to 6 premises, has {len(a.premise_ids)}"
            if a.conclusion_id in a.premise_ids:
                return "the conclusion cannot also be a premise"
        return None
    return check


async def reconstruct_arguments(client: LLMClient, paper_id: str, title: str, abstract: str,
                                claims: list[Claim]) -> list[Argument]:
    listing = "\n".join(f"{c.id}: [{c.kind}] {c.text}" for c in claims)
    system, user = render("argument", title=title, abstract=abstract[:2500], claims=listing)
    out, _ = await client.json("extractor", user, ArgumentsOut, system,
                               validate=_validate_args({c.id for c in claims}), max_tokens=3000)
    if not out:
        return []
    sid = short_id(paper_id)
    return [Argument(id=f"{sid}.arg{i + 1}", paper_id=paper_id, title=a.title,
                     premise_ids=list(dict.fromkeys(a.premise_ids)), conclusion_id=a.conclusion_id)
            for i, a in enumerate(out.arguments[:2])]


async def abstract_claims(client: LLMClient, papers: list[dict], stats: ExtractStats,
                          batch: int = 8) -> list[Claim]:
    groups = [papers[i:i + batch] for i in range(0, len(papers), batch)]

    async def one(group):
        text = "\n\n".join(f"paper_id: {p['id']}\nTitle: {p['title']}\nAbstract: {p['abstract'][:2000]}"
                           for p in group)
        system, user = render("abstract_claims", abstracts=text)
        obj, _ = await client.json("extractor", user, AbstractBatch, system, max_tokens=4000)
        return group, obj

    results = await asyncio.gather(*[one(g) for g in groups])
    out: list[Claim] = []
    for group, obj in results:
        if not obj:
            continue
        by_id = {p["id"]: p for p in group}
        for pc in obj.papers:
            p = by_id.get(pc.paper_id)
            if not p:
                continue
            for j, xc in enumerate(pc.claims[:3]):
                stats.proposed += 1
                if not quote_found(xc.quote, p["abstract"]) or sentence_count(xc.quote) > 2:
                    stats.dropped.append({"paper_id": p["id"], "quote": xc.quote[:200], "reason": "abstract quote"})
                    continue
                stats.kept += 1
                out.append(Claim(id=f"{short_id(p['id'])}.a{j + 1}", paper_id=p["id"], kind=xc.kind,
                                 text=xc.text, quote=xc.quote.strip(), level="abstract"))
    return out
