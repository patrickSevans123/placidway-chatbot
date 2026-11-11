"""Turn raw HTML into clean text, structured prices and FAQ pairs.

Three extraction paths run on the same document:

1. trafilatura pulls the main article text as markdown, which drops navigation,
   cookie banners, related-links rails and footers.
2. JSON-LD blocks are parsed for `Offer` nodes (price + currency) and `FAQPage`
   nodes (question + answer). These are the site's own machine-readable claims,
   so they are the most reliable price source on the page.
3. A regex pass over the cleaned text catches prices written in prose, such as
   "the outpatient program starts at $18,995", together with the sentence around
   them so the currency and the "starting from" qualifier survive.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field

import trafilatura
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

MONEY_RE = re.compile(r"(?:US\s*)?\$\s?(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{2})?")
CURRENCY_WORDS = {"USD", "US$", "dollars", "dollar"}


@dataclass
class PriceRow:
    treatment: str
    amount: float
    currency: str
    context: str
    source_url: str
    origin: str  # "json-ld" | "table" | "prose"


@dataclass
class FaqPair:
    question: str
    answer: str
    source_url: str


@dataclass
class ExtractedPage:
    url: str
    title: str
    text: str
    prices: list[PriceRow] = field(default_factory=list)
    faqs: list[FaqPair] = field(default_factory=list)
    tables: list[str] = field(default_factory=list)


def _clean_title(html: str, fallback: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
        # PlacidWay titles are "Page name | PlacidWay" or similar.
        return re.split(r"\s+[|\-–]\s+PlacidWay\s*$", title)[0].strip() or fallback
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(" ", strip=True)
    return fallback


def _jsonld_blocks(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    blocks: list[dict] = []
    for tag in soup.find_all("script", type="application/ld+json"):
        raw = tag.string or tag.get_text()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, list):
            blocks.extend(d for d in data if isinstance(d, dict))
        elif isinstance(data, dict):
            blocks.append(data)
    return blocks


def _walk(node, key: str):
    """Yield every value stored under `key` anywhere in a nested JSON-LD tree."""
    if isinstance(node, dict):
        for k, v in node.items():
            if k == key:
                yield v
            yield from _walk(v, key)
    elif isinstance(node, list):
        for item in node:
            yield from _walk(item, key)


def _prices_from_jsonld(blocks: list[dict], url: str) -> list[PriceRow]:
    rows: list[PriceRow] = []
    seen: set[tuple[float, str]] = set()

    for block in blocks:
        for offer in _walk(block, "offers"):
            offers = offer if isinstance(offer, list) else [offer]
            for item in offers:
                if not isinstance(item, dict):
                    continue
                price = item.get("price") or item.get("lowPrice")
                currency = item.get("priceCurrency") or "USD"
                if price is None:
                    continue
                try:
                    amount = float(str(price).replace(",", ""))
                except ValueError:
                    continue
                if amount <= 0:
                    continue
                key = (amount, currency)
                if key in seen:
                    continue
                seen.add(key)

                name = ""
                for candidate in ("name", "description"):
                    value = item.get(candidate)
                    if isinstance(value, str) and value.strip():
                        name = value.strip()
                        break
                if not name:
                    name = _first_name(block) or "Treatment package"

                rows.append(
                    PriceRow(
                        treatment=name[:160],
                        amount=amount,
                        currency=currency,
                        context="Listed as the package price in the page's structured data.",
                        source_url=url,
                        origin="json-ld",
                    )
                )
    return rows


def _first_name(block: dict) -> str:
    for key in ("name", "headline"):
        value = block.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _faqs_from_jsonld(blocks: list[dict], url: str) -> list[FaqPair]:
    pairs: list[FaqPair] = []
    seen: set[str] = set()
    for block in blocks:
        for entity in _walk(block, "mainEntity"):
            items = entity if isinstance(entity, list) else [entity]
            for item in items:
                if not isinstance(item, dict):
                    continue
                question = item.get("name")
                answer = item.get("acceptedAnswer")
                if isinstance(answer, dict):
                    answer = answer.get("text")
                if not isinstance(question, str) or not isinstance(answer, str):
                    continue
                question = question.strip()
                answer = re.sub(r"\s+", " ", answer).strip()
                if not question or not answer or question in seen:
                    continue
                seen.add(question)
                pairs.append(FaqPair(question=question, answer=answer, source_url=url))
    return pairs


def _tables_from_markdown(text: str) -> list[str]:
    """Collect contiguous markdown table blocks."""
    tables: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.strip().startswith("|"):
            current.append(line.rstrip())
        else:
            if len(current) >= 2:
                tables.append("\n".join(current))
            current = []
    if len(current) >= 2:
        tables.append("\n".join(current))
    return tables


def _prices_from_tables(tables: list[str], url: str) -> list[PriceRow]:
    rows: list[PriceRow] = []
    for table in tables:
        lines = [ln for ln in table.splitlines() if ln.strip().startswith("|")]
        if not lines:
            continue
        header = [c.strip() for c in lines[0].strip("|").split("|")]
        for line in lines[1:]:
            cells = [c.strip() for c in line.strip("|").split("|")]
            if not cells or set("".join(cells)) <= set("-: "):
                continue
            joined = " | ".join(cells)
            match = MONEY_RE.search(joined)
            if not match:
                continue
            amount = float(match.group(1).replace(",", ""))
            label = cells[0] if cells else "Treatment"
            detail = " | ".join(
                f"{header[i]}: {cells[i]}" for i in range(min(len(header), len(cells))) if i > 0 and cells[i]
            )
            rows.append(
                PriceRow(
                    treatment=label[:160],
                    amount=amount,
                    currency="USD",
                    context=f"From the price table on the page. {detail}"[:400],
                    source_url=url,
                    origin="table",
                )
            )
    return rows


def _prices_from_prose(text: str, url: str) -> list[PriceRow]:
    rows: list[PriceRow] = []
    seen: set[float] = set()
    for match in MONEY_RE.finditer(text):
        amount = float(match.group(1).replace(",", ""))
        if amount < 50 or amount in seen:
            continue
        seen.add(amount)
        start = max(0, match.start() - 220)
        end = min(len(text), match.end() + 220)
        context = re.sub(r"\s+", " ", text[start:end]).strip()
        rows.append(
            PriceRow(
                treatment="",
                amount=amount,
                currency="USD",
                context=context,
                source_url=url,
                origin="prose",
            )
        )
    return rows


def extract_page(html: str, url: str, fallback_title: str) -> ExtractedPage:
    text = trafilatura.extract(
        html,
        output_format="markdown",
        include_tables=True,
        include_links=False,
        include_comments=False,
        favor_recall=True,
        url=url,
    )

    # trafilatura occasionally returns only the headings of a page, or nothing
    # at all. A page that is 300 KB of HTML but yields under 1,500 characters of
    # text has not been extracted, it has been mangled, so fall back to a plain
    # body dump rather than silently shrinking the knowledge base.
    if not text or (len(text) < 1500 and len(html) > 50_000):
        log.warning(
            "trafilatura returned %d chars for a %d-byte page (%s); using fallback extraction",
            len(text or ""),
            len(html),
            url,
        )
        soup = BeautifulSoup(html, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
            tag.decompose()
        fallback = soup.get_text("\n", strip=True)
        if len(fallback) > len(text or ""):
            text = fallback

    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    blocks = _jsonld_blocks(html)
    tables = _tables_from_markdown(text)

    prices = _prices_from_jsonld(blocks, url)
    prices += _prices_from_tables(tables, url)
    prices += _prices_from_prose(text, url)

    # De-duplicate on (amount, origin) keeping the richest context.
    deduped: dict[tuple[float, str], PriceRow] = {}
    for row in prices:
        key = (row.amount, row.origin)
        if key not in deduped or len(row.context) > len(deduped[key].context):
            deduped[key] = row

    return ExtractedPage(
        url=url,
        title=_clean_title(html, fallback_title),
        text=text,
        prices=list(deduped.values()),
        faqs=_faqs_from_jsonld(blocks, url),
        tables=tables,
    )
