"""Hybrid retrieval: BM25 + dense embeddings, over claims and over abstracts.

Embeddings: Databricks embedding endpoint if configured, else local sentence-transformers
(BAAI/bge-small-en-v1.5), else an LSA fallback (TF-IDF + SVD in numpy). The backend used is
recorded in every index file so results can say what they ran on.
"""
from __future__ import annotations

import json
import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from crux_lab.config import INDEX_DIR as _INDEX_DIR

log = logging.getLogger(__name__)
INDEX_DIR = _INDEX_DIR          # per topic (config.topic_paths)
_STOP = set("""a an the of to in and or is are was were be been being for on with as by that this
these those it its at from but not no can could would should may might must will shall do does did
has have had he she they we you i his her their our your them him us me my so if then than such
which who whom whose what when where why how all any some each every one two also more most other
into about over under between because while there here""".split())


def tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z][a-z\-']+", text.lower()) if w not in _STOP and len(w) > 2]


class Embedder:
    _local = None

    def __init__(self, backend: str = "auto"):
        self.backend = backend
        if backend == "auto":
            self.backend = "local" if self._try_local() else "lsa"
        self._lsa: tuple | None = None

    @classmethod
    def _try_local(cls) -> bool:
        if cls._local is not None:
            return cls._local is not False
        try:
            from sentence_transformers import SentenceTransformer

            cls._local = SentenceTransformer("BAAI/bge-small-en-v1.5")
            return True
        except Exception as e:  # noqa: BLE001
            log.warning("local embeddings unavailable (%s); using LSA fallback", e)
            cls._local = False
            return False

    @property
    def name(self) -> str:
        return "bge-small-en-v1.5 (local)" if self.backend == "local" else "lsa-tfidf-svd"

    def fit(self, corpus_texts: list[str]) -> None:
        if self.backend != "lsa":
            return
        vocab = Counter(t for txt in corpus_texts for t in set(tokenize(txt)))
        words = [w for w, c in vocab.items() if c >= 2][:20000]
        idx = {w: i for i, w in enumerate(words)}
        n = len(corpus_texts)
        idf = np.array([math.log((1 + n) / (1 + vocab[w])) + 1 for w in words])
        m = np.zeros((n, len(words)), dtype=np.float32)
        for r, txt in enumerate(corpus_texts):
            for w, c in Counter(tokenize(txt)).items():
                if w in idx:
                    m[r, idx[w]] = (1 + math.log(c)) * idf[idx[w]]
        k = min(256, min(m.shape) - 1) if min(m.shape) > 2 else 1
        _, _, vt = np.linalg.svd(m, full_matrices=False)
        self._lsa = (idx, idf, vt[:k])

    def encode(self, texts: list[str]) -> np.ndarray:
        if self.backend == "local":
            v = self._local.encode(texts, batch_size=64, normalize_embeddings=True,
                                   show_progress_bar=False)
            return np.asarray(v, dtype=np.float32)
        if self._lsa is None:
            self.fit(texts)
        idx, idf, comp = self._lsa
        m = np.zeros((len(texts), len(idx)), dtype=np.float32)
        for r, txt in enumerate(texts):
            for w, c in Counter(tokenize(txt)).items():
                if w in idx:
                    m[r, idx[w]] = (1 + math.log(c)) * idf[idx[w]]
        v = m @ comp.T
        norms = np.linalg.norm(v, axis=1, keepdims=True)
        return v / np.maximum(norms, 1e-9)


@dataclass
class Hit:
    id: str
    score: float
    text: str
    meta: dict = field(default_factory=dict)


class HybridIndex:
    """BM25 + cosine over one collection of (id, text, meta) docs."""

    def __init__(self, ids: list[str], texts: list[str], metas: list[dict] | None = None,
                 embedder: Embedder | None = None, vectors: np.ndarray | None = None):
        self.ids, self.texts = ids, texts
        self.metas = metas or [{} for _ in ids]
        self.embedder = embedder or Embedder()
        self.bm25 = BM25Okapi([tokenize(t) or ["_"] for t in texts]) if texts else None
        if vectors is None and texts:
            self.embedder.fit(texts)
            vectors = self.embedder.encode(texts)
        self.vectors = vectors

    def __len__(self) -> int:
        return len(self.ids)

    def bm25_search(self, query: str, k: int = 20) -> list[Hit]:
        if not self.bm25:
            return []
        s = self.bm25.get_scores(tokenize(query) or ["_"])
        order = np.argsort(-s)[:k]
        return [Hit(self.ids[i], float(s[i]), self.texts[i], self.metas[i]) for i in order if s[i] > 0]

    def dense_search(self, query: str, k: int = 20) -> list[Hit]:
        if self.vectors is None or not len(self.ids):
            return []
        q = self.embedder.encode([query])[0]
        s = self.vectors @ q
        order = np.argsort(-s)[:k]
        return [Hit(self.ids[i], float(s[i]), self.texts[i], self.metas[i]) for i in order]

    def search(self, query: str, k: int = 20, rrf_k: int = 60) -> list[Hit]:
        """Reciprocal-rank fusion of BM25 and dense results."""
        fused: dict[str, float] = {}
        best: dict[str, Hit] = {}
        for hits in (self.bm25_search(query, k * 2), self.dense_search(query, k * 2)):
            for rank, h in enumerate(hits):
                fused[h.id] = fused.get(h.id, 0) + 1 / (rrf_k + rank + 1)
                best.setdefault(h.id, h)
        order = sorted(fused, key=lambda i: -fused[i])[:k]
        return [Hit(i, fused[i], best[i].text, best[i].meta) for i in order]

    def cosine(self, a: str, b: str) -> float:
        v = self.embedder.encode([a, b])
        return float(v[0] @ v[1])

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.save(path.with_suffix(".npy"), self.vectors if self.vectors is not None else np.zeros((0, 1)))
        path.with_suffix(".json").write_text(json.dumps(
            {"ids": self.ids, "texts": self.texts, "metas": self.metas, "embedder": self.embedder.name}))

    @classmethod
    def load(cls, path: Path, embedder: Embedder | None = None) -> "HybridIndex":
        d = json.loads(path.with_suffix(".json").read_text())
        emb = embedder or Embedder()
        vecs = np.load(path.with_suffix(".npy"))
        if emb.backend == "lsa":
            emb.fit(d["texts"])
            vecs = emb.encode(d["texts"])
        return cls(d["ids"], d["texts"], d["metas"], embedder=emb, vectors=vecs)
