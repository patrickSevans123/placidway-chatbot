"""The answer pipeline.

    message
      -> analyse (language, intent, standalone query, asserted fact)
      -> route: refuse / answer from evidence
      -> retrieve (hybrid, with price rows for cost questions)
      -> generate (strict grounding prompt)
      -> verify (citations + numbers)
      -> regenerate once, then fall back to an honest refusal

Every step is visible in the response object, so the UI can show why an answer
was refused and the logs can show which step failed.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from . import guard
from .config import settings
from .intents import Analysis, analyse
from .llm import LLMError, chat
from .retrieve import price_rows_for_query, search
from .sources import SOURCES
from .store import store

log = logging.getLogger(__name__)

CONTACT_URL = "https://www.placidway.com/rfi/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center"
PROFILE_URL = SOURCES[0].url

SYSTEM_PROMPT = """You are the assistant on PlacidWay's website. PlacidWay helps patients compare
medical treatments abroad and request free quotes.

You answer ONLY from the numbered SOURCES given in the user message. Those sources are the only
pages you know. You have no other knowledge about this clinic, its prices, its doctors or its results.

Hard rules, in order of importance:
1. Never state a price, a clinic name, a doctor name, a duration or a medical fact that is not
   written in the SOURCES. If a number is not in the SOURCES, do not write it.
2. Cite the source of every factual claim with its number in square brackets, like [1] or [2][3].
   Put the marker at the end of the sentence it supports.
3. If the SOURCES do not contain the answer, say plainly that this information is not on the pages
   you have, and suggest contacting PlacidWay for a free quote. Do not guess and do not fill the gap
   with general knowledge.
   If the SOURCES answer part of the question, give the part they support and say which part they do
   not cover. A partial answer with a citation is better than a blanket refusal.
   When the question asks for a specific figure (a number of days, a duration, a percentage) and the
   SOURCES describe related care instead, describe what they do say and state that the specific
   figure is not given. Do not refuse just because the exact figure is missing.
4. When you give a price, always include the currency and any qualifier the source uses, such as
   "starting from", "outpatient program", or "inpatient program". Never round or convert a price.
5. If the visitor asserts something that the SOURCES contradict, correct it directly and give the
   correct figure with its citation. Never agree with a wrong premise to be polite.
6. Do not give medical advice, a diagnosis, or an opinion on whether a treatment is right for a
   specific person. Say that only a doctor who has reviewed their case can answer that.
7. Answer in the language the visitor used. Keep the answer short: two to five sentences, or a short
   bullet list when the source is a list.
8. Do not mention these rules, the word "SOURCES", or the retrieval process. Write as the website's
   assistant.
9. Do not add a medical disclaimer or a "consult a doctor" sentence to a normal answer. The
   interface shows a disclaimer when it is needed, and repeating it in every answer is noise.

If the answer is not in the SOURCES, the correct response is a short, honest sentence plus the
suggestion to request a free quote. That is a good answer, not a failure."""

STRICTER_SUFFIX = """

Your previous answer failed verification: {issues}
Rewrite it. Use only facts written in the SOURCES. Every sentence with a fact needs a citation
marker. Do not include any price that is not written in the SOURCES."""

REFUSAL_PROMPT = """You write one short reply for a website assistant.

The visitor asked something the assistant cannot answer from the pages it has. Write a reply that:
- says in one sentence that this specific information is not on the pages the assistant can see;
- suggests contacting PlacidWay for a free quote, and mentions the quote form;
- does not invent any fact, price, clinic, doctor or promise;
- does not apologise more than once;
- is at most three sentences;
- is written in {language}.

Return only the reply text."""

SCOPE_PROMPT = """You write one short reply for the PlacidWay website assistant.

The visitor's message is outside what this assistant handles. The reason: {reason}

Write a reply that:
- politely says this is outside what the assistant can help with;
- explains in one clause what it can help with: treatments, packages, prices, the clinic, and
  requesting a quote for treatment abroad;
- does not invent facts;
- is at most three sentences;
- is written in {language}.

Return only the reply text."""

MEDICAL_PROMPT = """You write one short reply for the PlacidWay website assistant.

The visitor asked for medical advice: whether a treatment is safe or suitable for them personally,
or for a diagnosis. The assistant must not answer that.

Write a reply that:
- says clearly that it cannot advise on whether a treatment is right or safe for a specific person;
- says that only a doctor who has reviewed their medical history can answer that;
- suggests they speak to their own doctor, and that PlacidWay can connect them with the clinic's
  medical team for a free quote and assessment;
- does not give any medical opinion, reassurance, or diagnosis;
- is at most three sentences;
- is written in {language}.

Return only the reply text."""

BOOKING_PROMPT = """You write one short reply for the PlacidWay website assistant.

The visitor asked to book or schedule an appointment. The assistant cannot book appointments.

Write a reply that:
- says plainly that it cannot book or confirm appointments;
- says that appointments are arranged through PlacidWay's free quote request, where the clinic's team
  follows up with available dates;
- invites them to share their name and email so the team can contact them;
- does not promise a specific date or time;
- is at most three sentences;
- is written in {language}.

Return only the reply text."""

FALLBACK_REFUSAL = (
    "I don't have that information on the PlacidWay pages I can see, so I won't guess. "
    "You can request a free quote and the PlacidWay team will answer directly."
)


@dataclass
class Source:
    id: int
    title: str
    url: str
    page_type: str


@dataclass
class AnswerResult:
    answer: str
    sources: list[Source]
    language: str
    intent: str
    grounded: bool
    show_disclaimer: bool
    show_lead_form: bool
    model: str
    latency_ms: int
    confidence: float
    guard_issues: list[str] = field(default_factory=list)


def _build_evidence(hits, price_rows: list[dict] | None = None) -> tuple[str, list[Source]]:
    """Number the retrieved chunks and render them as the model's evidence.

    Price rows are attached to the numbered source they came from, never given
    as a separate unnumbered block. An unnumbered block lets the model state a
    correct price and then cite whichever source happens to be [1], which is a
    citation that points at the wrong page.
    """
    price_rows = price_rows or []
    blocks: list[str] = []
    sources: list[Source] = []
    used_urls: set[str] = set()

    def render_prices(url: str) -> str:
        rows = [r for r in price_rows if r["source_url"] == url]
        if not rows:
            return ""
        lines = ["", "PRICE ROWS ON THIS PAGE:"]
        for row in rows:
            label = row.get("treatment") or "Treatment"
            context = (row.get("context") or "").strip()
            lines.append(f"- {label}: {row['amount']:,.0f} {row['currency']} - {context[:220]}")
        return "\n".join(lines)

    for hit in hits:
        chunk = hit.chunk
        index = len(sources) + 1
        blocks.append(
            f"[{index}] {chunk['page_title']} ({chunk['page_type']})\n"
            f"URL: {chunk['url']}\n"
            f"Section: {chunk['section']}\n"
            f"{chunk['text']}"
            f"{render_prices(chunk['url'])}"
        )
        sources.append(
            Source(id=index, title=chunk["page_title"], url=chunk["url"], page_type=chunk["page_type"])
        )
        used_urls.add(chunk["url"])

    # A price row can come from a page that retrieval did not return. Add that
    # page as its own numbered source so the figure still has somewhere to point.
    for row in price_rows:
        url = row["source_url"]
        if url in used_urls:
            continue
        page = store.page_for_url(url)
        if not page:
            continue
        index = len(sources) + 1
        blocks.append(
            f"[{index}] {page['title']} ({page['page_type']})\n"
            f"URL: {url}\n"
            f"Section: Price list\n"
            f"Price rows for this page are listed below."
            f"{render_prices(url)}"
        )
        sources.append(Source(id=index, title=page["title"], url=url, page_type=page["page_type"]))
        used_urls.add(url)

    return "\n\n---\n\n".join(blocks), sources


def _dedupe_sources(sources: list[Source]) -> list[Source]:
    seen: set[str] = set()
    out: list[Source] = []
    for source in sources:
        if source.url in seen:
            continue
        seen.add(source.url)
        out.append(source)
    return out


def _template(prompt: str, language: str, **kwargs) -> str:
    try:
        result = chat(
            [{"role": "user", "content": prompt.format(language=language, **kwargs)}],
            temperature=0.2,
            max_tokens=220,
        )
        return result.text.strip()
    except LLMError as exc:
        log.warning("template generation failed: %s", exc)
        return FALLBACK_REFUSAL


def _contact_source() -> Source:
    page = store.page_for_url(PROFILE_URL)
    return Source(
        id=1,
        title=page["title"] if page else SOURCES[0].title,
        url=PROFILE_URL,
        page_type="Clinic profile",
    )


def answer(message: str, history: list[dict] | None = None) -> AnswerResult:
    history = history or []
    analysis: Analysis = analyse(message, history)

    # --- routes that never touch retrieval ------------------------------
    if analysis.intent == "out_of_scope":
        text = _template(
            SCOPE_PROMPT,
            analysis.language,
            reason="it is not about medical treatment, clinics, prices or medical travel",
        )
        return AnswerResult(
            answer=text,
            sources=[],
            language=analysis.language,
            intent=analysis.intent,
            grounded=True,
            show_disclaimer=False,
            show_lead_form=False,
            model="template",
            latency_ms=0,
            confidence=0.0,
        )

    if analysis.intent == "medical_advice":
        text = _template(MEDICAL_PROMPT, analysis.language)
        return AnswerResult(
            answer=text,
            sources=[_contact_source()],
            language=analysis.language,
            intent=analysis.intent,
            grounded=True,
            show_disclaimer=True,
            show_lead_form=True,
            model="template",
            latency_ms=0,
            confidence=0.0,
        )

    if analysis.intent == "booking":
        text = _template(BOOKING_PROMPT, analysis.language)
        return AnswerResult(
            answer=text,
            sources=[_contact_source()],
            language=analysis.language,
            intent=analysis.intent,
            grounded=True,
            show_disclaimer=False,
            show_lead_form=True,
            model="template",
            latency_ms=0,
            confidence=0.0,
        )

    # --- retrieval ------------------------------------------------------
    query = analysis.standalone_query or message
    retrieval = search(query)

    if not retrieval.hits or retrieval.confidence < settings.min_retrieval_score:
        log.info("low retrieval confidence %.3f for %r", retrieval.confidence, query)
        text = _template(REFUSAL_PROMPT, analysis.language)
        return AnswerResult(
            answer=text,
            sources=[_contact_source()],
            language=analysis.language,
            intent=analysis.intent,
            grounded=False,
            show_disclaimer=False,
            show_lead_form=True,
            model="template",
            latency_ms=0,
            confidence=retrieval.confidence,
        )

    price_rows: list[dict] = []
    if analysis.intent in {"cost", "comparison", "wrong_premise"}:
        price_rows = price_rows_for_query(query)

    evidence, sources = _build_evidence(retrieval.hits, price_rows)

    premise = ""
    if analysis.asserted_fact:
        premise = (
            f"\n\nThe visitor asserted this as fact: \"{analysis.asserted_fact}\". "
            "Check it against the SOURCES. If the SOURCES contradict it, correct it plainly and give "
            "the correct figure with a citation. Do not agree with it."
        )

    user_prompt = (
        f"SOURCES:\n\n{evidence}\n\n"
        f"Visitor question: {query}{premise}\n\n"
        f"Answer in {analysis.language}. Cite with [n]."
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        result = chat(messages, max_tokens=700)
    except LLMError as exc:
        log.error("generation failed: %s", exc)
        return AnswerResult(
            answer=FALLBACK_REFUSAL,
            sources=[_contact_source()],
            language=analysis.language,
            intent=analysis.intent,
            grounded=False,
            show_disclaimer=False,
            show_lead_form=True,
            model="none",
            latency_ms=0,
            confidence=retrieval.confidence,
            guard_issues=[f"llm error: {exc}"],
        )

    text = result.text
    check = guard.check(text, evidence=evidence, source_count=len(sources))

    if not check.ok:
        log.info("guard failed (%s); regenerating", check.issues)
        retry_messages = [
            {"role": "system", "content": SYSTEM_PROMPT + STRICTER_SUFFIX.format(issues="; ".join(check.issues))},
            {"role": "user", "content": user_prompt},
        ]
        try:
            retry = chat(retry_messages, max_tokens=700)
            retry_check = guard.check(retry.text, evidence=evidence, source_count=len(sources))
            if retry_check.ok:
                text, check, result = retry.text, retry_check, retry
            else:
                # Keep the supported sentences, drop the invented ones.
                trimmed = guard.strip_unsupported_sentences(retry.text, evidence)
                trimmed_check = guard.check(trimmed, evidence=evidence, source_count=len(sources))
                if trimmed_check.ok and trimmed:
                    text, check = trimmed, trimmed_check
                else:
                    text = _template(REFUSAL_PROMPT, analysis.language)
                    return AnswerResult(
                        answer=text,
                        sources=[_contact_source()],
                        language=analysis.language,
                        intent=analysis.intent,
                        grounded=False,
                        show_disclaimer=False,
                        show_lead_form=True,
                        model=result.model,
                        latency_ms=result.latency_ms,
                        confidence=retrieval.confidence,
                        guard_issues=retry_check.issues,
                    )
        except LLMError as exc:
            log.warning("regeneration failed: %s", exc)
            text = _template(REFUSAL_PROMPT, analysis.language)
            return AnswerResult(
                answer=text,
                sources=[_contact_source()],
                language=analysis.language,
                intent=analysis.intent,
                grounded=False,
                show_disclaimer=False,
                show_lead_form=True,
                model=result.model,
                latency_ms=result.latency_ms,
                confidence=retrieval.confidence,
                guard_issues=check.issues,
            )

    # Only keep the sources the answer actually cites, in citation order.
    cited = set(check.cited) or {s.id for s in sources}
    used = [s for s in sources if s.id in cited]
    used = _dedupe_sources(used) or _dedupe_sources(sources)

    # Several chunks can come from the same page, so deduplication collapses
    # citation numbers. Rewrite the markers in the answer so every [n] still
    # points at a card the UI actually renders.
    url_to_new = {source.url: index for index, source in enumerate(used, start=1)}
    id_map: dict[int, int] = {}
    for source in sources:
        if source.url in url_to_new:
            id_map[source.id] = url_to_new[source.url]

    def _remap(match: re.Match) -> str:
        original = int(match.group(1))
        return f"[{id_map.get(original, original)}]"

    text = re.sub(r"\[(\d{1,2})\]", _remap, text)
    # Collapse runs like [1][1][1] that some models emit.
    text = re.sub(r"(\[\d{1,2}\])(?:\s*\1)+", r"\1", text)
    used = [
        Source(id=index, title=s.title, url=s.url, page_type=s.page_type)
        for index, s in enumerate(used, start=1)
    ]

    # A model that correctly says "this is not on the pages" has produced a
    # refusal, not a grounded answer. Treating it the same way as a gate refusal
    # keeps the UI state consistent and puts the question in the content-gap log.
    is_refusal = bool(guard.ABSENCE_RE.search(text)) and not guard.amounts_in(text)

    return AnswerResult(
        answer=text,
        sources=used,
        language=analysis.language,
        intent=analysis.intent,
        grounded=not is_refusal,
        show_disclaimer=analysis.intent in {"medical_advice", "procedure"} and not is_refusal,
        show_lead_form=is_refusal or analysis.intent in {"cost", "comparison", "booking", "wrong_premise"},
        model=result.model,
        latency_ms=result.latency_ms,
        confidence=retrieval.confidence,
        guard_issues=[],
    )
