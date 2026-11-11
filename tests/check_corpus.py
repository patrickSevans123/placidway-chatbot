"""Sanity checks on the committed corpus, run in CI on every push.

`app/refresh.py` validates a *new* corpus against the live one. This checks the
corpus that is actually in the repository, from a cold start, with no network
and no model calls: the file a reviewer or a fresh container gets.

It is deliberately narrow. Each check here has caught or would have caught a
real failure: pages shrinking when an extractor regresses, prices losing their
currency, chunks disappearing, the allow-list drifting from the pages that were
actually ingested.

    python -m tests.check_corpus
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from app.sources import SOURCES

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "corpus.json"

MIN_PAGE_CHARS = 400
MAX_CHUNK_CHARS = 2600
MIN_CHUNKS = 100
MIN_PRICES = 40

problems: list[str] = []


def check(ok: bool, message: str) -> None:
    if not ok:
        problems.append(message)


def main() -> int:
    if not CORPUS.exists():
        print(f"FAIL: {CORPUS} does not exist")
        return 1

    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    allowed = {source.url for source in SOURCES}

    pages = corpus.get("pages", [])
    chunks = corpus.get("chunks", [])
    prices = corpus.get("prices", [])
    faqs = corpus.get("faqs", [])

    check(len(SOURCES) == 7, f"the allow-list has {len(SOURCES)} sources, expected 7")
    check(corpus.get("page_count") == len(pages) == len(SOURCES),
          f"page_count={corpus.get('page_count')} pages={len(pages)} sources={len(SOURCES)}")
    check(corpus.get("chunk_count") == len(chunks), "chunk_count does not match the chunk list")

    try:
        datetime.fromisoformat(corpus["built_at"].replace("Z", "+00:00"))
    except (KeyError, ValueError):
        problems.append("built_at is missing or not ISO 8601")

    for page in pages:
        slug = page.get("slug", "?")
        check(page.get("url") in allowed, f"{slug}: url is not one of the seven sources")
        check(page.get("chars", 0) >= MIN_PAGE_CHARS,
              f"{slug}: extracted to {page.get('chars')} characters, below {MIN_PAGE_CHARS}")
        check(bool(page.get("text_sha256")), f"{slug}: no text hash, so refresh cannot detect change")

    check(len({page.get("url") for page in pages}) == len(pages), "two pages share a url")
    check(len(chunks) >= MIN_CHUNKS, f"{len(chunks)} chunks, expected at least {MIN_CHUNKS}")
    check(len(prices) >= MIN_PRICES, f"{len(prices)} price rows, expected at least {MIN_PRICES}")

    for chunk in chunks:
        where = f"chunk {chunk.get('id', '?')}"
        check(chunk.get("url") in allowed, f"{where}: url is not one of the seven sources")
        check(bool((chunk.get("text") or "").strip()), f"{where}: empty text")
        check(len(chunk.get("text") or "") <= MAX_CHUNK_CHARS,
              f"{where}: {len(chunk.get('text') or '')} characters, over {MAX_CHUNK_CHARS}")

    for row in prices:
        where = f"price {row.get('treatment', '?')!r}"
        check(float(row.get("amount") or 0) > 0, f"{where}: amount is not positive")
        check(bool(row.get("currency")), f"{where}: no currency")
        check(row.get("source_url") in allowed, f"{where}: source_url is not one of the seven sources")
        check(bool(row.get("context")), f"{where}: no context, so the price is unqualified")

    for faq in faqs:
        check(bool((faq.get("question") or "").strip()), "an FAQ has no question")
        check(bool((faq.get("answer") or "").strip()), "an FAQ has no answer")
        check(faq.get("source_url") in allowed, "an FAQ points outside the seven sources")

    print(f"corpus      {CORPUS.name}")
    print(f"built_at    {corpus.get('built_at')}")
    print(f"pages       {len(pages)}  {', '.join(page.get('slug', '?') for page in pages)}")
    print(f"chunks      {len(chunks)}  longest {max((len(c.get('text') or '') for c in chunks), default=0)} chars")
    print(f"prices      {len(prices)}  currencies {sorted({r.get('currency') for r in prices})}")
    print(f"faqs        {len(faqs)}")

    if problems:
        print(f"\n{len(problems)} problem(s):")
        for problem in problems:
            print(f"  - {problem}")
        return 1

    print("\nok - corpus is intact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
