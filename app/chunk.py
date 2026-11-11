"""Section-aware chunking.

Fixed-size chunking cuts price tables in half and separates a heading from the
paragraph that explains it. On a seven-page corpus we can afford to be careful,
so the splitter works in this order:

1. Split the markdown on headings, so every chunk belongs to one named section.
2. Inside a section, pack whole paragraphs up to a target size.
3. Never split a markdown table; a table is always one chunk.
4. Carry a small overlap between consecutive chunks of the same section so a
   sentence that straddles the boundary is still retrievable.

Each chunk also stores a short header ("Page: ... | Section: ...") that is
prepended for embedding only. The header is not shown to the model as evidence,
because it is not page content.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, asdict

TARGET_CHARS = 900
MAX_CHARS = 1400
OVERLAP_CHARS = 150

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


@dataclass
class Chunk:
    id: str
    url: str
    page_title: str
    page_type: str
    section: str
    text: str
    ordinal: int

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def embed_text(self) -> str:
        return f"{self.page_title} | {self.section}\n{self.text}"


def _split_sections(markdown: str) -> list[tuple[str, str]]:
    """Return [(section_title, section_body)] preserving document order."""
    sections: list[tuple[str, list[str]]] = [("Overview", [])]
    for line in markdown.splitlines():
        match = HEADING_RE.match(line.strip())
        if match:
            title = match.group(2).strip()
            # Ignore decorative headings that carry no information.
            if title and len(title) < 120:
                sections.append((title, []))
                continue
        sections[-1][1].append(line)
    return [(title, "\n".join(body).strip()) for title, body in sections if "\n".join(body).strip()]


def _is_table(block: str) -> bool:
    lines = [ln for ln in block.splitlines() if ln.strip()]
    return bool(lines) and all(ln.strip().startswith("|") for ln in lines)


def _pack(paragraphs: list[str]) -> list[str]:
    """Greedily pack paragraphs into chunks of roughly TARGET_CHARS."""
    chunks: list[str] = []
    current: list[str] = []
    size = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # A table is atomic: flush what we have, then emit the table alone.
        if _is_table(para):
            if current:
                chunks.append("\n\n".join(current))
                current, size = [], 0
            chunks.append(para)
            continue

        # A single oversized paragraph is split on sentence boundaries first,
        # then on line breaks, because some pages (the video listing) are one
        # long block of newline-separated titles with no sentence punctuation.
        if len(para) > MAX_CHARS:
            if current:
                chunks.append("\n\n".join(current))
                current, size = [], 0
            units: list[str] = []
            for sentence in re.split(r"(?<=[.!?])\s+", para):
                if len(sentence) > MAX_CHARS:
                    units.extend(ln for ln in sentence.splitlines() if ln.strip())
                else:
                    units.append(sentence)
            # Last resort: a single line longer than MAX_CHARS (some pages ship
            # one unwrapped block) is cut on character count.
            hard: list[str] = []
            for unit in units:
                while len(unit) > MAX_CHARS:
                    hard.append(unit[:MAX_CHARS])
                    unit = unit[MAX_CHARS - OVERLAP_CHARS :]
                if unit.strip():
                    hard.append(unit)
            units = hard
            buffer = ""
            for unit in units:
                if len(buffer) + len(unit) + 1 > TARGET_CHARS and buffer:
                    chunks.append(buffer.strip())
                    buffer = buffer[-OVERLAP_CHARS:] + " " + unit
                else:
                    buffer = f"{buffer} {unit}".strip()
            if buffer.strip():
                chunks.append(buffer.strip())
            continue

        if size + len(para) > TARGET_CHARS and current:
            chunks.append("\n\n".join(current))
            tail = "\n\n".join(current)[-OVERLAP_CHARS:]
            current = [tail, para]
            size = len(tail) + len(para)
        else:
            current.append(para)
            size += len(para)

    if current:
        chunks.append("\n\n".join(current))
    return [c for c in chunks if len(c.strip()) > 40]


def chunk_page(
    *,
    url: str,
    page_title: str,
    page_type: str,
    text: str,
    faqs: list[tuple[str, str]] | None = None,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    ordinal = 0

    def emit(section: str, piece: str) -> None:
        nonlocal ordinal
        digest = hashlib.sha1(f"{url}|{section}|{ordinal}|{piece[:80]}".encode()).hexdigest()[:12]
        chunks.append(
            Chunk(
                id=f"{page_type[:3].lower()}-{digest}",
                url=url,
                page_title=page_title,
                page_type=page_type,
                section=section,
                text=piece.strip(),
                ordinal=ordinal,
            )
        )
        ordinal += 1

    # Some pages (the video listing) are a run of headings whose body is a
    # single word. There the heading *is* the content, so short sections are
    # collected into one list chunk instead of being dropped as noise.
    pending: list[str] = []
    pending_size = 0
    pending_section = ""

    def flush_pending() -> None:
        nonlocal pending, pending_size, pending_section
        if pending:
            emit(pending_section or "List", "\n".join(pending))
            pending, pending_size, pending_section = [], 0, ""

    for section, body in _split_sections(text):
        if len(body) < 60:
            line = f"- {section}" + (f": {body}" if body else "")
            if not pending:
                pending_section = section
            pending.append(line)
            pending_size += len(line)
            if pending_size >= TARGET_CHARS:
                flush_pending()
            continue

        flush_pending()
        for piece in _pack(re.split(r"\n\s*\n", body)):
            emit(section, piece)

    flush_pending()

    # FAQ pairs are already question-shaped, which makes them strong retrieval
    # targets for exactly the kind of question a visitor types.
    for question, answer in faqs or []:
        emit(f"FAQ: {question[:90]}", f"**Q: {question}**\n\n{answer}")

    return chunks
