"""In-memory index over the corpus: BM25 plus optional dense vectors.

The corpus is small (a few hundred chunks), so everything lives in memory and
is rebuilt when the corpus file changes. No vector database, no server to run,
nothing to keep in sync.

Dense vectors are optional on purpose. If `fastembed` is not installed or the
model cannot be downloaded, the store falls back to BM25 alone and says so in
`/api/health`, rather than failing to start.
"""

from __future__ import annotations

import hashlib
import json
import math
import logging
import re
import threading
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from .config import settings

log = logging.getLogger(__name__)

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "can", "could", "did", "do",
    "does", "for", "from", "had", "has", "have", "how", "i", "if", "in", "into", "is", "it", "its",
    "me", "my", "of", "on", "or", "our", "so", "that", "the", "their", "them", "then", "there",
    "these", "they", "this", "to", "was", "we", "were", "what", "when", "where", "which", "who",
    "why", "will", "with", "would", "you", "your", "about", "any", "also", "just", "more", "most",
    "not", "only", "than", "very", "much", "many", "some", "such", "up", "out", "over", "under",
}

# Words a visitor uses that the pages may not. Expanding them at query time is
# cheaper and more predictable than hoping an embedding model bridges the gap.
SYNONYMS: dict[str, list[str]] = {
    "cost": ["price", "pricing", "fee", "how much"],
    "price": ["cost", "pricing", "fee"],
    "pricing": ["price", "cost"],
    "cheap": ["cost", "price", "affordable", "starting"],
    "expensive": ["cost", "price"],
    "fee": ["price", "cost"],
    "package": ["program", "treatment"],
    "program": ["package", "treatment"],
    "include": ["included", "inclusions", "covers"],
    "included": ["include", "inclusions", "covers"],
    "recovery": ["recover", "aftercare", "healing"],
    "duration": ["weeks", "long", "stay", "days"],
    "long": ["duration", "weeks", "days"],
    "safe": ["safety", "risk", "side effects"],
    "doctor": ["physician", "dr", "specialist"],
    "clinic": ["center", "centre", "hospital"],
    "center": ["clinic", "centre"],
    "location": ["address", "where", "tijuana"],
    "address": ["location", "where"],
    "contact": ["phone", "email", "quote", "request"],
    "book": ["booking", "appointment", "schedule"],
    "compare": ["comparison", "versus", "vs"],
    "video": ["videos", "testimonial", "story"],
    "testimonial": ["video", "story", "review"],
}

TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    tokens = TOKEN_RE.findall(text.lower())
    out: list[str] = []
    for token in tokens:
        if token in STOPWORDS or len(token) < 2:
            continue
        # Very light stemming: enough to match "prices"/"price", "included"/"include".
        if len(token) > 4 and token.endswith("ies"):
            token = token[:-3] + "y"
        elif len(token) > 4 and token.endswith("es") and not token.endswith("ses"):
            token = token[:-2]
        elif len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
            token = token[:-1]
        out.append(token)
    return out


def expand_query(query: str) -> str:
    """Append synonyms for any known term, so BM25 sees both vocabularies."""
    lowered = query.lower()
    extra: list[str] = []
    for term, alternatives in SYNONYMS.items():
        if re.search(rf"\b{re.escape(term)}\b", lowered):
            extra.extend(alternatives)
    return f"{query} {' '.join(extra)}" if extra else query


@dataclass
class Hit:
    chunk: dict
    score: float
    raw_score: float = 0.0
    bm25_rank: int | None = None
    dense_rank: int | None = None


class Store:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.corpus: dict = {}
        self.chunks: list[dict] = []
        self.bm25: BM25Okapi | None = None
        self.embeddings: np.ndarray | None = None
        self.idf: dict[str, float] = {}
        self.embedder = None
        self.dense_ready = False
        self.corpus_hash: str = ""
        self._load()

    # -- loading ---------------------------------------------------------
    def _load(self) -> None:
        path: Path = settings.corpus_path
        if not path.exists():
            log.warning("corpus not found at %s; run `python -m app.ingest`", path)
            return

        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest == self.corpus_hash:
            return

        corpus = json.loads(raw.decode("utf-8"))
        chunks = corpus.get("chunks", [])
        if not chunks:
            log.warning("corpus has no chunks")
            return

        tokenized = [tokenize(f"{c['page_title']} {c['section']} {c['text']}") for c in chunks]

        # Document frequency per token, used to weight query coverage by how
        # distinctive each word is. "cost" appears everywhere and says little;
        # "adenocarcinoma" appears on three pages and says a lot.
        df: dict[str, int] = {}
        for tokens in tokenized:
            for token in set(tokens):
                df[token] = df.get(token, 0) + 1
        total = max(1, len(chunks))
        idf = {token: math.log((total + 1) / (count + 1)) + 1.0 for token, count in df.items()}

        with self._lock:
            self.corpus = corpus
            self.chunks = chunks
            self.bm25 = BM25Okapi(tokenized)
            self.idf = idf
            self.corpus_hash = digest
            self.embeddings = None
            self.dense_ready = False

        log.info("loaded corpus: %d chunks from %d pages", len(chunks), corpus.get("page_count", 0))
        self._load_dense()

    def _load_dense(self) -> None:
        if not settings.use_dense:
            log.info("dense retrieval disabled by config")
            return
        try:
            from fastembed import TextEmbedding
        except ImportError:
            log.warning("fastembed not installed; BM25-only retrieval")
            return

        try:
            if self.embedder is None:
                self.embedder = TextEmbedding(model_name=settings.embedding_model)
        except Exception as exc:  # model download or onnx runtime failure
            log.warning("could not load embedding model (%s); BM25-only retrieval", exc)
            self.embedder = None
            return

        cache = settings.embeddings_path
        if cache.exists():
            try:
                vectors = np.load(cache)
                if vectors.shape[0] == len(self.chunks):
                    self.embeddings = vectors
                    self.dense_ready = True
                    log.info("loaded cached embeddings %s", vectors.shape)
                    return
            except Exception as exc:
                log.warning("could not read embedding cache (%s); recomputing", exc)

        try:
            texts = [f"{c['page_title']} | {c['section']}\n{c['text']}" for c in self.chunks]
            vectors = np.array(list(self.embedder.embed(texts)), dtype=np.float32)
            vectors /= np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-9
            np.save(cache, vectors)
            self.embeddings = vectors
            self.dense_ready = True
            log.info("built embeddings %s", vectors.shape)
        except Exception as exc:
            log.warning("embedding build failed (%s); BM25-only retrieval", exc)

    def reload(self) -> None:
        self.corpus_hash = ""
        self._load()

    # -- search ----------------------------------------------------------
    def bm25_search(self, query: str, k: int) -> list[tuple[int, float]]:
        if self.bm25 is None:
            return []
        tokens = tokenize(expand_query(query))
        if not tokens:
            return []
        scores = self.bm25.get_scores(tokens)
        order = np.argsort(scores)[::-1][:k]
        return [(int(i), float(scores[i])) for i in order if scores[i] > 0]

    def dense_search(self, query: str, k: int) -> list[tuple[int, float]]:
        if not self.dense_ready or self.embeddings is None or self.embedder is None:
            return []
        try:
            vector = np.array(list(self.embedder.query_embed([query]))[0], dtype=np.float32)
        except Exception as exc:
            log.warning("query embedding failed: %s", exc)
            return []
        vector /= np.linalg.norm(vector) + 1e-9
        scores = self.embeddings @ vector
        order = np.argsort(scores)[::-1][:k]
        return [(int(i), float(scores[i])) for i in order]

    def prices_for(self, url: str | None = None) -> list[dict]:
        rows = self.corpus.get("prices", [])
        if url is None:
            return rows
        return [r for r in rows if r["source_url"] == url]

    def page_for_url(self, url: str) -> dict | None:
        for page in self.corpus.get("pages", []):
            if page["url"] == url:
                return page
        return None

    @property
    def ready(self) -> bool:
        return bool(self.chunks)


store = Store()
