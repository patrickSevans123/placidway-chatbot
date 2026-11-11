"""Unit tests for retrieval and chunking.

These run against the built corpus, so they need `python -m app.ingest` to have
run at least once. They assert that a known question retrieves the right page,
which is the property that matters more than any single score.
"""

from __future__ import annotations

import pytest

from app.chunk import chunk_page
from app.retrieve import search
from app.store import store


pytestmark = pytest.mark.skipif(not store.ready, reason="corpus not built; run python -m app.ingest")


def _top_pages(query: str, k: int = 3) -> list[str]:
    result = search(query, top_k=k)
    return [hit.chunk["page_type"] for hit in result.hits]


def test_cost_question_reaches_a_price_page():
    pages = _top_pages("How much does adenocarcinoma treatment cost in Tijuana?")
    assert "Treatment package" in pages or "Price list" in pages


def test_inclusion_question_reaches_a_package():
    pages = _top_pages("What is included in the adrenal cancer package?")
    assert "Treatment package" in pages


def test_clinic_question_reaches_the_profile():
    pages = _top_pages("Where is the clinic and who are the doctors?")
    assert "Clinic profile" in pages


def test_out_of_scope_question_has_low_confidence():
    result = search("What is the weather in Cancun?")
    assert result.confidence < 0.35


def test_in_scope_question_has_high_confidence():
    result = search("How much does the adrenal cancer package cost?")
    assert result.confidence > 0.5


def test_every_chunk_carries_its_source():
    for chunk in store.chunks:
        assert chunk["url"].startswith("https://www.placidway.com/")
        assert chunk["page_title"]
        assert chunk["text"].strip()


def test_chunker_never_splits_a_table():
    markdown = (
        "## Prices\n\n"
        "| Procedure | Price |\n|---|---|\n| Breast Cancer | $18995 |\n| Lung Cancer | $18995 |\n\n"
        "## Notes\n\nSome notes about the clinic and how it works, long enough to be kept.\n"
    )
    chunks = chunk_page(url="https://example.com", page_title="T", page_type="Price list", text=markdown)
    table_chunks = [c for c in chunks if "| Breast Cancer |" in c.text]
    assert table_chunks
    assert "| Lung Cancer |" in table_chunks[0].text


def test_chunker_keeps_short_heading_sections():
    # The video page is a list of headings with one-word bodies.
    markdown = "\n\n".join(f"## Video title number {i}\n\nCancer Treatment" for i in range(40))
    chunks = chunk_page(url="https://example.com", page_title="V", page_type="Clinic videos", text=markdown)
    joined = " ".join(c.text for c in chunks)
    assert "Video title number 0" in joined
    assert "Video title number 39" in joined
