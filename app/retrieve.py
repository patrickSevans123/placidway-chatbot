"""Hybrid retrieval with reciprocal rank fusion.

BM25 is strong on this corpus because visitors use the same words as the pages
("price", "package", "included"). Dense vectors cover the paraphrases BM25
misses ("how expensive is it", "what do I get for the money"). Fusing the two
ranked lists with RRF needs no score calibration between them, which matters
because BM25 scores and cosine similarities are not comparable.

A small page-type prior is applied on top: a question about cost should prefer
the price list and the price comparison page, a question about the clinic should
prefer the profile. The prior is a tie-breaker, not a filter.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from .config import settings
from .store import Hit, store, tokenize

log = logging.getLogger(__name__)

RRF_K = 60

PAGE_PRIORS: dict[str, tuple[str, ...]] = {
    "Price list": ("price", "cost", "how much", "fee", "pricing", "usd", "dollar", "cheap", "expensive", "budget"),
    "Price comparison": ("compare", "cheaper", "versus", "vs", "average", "range", "abroad", "other countries"),
    "Clinic profile": ("clinic", "center", "centre", "doctor", "dr", "address", "location", "where", "accredit", "contact", "phone"),
    "Clinic videos": ("video", "testimonial", "story", "patient experience", "review"),
    "Treatment package": ("package", "included", "include", "program", "duration", "weeks", "recovery", "treatment"),
}

PRIOR_BOOST = 0.15

# The three packages share almost identical section names ("Key Takeaways",
# "Included in the Out-Patient Program"), so a question that names one cancer
# type must prefer chunks that actually mention it.
TREATMENT_TERMS = ("adenocarcinoma", "adrenal", "anal")


def _treatment_boost(query: str, text: str) -> float:
    lowered = query.lower()
    haystack = text.lower()
    for term in TREATMENT_TERMS:
        if re.search(rf"\b{term}\b", lowered) and term in haystack:
            return 0.06
    return 0.0


@dataclass
class RetrievalResult:
    hits: list[Hit]
    confidence: float
    used_dense: bool


def _prior_for(query: str, page_type: str) -> float:
    lowered = query.lower()
    keywords = PAGE_PRIORS.get(page_type, ())
    return PRIOR_BOOST if any(re.search(rf"\b{re.escape(k)}", lowered) for k in keywords) else 0.0


def _coverage(query: str, hits: list[Hit], idf: dict[str, float]) -> float:
    """IDF-weighted fraction of the query's content words present in the evidence.

    On a seven-page corpus this is the sharpest signal available for "is this
    question even about our content". Weighting by inverse document frequency
    stops common words from carrying a question: "cost" and "Mexico" appear on
    most pages, so a question about dental implants would otherwise look
    supported just because it mentions Mexico. "dental" and "implants" appear
    nowhere, and they are the words that decide it.
    """
    query_tokens = {t for t in tokenize(query) if len(t) >= 3}
    if not query_tokens:
        return 0.0

    evidence_tokens: set[str] = set()
    for hit in hits:
        evidence_tokens.update(tokenize(hit.chunk["text"]))

    def weight(token: str) -> float:
        return idf.get(token, 6.0)

    total = sum(weight(t) for t in query_tokens)
    if total <= 0:
        return 0.0
    found = sum(weight(t) for t in query_tokens if t in evidence_tokens)
    return found / total


def search(query: str, top_k: int | None = None) -> RetrievalResult:
    top_k = top_k or settings.top_k
    # One snapshot for the whole search, so a refresh landing mid-request
    # cannot hand us chunks from one build and a BM25 matrix from another.
    index = store.snapshot
    if not index.chunks:
        return RetrievalResult(hits=[], confidence=0.0, used_dense=False)

    bm25_hits = store.bm25_search(query, settings.candidate_k, index)
    dense_hits = store.dense_search(query, settings.candidate_k, index) if index.dense_ready else []

    fused: dict[int, Hit] = {}

    for rank, (idx, score) in enumerate(bm25_hits):
        fused[idx] = Hit(
            chunk=index.chunks[idx],
            score=1.0 / (RRF_K + rank + 1),
            raw_score=1.0 / (RRF_K + rank + 1),
            bm25_rank=rank,
        )

    for rank, (idx, score) in enumerate(dense_hits):
        contribution = 1.0 / (RRF_K + rank + 1)
        if idx in fused:
            fused[idx].score += contribution
            fused[idx].raw_score += contribution
            fused[idx].dense_rank = rank
        else:
            fused[idx] = Hit(
                chunk=index.chunks[idx],
                score=contribution,
                raw_score=contribution,
                dense_rank=rank,
            )

    for hit in fused.values():
        hit.score += _prior_for(query, hit.chunk["page_type"])
        hit.score += _treatment_boost(query, hit.chunk["text"])

    ranked = sorted(fused.values(), key=lambda h: h.score, reverse=True)[:top_k]

    # Confidence: how much of the question's vocabulary the evidence actually
    # contains, plus a small bonus when the dense model is also confident. The
    # page-type prior is deliberately excluded - it is a tie-breaker for
    # ordering, and letting it in would make an off-topic question that happens
    # to contain "cost" look well supported.
    coverage = _coverage(query, ranked, index.idf)
    top_cosine = 0.0
    if dense_hits:
        top_cosine = max(score for _, score in dense_hits)
    confidence = coverage + (0.15 if top_cosine >= 0.62 else 0.0)
    confidence = round(min(1.0, confidence), 4)

    return RetrievalResult(hits=ranked, confidence=confidence, used_dense=index.dense_ready)


def price_rows_for_query(query: str, limit: int = 12) -> list[dict]:
    """Return the price rows most relevant to a cost question.

    Prices are structured data, so they are looked up directly rather than
    retrieved as text. This is what keeps a cost answer exact: the model is
    handed the row, not a paragraph that happens to contain a number.
    """
    rows = store.snapshot.corpus.get("prices", [])
    if not rows:
        return []

    lowered = query.lower()
    scored: list[tuple[float, dict]] = []
    for row in rows:
        haystack = f"{row.get('treatment','')} {row.get('context','')}".lower()
        score = 0.0
        for token in set(re.findall(r"[a-z]{4,}", lowered)):
            if token in haystack:
                score += 1.0
        # Prefer rows that came from structured data over prose matches.
        score += {"json-ld": 0.5, "table": 0.4, "prose": 0.0}.get(row.get("origin", ""), 0.0)
        scored.append((score, row))

    scored.sort(key=lambda pair: pair[0], reverse=True)
    best = [row for score, row in scored if score > 0][:limit]
    return best or [row for _, row in scored[:limit]]
