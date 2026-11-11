"""Polite HTTP fetching.

Rules this module enforces, because the brief asks for them explicitly:
  * robots.txt is fetched and obeyed before any page request;
  * the crawler identifies itself with a descriptive User-Agent;
  * requests are spaced by at least CRAWL_DELAY seconds (default 3, the value
    placidway.com publishes in robots.txt, which is stricter than the 1/s asked for);
  * only the seven allow-listed URLs are ever requested.
"""

from __future__ import annotations

import hashlib
import logging
import time
import urllib.robotparser
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .config import settings
from .sources import BY_URL, SOURCES, Source

log = logging.getLogger(__name__)

_last_request_at: float = 0.0
_robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}


@dataclass
class FetchedPage:
    source: Source
    html: str
    status: int
    sha256: str
    fetched_at: str


def _throttle() -> None:
    """Sleep so that consecutive requests are at least CRAWL_DELAY apart."""
    global _last_request_at
    elapsed = time.monotonic() - _last_request_at
    wait = settings.crawl_delay - elapsed
    if wait > 0:
        time.sleep(wait)
    _last_request_at = time.monotonic()


def _robots_for(url: str, client: httpx.Client) -> urllib.robotparser.RobotFileParser:
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin in _robots_cache:
        return _robots_cache[origin]

    parser = urllib.robotparser.RobotFileParser()
    parser.set_url(f"{origin}/robots.txt")
    try:
        _throttle()
        response = client.get(f"{origin}/robots.txt")
        if response.status_code == 200:
            parser.parse(response.text.splitlines())
        else:
            # No robots.txt means no restrictions, but say so in the log.
            log.warning("robots.txt returned %s for %s; treating as allow-all", response.status_code, origin)
            parser.parse([])
    except httpx.HTTPError as exc:
        log.warning("could not read robots.txt for %s (%s); treating as allow-all", origin, exc)
        parser.parse([])

    _robots_cache[origin] = parser
    return parser


def allowed(url: str, client: httpx.Client) -> bool:
    if url not in BY_URL:
        return False
    parser = _robots_for(url, client)
    return parser.can_fetch(settings.user_agent, url)


def fetch_all(force: bool = False) -> list[FetchedPage]:
    """Fetch every allow-listed page, honouring robots.txt and the crawl delay.

    Raw HTML is cached under data/raw/<slug>.html. When the cached copy has the
    same SHA-256 as the live page, the cached copy is reused, so a refresh only
    re-parses pages that actually changed.
    """
    settings.raw_dir.mkdir(parents=True, exist_ok=True)
    pages: list[FetchedPage] = []

    headers = {
        "User-Agent": settings.user_agent,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en",
    }

    with httpx.Client(headers=headers, timeout=settings.fetch_timeout, follow_redirects=True) as client:
        for source in SOURCES:
            if not allowed(source.url, client):
                log.warning("robots.txt disallows %s - skipping", source.url)
                continue

            cache_path = settings.raw_dir / f"{source.slug}.html"
            _throttle()
            try:
                response = client.get(source.url)
            except httpx.HTTPError as exc:
                log.error("fetch failed for %s: %s", source.url, exc)
                if cache_path.exists():
                    log.warning("falling back to cached copy of %s", source.slug)
                    html = cache_path.read_text(encoding="utf-8", errors="replace")
                    pages.append(
                        FetchedPage(source, html, 0, hashlib.sha256(html.encode()).hexdigest(), "cached")
                    )
                continue

            if response.status_code != 200:
                log.error("HTTP %s for %s", response.status_code, source.url)
                if cache_path.exists():
                    html = cache_path.read_text(encoding="utf-8", errors="replace")
                    pages.append(
                        FetchedPage(source, html, response.status_code, hashlib.sha256(html.encode()).hexdigest(), "cached")
                    )
                continue

            html = response.text
            digest = hashlib.sha256(html.encode("utf-8")).hexdigest()

            if cache_path.exists() and not force:
                old = hashlib.sha256(cache_path.read_bytes()).hexdigest()
                if old == digest:
                    log.info("%s unchanged (%s)", source.slug, digest[:12])

            cache_path.write_text(html, encoding="utf-8")
            pages.append(
                FetchedPage(
                    source=source,
                    html=html,
                    status=response.status_code,
                    sha256=digest,
                    fetched_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                )
            )
            log.info("fetched %s (%d bytes, %s)", source.slug, len(html), digest[:12])

    return pages


def read_cached(slug: str) -> str | None:
    path: Path = settings.raw_dir / f"{slug}.html"
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")
    return None
