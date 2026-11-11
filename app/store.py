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
from dataclasses import dataclass, field, replace
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


@dataclass(frozen=True)
class Index:
    """One consistent view of the corpus.

    Everything a search needs lives here, so a reload builds a complete new
    index and swaps it in with a single assignment. A reader that takes
    ``store.snapshot`` once cannot end up with the chunk list from one build and
    the BM25 matrix from another.
    """

    corpus: dict = field(default_factory=dict)
    chunks: list[dict] = field(default_factory=list)
    bm25: BM25Okapi | None = None
    idf: dict[str, float] = field(default_factory=dict)
    embeddings: np.ndarray | None = None
    dense_ready: bool = False
    corpus_hash: str = ""


class Store:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._index = Index()
        self.embedder = None
        self._load()

    # -- reading ---------------------------------------------------------
    @property
    def snapshot(self) -> Index:
        """The current index. Read it once per request and use that object."""
        return self._index

    @property
    def corpus(self) -> dict:
        return self._index.corpus

    @property
    def chunks(self) -> list[dict]:
        return self._index.chunks

    @property
    def bm25(self) -> BM25Okapi | None:
        return self._index.bm25

    @property
    def idf(self) -> dict[str, float]:
        return self._index.idf

    @property
    def embeddings(self) -> np.ndarray | None:
        return self._index.embeddings

    @property
    def dense_ready(self) -> bool:
        return self._index.dense_ready

    @property
    def corpus_hash(self) -> str:
        return self._index.corpus_hash

    # -- loading ---------------------------------------------------------
    def _load(self) -> None:
        path: Path = settings.corpus_path
        if not path.exists():
            log.warning("corpus not found at %s; run `python -m app.ingest`", path)
            return

        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest == self._index.corpus_hash:
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

        # Build the whole index first, then publish it with one assignment.
        self._index = Index(
            corpus=corpus,
            chunks=chunks,
            bm25=BM25Okapi(tokenized),
            idf=idf,
            embeddings=None,
            dense_ready=False,
            corpus_hash=digest,
        )

        log.info("loaded corpus: %d chunks from %d pages", len(chunks), corpus.get("page_count", 0))
        self._load_dense()

    def _load_dense(self) -> None:
        if not settings.use_dense:
            log.info("dense retrieval disabled by config")
            return

        backend = settings.embedding_backend
        if backend == "none":
            log.info("dense retrieval disabled (EMBEDDING_BACKEND=none)")
            return

        index = self._index
        if not index.chunks:
            return

        cache = settings.embeddings_path
        if cache.exists():
            try:
                vectors = np.load(cache)
                if vectors.shape[0] == len(index.chunks):
                    self._index = replace(index, embeddings=vectors, dense_ready=True)
                    log.info("loaded cached embeddings %s", vectors.shape)
                    return
            except Exception as exc:
                log.warning("could not read embedding cache (%s); recomputing", exc)

        texts = [f"{c['page_title']} | {c['section']}\n{c['text']}" for c in index.chunks]

        if backend == "api":
            vectors = self._embed_api(texts)
        else:
            vectors = self._embed_local(texts)

        if vectors is None:
            log.warning("dense retrieval unavailable; BM25-only")
            return

        vectors = np.asarray(vectors, dtype=np.float32)
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-9
        try:
            np.save(cache, vectors)
        except OSError as exc:
            log.warning("could not cache embeddings: %s", exc)

        # Only publish if the corpus did not change while the vectors were
        # being built; otherwise the row order would not match the chunks.
        if self._index.corpus_hash == index.corpus_hash:
            self._index = replace(index, embeddings=vectors, dense_ready=True)
        log.info("built embeddings %s via %s", vectors.shape, backend)

    def _embed_api(self, texts: list[str]) -> np.ndarray | None:
        """Embed through the OpenAI-compatible /embeddings endpoint."""
        if not settings.llm_api_key:
            log.warning("no LLM_API_KEY; cannot build API embeddings")
            return None

        import httpx

        url = f"{settings.llm_base_url.rstrip('/')}/embeddings"
        headers = {
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        out: list[list[float]] = []
        batch = max(1, settings.embedding_batch)

        try:
            with httpx.Client(timeout=120.0) as client:
                for start in range(0, len(texts), batch):
                    chunk = texts[start : start + batch]
                    response = client.post(
                        url,
                        headers=headers,
                        json={"model": settings.embedding_model, "input": chunk},
                    )
                    if response.status_code >= 400:
                        log.warning("embedding API returned %s: %s", response.status_code, response.text[:200])
                        return None
                    payload = response.json()
                    data = sorted(payload.get("data", []), key=lambda d: d.get("index", 0))
                    out.extend(item["embedding"] for item in data)
        except Exception as exc:
            log.warning("embedding API failed: %s", exc)
            return None

        if len(out) != len(texts):
            log.warning("embedding count mismatch: %d vs %d", len(out), len(texts))
            return None
        return np.array(out, dtype=np.float32)

    def _embed_local(self, texts: list[str]) -> np.ndarray | None:
        """Embed with fastembed. Optional: only used when EMBEDDING_BACKEND=local."""
        try:
            from fastembed import TextEmbedding
        except ImportError:
            log.warning("fastembed not installed; install it or set EMBEDDING_BACKEND=api")
            return None

        try:
            if self.embedder is None:
                self.embedder = TextEmbedding(model_name=settings.embedding_model)
            return np.array(list(self.embedder.embed(texts)), dtype=np.float32)
        except Exception as exc:
            log.warning("local embedding failed (%s)", exc)
            return None

    def _embed_query(self, query: str) -> np.ndarray | None:
        if settings.embedding_backend == "api":
            vectors = self._embed_api([query])
            return vectors[0] if vectors is not None else None
        if self.embedder is None:
            return None
        try:
            return np.array(list(self.embedder.query_embed([query]))[0], dtype=np.float32)
        except Exception as exc:
            log.warning("query embedding failed: %s", exc)
            return None

    def reload(self) -> None:
        # Clearing the hash makes _load read the file again even when the bytes
        # are identical, which is what a caller asking for a reload expects.
        self._index = replace(self._index, corpus_hash="")
        self._load()

    # -- search ----------------------------------------------------------
    def bm25_search(self, query: str, k: int, index: Index | None = None) -> list[tuple[int, float]]:
        index = index or self._index
        if index.bm25 is None:
            return []
        tokens = tokenize(expand_query(query))
        if not tokens:
            return []
        scores = index.bm25.get_scores(tokens)
        order = np.argsort(scores)[::-1][:k]
        return [(int(i), float(scores[i])) for i in order if scores[i] > 0]

    def dense_search(self, query: str, k: int, index: Index | None = None) -> list[tuple[int, float]]:
        index = index or self._index
        if not index.dense_ready or index.embeddings is None:
            return []
        vector = self._embed_query(query)
        if vector is None:
            return []
        vector = vector.astype(np.float32)
        vector /= np.linalg.norm(vector) + 1e-9
        scores = index.embeddings @ vector
        order = np.argsort(scores)[::-1][:k]
        return [(int(i), float(scores[i])) for i in order]

    def prices_for(self, url: str | None = None) -> list[dict]:
        rows = self._index.corpus.get("prices", [])
        if url is None:
            return rows
        return [r for r in rows if r["source_url"] == url]

    def page_for_url(self, url: str) -> dict | None:
        for page in self._index.corpus.get("pages", []):
            if page["url"] == url:
                return page
        return None

    @property
    def ready(self) -> bool:
        return bool(self._index.chunks)


store = Store()
