"""Scheduled refresh of the knowledge base.

The seven pages are re-checked on a timer. Three rules make that safe to leave
running unattended:

  * nothing is rebuilt when no page changed, so a daily check costs seven HTTP
    requests and no embedding calls;
  * a new corpus is validated against the current one before it replaces it, so
    a broken extractor cannot quietly shrink the knowledge base;
  * only one refresh runs at a time, and the index is swapped in one step, so a
    visitor asking a question mid-refresh gets either the old corpus or the new
    one, never a mixture.

The sanity gate exists because of a real incident: trafilatura 2.0.0 extracted
the price-comparison page as 478 characters instead of 8,916, which silently
dropped 24 chunks and 22 price rows. Nothing failed. The bot simply stopped
knowing things it used to know.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from .config import settings
from .fetch import fetch_all
from .ingest import build, write_corpus
from .sources import SOURCES
from .store import store

log = logging.getLogger("refresh")

# A page that extracts to fewer characters than this is treated as a failed
# extraction, not as a page that genuinely got shorter. The smallest real page
# in this corpus is the video list at roughly 1.2k characters.
MIN_PAGE_CHARS = 400

# A single page that loses more than half its text is a broken extractor, not an
# edit. This is the check that catches the trafilatura regression, where the
# price-comparison page went from 8,916 characters to 478.
MAX_PAGE_DROP = 0.50

# A rebuild that loses more than this share of the whole corpus is rejected.
MAX_SHRINK = 0.10

_lock = threading.Lock()


class RefreshBusy(RuntimeError):
    """Another refresh is already running."""


class RefreshRejected(RuntimeError):
    """The new corpus failed the sanity gate; the old one is still live."""


@dataclass
class Outcome:
    ok: bool
    changed: bool
    reason: str | None = None
    pages: int = 0
    chunks: int = 0
    prices: int = 0
    changed_pages: list[str] = field(default_factory=list)
    seconds: float = 0.0
    checked_at: str = ""
    built_at: str | None = None
    diff: dict | None = None

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "changed": self.changed,
            "reason": self.reason,
            "pages": self.pages,
            "chunks": self.chunks,
            "prices": self.prices,
            "changed_pages": self.changed_pages,
            "seconds": self.seconds,
            "checked_at": self.checked_at,
            "built_at": self.built_at,
            "diff": self.diff,
        }


# -- state file ----------------------------------------------------------


def _state_path() -> Path:
    return settings.refresh_state_path


def load_state() -> dict:
    path = _state_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        log.warning("could not read %s; starting from empty state", path)
        return {}


def _save_state(state: dict) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(state, indent=1), encoding="utf-8")
        os.replace(tmp, path)
    except OSError as exc:
        log.warning("could not write refresh state: %s", exc)


# -- sanity gate ---------------------------------------------------------


def check_corpus(new: dict, old: dict | None) -> str | None:
    """Return a reason to reject the new corpus, or None to accept it.

    The thresholds are deliberately loose. They are not there to police small
    edits to the pages; they are there to catch an extractor that has stopped
    working, which shows up as a page collapsing to a few hundred characters.
    """
    page_count = new.get("page_count", 0)
    if page_count < len(SOURCES):
        return f"only {page_count} of {len(SOURCES)} pages extracted"

    for page in new.get("pages", []):
        chars = page.get("chars", 0)
        if chars < MIN_PAGE_CHARS:
            return f"{page.get('slug', '?')} extracted to {chars} characters (minimum {MIN_PAGE_CHARS})"

    if not old:
        return None

    # Per page: a page that lost more than half its text is a broken extractor,
    # not an edit. This is the check that catches the trafilatura regression.
    previous = {p.get("slug"): p.get("chars", 0) for p in old.get("pages", [])}
    for page in new.get("pages", []):
        slug = page.get("slug")
        before = previous.get(slug, 0)
        after = page.get("chars", 0)
        if before and after < before * (1 - MAX_PAGE_DROP):
            return f"{slug} fell from {before} to {after} characters"

    # A page that used to list prices and now lists none has lost its table,
    # which is the failure that matters most on a site whose main question is
    # "how much does it cost".
    previous_prices = {p.get("slug"): p.get("prices", 0) for p in old.get("pages", [])}
    for page in new.get("pages", []):
        slug = page.get("slug")
        before = previous_prices.get(slug, 0)
        after = page.get("prices", 0)
        if before and not after:
            return f"{slug} lost all {before} price rows"

    old_chunks = old.get("chunk_count", 0)
    new_chunks = new.get("chunk_count", 0)
    if old_chunks and new_chunks < old_chunks * (1 - MAX_SHRINK):
        return f"chunk count fell from {old_chunks} to {new_chunks}"

    old_prices = len(old.get("prices", []))
    new_prices = len(new.get("prices", []))
    if old_prices and new_prices < old_prices * (1 - MAX_SHRINK):
        return f"price rows fell from {old_prices} to {new_prices}"

    return None


# -- the change report ---------------------------------------------------


def _price_key(row: dict) -> tuple[str, str]:
    return (row.get("source_url", ""), (row.get("treatment") or "").strip().lower())


def diff_corpora(old: dict, new: dict) -> dict:
    """What actually changed between two builds.

    A page slug in a log line says a page moved. It does not say that the
    adenocarcinoma package went from 18,995 to 19,995, which is the only change
    anyone running this site cares about.
    """
    old_prices = {_price_key(r): r for r in old.get("prices", [])}
    new_prices = {_price_key(r): r for r in new.get("prices", [])}

    moved = [
        {
            "treatment": new_prices[key].get("treatment") or "Treatment",
            "from": old_prices[key].get("amount"),
            "to": new_prices[key].get("amount"),
            "currency": new_prices[key].get("currency", "USD"),
        }
        for key in old_prices.keys() & new_prices.keys()
        if old_prices[key].get("amount") != new_prices[key].get("amount")
    ]

    old_chunks = {c.get("id") for c in old.get("chunks", [])}
    new_chunks = {c.get("id") for c in new.get("chunks", [])}

    return {
        "prices_added": len(new_prices.keys() - old_prices.keys()),
        "prices_removed": len(old_prices.keys() - new_prices.keys()),
        "prices_moved": moved[:20],
        "chunks_added": len(new_chunks - old_chunks),
        "chunks_removed": len(old_chunks - new_chunks),
    }


# -- the refresh ---------------------------------------------------------


def run(force: bool = False) -> Outcome:
    """Re-check the seven pages and rebuild only if something changed.

    Raises RefreshBusy when another run holds the lock, and RefreshRejected when
    the new corpus fails the sanity gate. In both cases the live index is
    untouched.
    """
    if not _lock.acquire(blocking=False):
        raise RefreshBusy("a refresh is already running")

    started = time.monotonic()
    checked_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    state = load_state()

    try:
        fetched = fetch_all()
        new_corpus = build(offline=False, write=False, fetched=fetched)

        # Compare the extracted text, not the raw HTML. The live pages carry
        # per-request nonces and rotating widgets, so their bytes differ on
        # every fetch even when the article is identical.
        previous = {p.get("slug"): p.get("text_sha256") for p in store.corpus.get("pages", [])}
        changed_pages = [
            page["slug"]
            for page in new_corpus["pages"]
            if previous.get(page["slug"]) != page.get("text_sha256")
        ]

        state["last_checked"] = checked_at
        state["pages"] = {
            page["slug"]: {
                "text_sha256": page.get("text_sha256"),
                "chars": page.get("chars", 0),
                "chunks": page.get("chunks", 0),
            }
            for page in new_corpus["pages"]
        }

        if not force and not changed_pages and store.ready:
            state["last_result"] = "unchanged"
            state["last_reason"] = None
            _save_state(state)
            log.info("refresh: no page changed; index left as is")
            return Outcome(
                ok=True,
                changed=False,
                pages=store.corpus.get("page_count", 0),
                chunks=len(store.chunks),
                prices=len(store.corpus.get("prices", [])),
                seconds=round(time.monotonic() - started, 1),
                checked_at=checked_at,
                built_at=store.corpus.get("built_at"),
            )

        reason = check_corpus(new_corpus, store.corpus)
        if reason and not force:
            state["last_result"] = "rejected"
            state["last_reason"] = reason
            _save_state(state)
            log.error("refresh rejected, old corpus kept: %s", reason)
            raise RefreshRejected(reason)

        diff = diff_corpora(store.corpus, new_corpus)
        write_corpus(new_corpus)
        store.reload()

        state["last_changed"] = checked_at
        state["last_result"] = "rebuilt"
        state["last_reason"] = None
        state["changed_pages"] = changed_pages
        state["built_at"] = new_corpus.get("built_at")
        state["last_diff"] = diff
        _save_state(state)

        log.info(
            "refresh: rebuilt %d chunks from %d pages (%s)",
            new_corpus["chunk_count"],
            new_corpus["page_count"],
            ", ".join(changed_pages) or "forced",
        )
        return Outcome(
            ok=True,
            changed=True,
            pages=new_corpus["page_count"],
            chunks=new_corpus["chunk_count"],
            prices=len(new_corpus["prices"]),
            changed_pages=changed_pages,
            seconds=round(time.monotonic() - started, 1),
            checked_at=checked_at,
            built_at=new_corpus.get("built_at"),
            diff=diff,
        )
    finally:
        _lock.release()


def status() -> dict:
    """What the last run did, for /api/health and the admin endpoint."""
    state = load_state()
    return {
        "last_checked": state.get("last_checked"),
        "last_changed": state.get("last_changed"),
        "last_result": state.get("last_result"),
        "last_reason": state.get("last_reason"),
        "changed_pages": state.get("changed_pages", []),
        "corpus_built_at": store.corpus.get("built_at"),
        "last_diff": state.get("last_diff"),
    }
