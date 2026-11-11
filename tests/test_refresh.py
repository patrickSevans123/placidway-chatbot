"""Tests for the scheduled refresh.

Three properties matter, and each one is a way the refresh could quietly damage
a working knowledge base:

  * the sanity gate rejects a corpus that lost a page, a chunk, or a price row;
  * a run where the extracted text did not change does not rebuild anything;
  * a rejected or concurrent run leaves the live corpus exactly as it was.
"""

from __future__ import annotations

import pytest

from app import refresh
from app.fetch import FetchedPage
from app.sources import SOURCES


# -- fixtures ------------------------------------------------------------


def _page(slug: str = "price-list", chars: int = 5000, text_hash: str | None = None) -> dict:
    return {
        "slug": slug,
        "url": f"https://www.placidway.com/{slug}",
        "title": slug,
        "page_type": "Price list",
        "summary": "",
        "sha256": "0" * 64,
        "text_sha256": text_hash or f"hash-{slug}",
        "chars": chars,
        "chunks": 20,
        "prices": 10,
        "faqs": 0,
    }


def _corpus(pages: int = 7, chars: int = 5000, chunks: int = 183, prices: int = 69) -> dict:
    return {
        "built_at": "2026-01-01T00:00:00Z",
        "page_count": pages,
        "chunk_count": chunks,
        "pages": [_page(f"page-{i}", chars) for i in range(pages)],
        "chunks": [],
        "prices": [{} for _ in range(prices)],
        "faqs": [],
    }


def _fetched() -> list[FetchedPage]:
    return [
        FetchedPage(
            source=source,
            html="<html></html>",
            status=200,
            sha256="a" * 64,
            fetched_at="2026-01-01T00:00:00Z",
        )
        for source in SOURCES
    ]


# -- the sanity gate -----------------------------------------------------


def test_gate_accepts_a_healthy_corpus():
    assert refresh.check_corpus(_corpus(), _corpus()) is None


def test_gate_accepts_a_corpus_with_no_previous_build():
    assert refresh.check_corpus(_corpus(), None) is None


def test_gate_rejects_a_page_that_collapsed():
    # The real incident: the price-comparison page went from 8,916 characters
    # to 478 when trafilatura was pinned to 2.0.0.
    old = _corpus()
    old["pages"][3]["chars"] = 8916
    new = _corpus()
    new["pages"][3]["chars"] = 478
    reason = refresh.check_corpus(new, old)
    assert reason is not None
    assert "8916" in reason
    assert "478" in reason


def test_gate_rejects_a_page_below_the_absolute_floor():
    new = _corpus()
    new["pages"][0]["chars"] = 120
    reason = refresh.check_corpus(new, None)
    assert reason is not None
    assert "120" in reason


def test_gate_rejects_a_missing_page():
    reason = refresh.check_corpus(_corpus(pages=6), _corpus())
    assert reason is not None
    assert "6 of 7" in reason


def test_gate_rejects_a_chunk_collapse():
    reason = refresh.check_corpus(_corpus(chunks=159), _corpus(chunks=183))
    assert reason is not None
    assert "183" in reason


def test_gate_rejects_a_price_collapse():
    reason = refresh.check_corpus(_corpus(prices=47), _corpus(prices=69))
    assert reason is not None
    assert "69" in reason


def test_gate_allows_a_small_shrink():
    # 183 -> 175 is a 4.4% drop, inside the 10% tolerance.
    assert refresh.check_corpus(_corpus(chunks=175), _corpus(chunks=183)) is None


# -- the run -------------------------------------------------------------


needs_corpus = pytest.mark.skipif(not refresh.store.ready, reason="corpus not built; run python -m app.ingest")


@needs_corpus
def test_run_skips_the_rebuild_when_the_text_is_identical(monkeypatch, tmp_path):
    monkeypatch.setattr(refresh, "fetch_all", lambda: _fetched())
    monkeypatch.setattr(refresh, "_state_path", lambda: tmp_path / "refresh_state.json")
    # The build returns exactly what is already live, so no page changed.
    monkeypatch.setattr(refresh, "build", lambda **kwargs: refresh.store.corpus)

    def no_write(corpus):
        raise AssertionError("an unchanged corpus must not be written")

    monkeypatch.setattr(refresh, "write_corpus", no_write)

    outcome = refresh.run()
    assert outcome.ok is True
    assert outcome.changed is False
    assert outcome.chunks == len(refresh.store.chunks)


@needs_corpus
def test_run_passes_the_fetched_pages_to_build(monkeypatch, tmp_path):
    pages = _fetched()
    monkeypatch.setattr(refresh, "fetch_all", lambda: pages)
    monkeypatch.setattr(refresh, "_state_path", lambda: tmp_path / "refresh_state.json")

    seen: dict = {}

    def fake_build(**kwargs):
        seen.update(kwargs)
        return _corpus()

    monkeypatch.setattr(refresh, "build", fake_build)
    monkeypatch.setattr(refresh, "write_corpus", lambda corpus: None)
    monkeypatch.setattr(refresh.store, "reload", lambda: None)

    refresh.run()
    # The pages are downloaded once, not twice.
    assert seen["fetched"] is pages
    assert seen["write"] is False


@needs_corpus
def test_run_keeps_the_old_corpus_when_the_gate_rejects(monkeypatch, tmp_path):
    monkeypatch.setattr(refresh, "fetch_all", lambda: _fetched())
    monkeypatch.setattr(refresh, "_state_path", lambda: tmp_path / "refresh_state.json")

    broken = _corpus()
    broken["pages"][0]["chars"] = 100
    monkeypatch.setattr(refresh, "build", lambda **kwargs: broken)

    def no_write(corpus):
        raise AssertionError("a rejected corpus must not be written")

    monkeypatch.setattr(refresh, "write_corpus", no_write)

    before = refresh.store.corpus.get("built_at")
    with pytest.raises(refresh.RefreshRejected):
        refresh.run()
    assert refresh.store.corpus.get("built_at") == before


@needs_corpus
def test_run_refuses_a_second_concurrent_refresh(monkeypatch, tmp_path):
    monkeypatch.setattr(refresh, "_state_path", lambda: tmp_path / "refresh_state.json")

    assert refresh._lock.acquire(blocking=False)
    try:
        with pytest.raises(refresh.RefreshBusy):
            refresh.run()
    finally:
        refresh._lock.release()


@needs_corpus
def test_run_records_the_check_time(monkeypatch, tmp_path):
    state_file = tmp_path / "refresh_state.json"
    monkeypatch.setattr(refresh, "fetch_all", lambda: _fetched())
    monkeypatch.setattr(refresh, "_state_path", lambda: state_file)
    monkeypatch.setattr(refresh, "build", lambda **kwargs: refresh.store.corpus)

    refresh.run()
    state = refresh.load_state()
    assert state["last_checked"]
    assert state["last_result"] == "unchanged"
    assert len(state["pages"]) == len(SOURCES)
