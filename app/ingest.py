"""Build the knowledge base.

    python -m app.ingest            # fetch, extract, chunk, write data/corpus.json
    python -m app.ingest --offline  # rebuild from cached HTML, no network

The output is a single JSON file. Keeping the knowledge base as a plain file
means a refresh is atomic (write to a temp file, then rename), the diff between
two builds is readable, and the app has no database dependency for retrieval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path

from .chunk import chunk_page
from .config import settings
from .extract import extract_page
from .fetch import fetch_all, read_cached
from .sources import SOURCES

log = logging.getLogger("ingest")


def build(
    offline: bool = False,
    write: bool = True,
    fetched: list | None = None,
) -> dict:
    """Fetch, extract and chunk the seven pages.

    With ``write=False`` the corpus is returned but nothing on disk changes, so
    a caller can validate it before replacing a working knowledge base. Passing
    ``fetched`` reuses pages that were already downloaded, which stops a refresh
    from requesting every URL twice.
    """
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    if fetched is not None:
        pages_html = [(p.source, p.html, p.sha256) for p in fetched]
    elif offline:
        pages_html = []
        for source in SOURCES:
            html = read_cached(source.slug)
            if html is None:
                log.error("no cached HTML for %s; run without --offline first", source.slug)
                continue
            pages_html.append((source, html, "cached"))
    else:
        fetched = fetch_all()
        pages_html = [(p.source, p.html, p.sha256) for p in fetched]

    if not pages_html:
        raise SystemExit("nothing to ingest: no pages fetched and no cache available")

    page_records: list[dict] = []
    all_chunks: list[dict] = []
    all_prices: list[dict] = []
    all_faqs: list[dict] = []

    for source, html, digest in pages_html:
        extracted = extract_page(html, source.url, source.title)
        faq_pairs = [(f.question, f.answer) for f in extracted.faqs]

        chunks = chunk_page(
            url=source.url,
            page_title=extracted.title or source.title,
            page_type=source.page_type,
            text=extracted.text,
            faqs=faq_pairs,
        )

        page_records.append(
            {
                "slug": source.slug,
                "url": source.url,
                "title": extracted.title or source.title,
                "page_type": source.page_type,
                "summary": source.summary,
                "sha256": digest,
                # Hash of the extracted article text, not the raw HTML. The raw
                # pages carry per-request nonces, so their hash changes on every
                # fetch; this one only changes when the content does.
                "text_sha256": hashlib.sha256(extracted.text.encode("utf-8")).hexdigest(),
                "chars": len(extracted.text),
                "chunks": len(chunks),
                "prices": len(extracted.prices),
                "faqs": len(extracted.faqs),
            }
        )
        all_chunks.extend(c.to_dict() for c in chunks)
        all_prices.extend(
            {
                "treatment": p.treatment,
                "amount": p.amount,
                "currency": p.currency,
                "context": p.context,
                "source_url": p.source_url,
                "origin": p.origin,
            }
            for p in extracted.prices
        )
        all_faqs.extend(
            {"question": f.question, "answer": f.answer, "source_url": f.source_url} for f in extracted.faqs
        )

        log.info(
            "%-22s %5d chars  %3d chunks  %2d prices  %2d faqs",
            source.slug,
            len(extracted.text),
            len(chunks),
            len(extracted.prices),
            len(extracted.faqs),
        )

    corpus = {
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "page_count": len(page_records),
        "chunk_count": len(all_chunks),
        "pages": page_records,
        "chunks": all_chunks,
        "prices": all_prices,
        "faqs": all_faqs,
    }

    if write:
        write_corpus(corpus)

    return corpus


def write_corpus(corpus: dict) -> None:
    """Replace the corpus atomically, then drop the embedding cache.

    The write goes to a temp file and is renamed over the old one, so a reader
    never sees a half-written JSON file. The embedding cache is deleted because
    its row count is tied to the chunk count; the store rebuilds it lazily.
    """
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    tmp = settings.corpus_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(corpus, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, settings.corpus_path)

    if settings.embeddings_path.exists():
        settings.embeddings_path.unlink()

    log.info(
        "wrote %s: %d pages, %d chunks, %d price rows, %d faqs",
        settings.corpus_path,
        corpus["page_count"],
        corpus["chunk_count"],
        len(corpus["prices"]),
        len(corpus["faqs"]),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the PlacidWay knowledge base")
    parser.add_argument("--offline", action="store_true", help="rebuild from cached HTML only")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(message)s")
    corpus = build(offline=args.offline)

    if corpus["page_count"] < len(SOURCES):
        log.warning("only %d of %d pages ingested", corpus["page_count"], len(SOURCES))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
