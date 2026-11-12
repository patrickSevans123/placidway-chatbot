"""Thin OpenAI-compatible chat client with a model fallback chain.

The endpoint is any server that speaks `/v1/chat/completions`. In this
deployment it is a local router in front of several providers, which is why the
client tolerates two response shapes: a normal JSON body, and a server-sent
event stream that some upstreams return even when `stream` was not requested.
"""

from __future__ import annotations

import itertools
import json
import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass

import httpx

from .config import settings

log = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


@dataclass
class LLMResult:
    text: str
    model: str
    latency_ms: int


def _parse_body(body: str) -> str:
    """Accept either a JSON completion or an SSE stream, return the text."""
    stripped = body.lstrip()
    if stripped.startswith("data:"):
        parts: list[str] = []
        for line in stripped.splitlines():
            line = line.strip()
            if not line.startswith("data:"):
                continue
            payload = line[5:].strip()
            if payload in ("", "[DONE]"):
                continue
            try:
                event = json.loads(payload)
            except json.JSONDecodeError:
                continue
            for choice in event.get("choices", []):
                delta = choice.get("delta") or choice.get("message") or {}
                content = delta.get("content")
                if isinstance(content, str):
                    parts.append(content)
        return "".join(parts).strip()

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise LLMError(f"response was not JSON: {body[:200]}") from exc

    if "error" in data and not data.get("choices"):
        message = data["error"]
        if isinstance(message, dict):
            message = message.get("message", message)
        raise LLMError(str(message)[:300])

    choices = data.get("choices") or []
    if not choices:
        raise LLMError(f"no choices in response: {body[:200]}")

    choice = choices[0]
    message = choice.get("message") or {}
    content = message.get("content")
    if content is None:
        content = choice.get("text", "")
    if isinstance(content, list):  # some providers return content parts
        content = "".join(part.get("text", "") for part in content if isinstance(part, dict))
    return (content or "").strip()


def _headers() -> dict[str, str]:
    """The headers every model call sends.

    One gateway asks each client to identify itself and to send a stable
    conversation id, so the same call works unchanged against a plain
    OpenAI-compatible server, which ignores both.
    """
    return {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
        "User-Agent": settings.llm_user_agent,
        "x-opencode-session": settings.llm_session_id,
    }


def chat(
    messages: list[dict],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int = 900,
    timeout: float | None = None,
) -> LLMResult:
    if not settings.llm_api_key:
        raise LLMError("LLM_API_KEY is not set")

    candidates = [model or settings.llm_model, *settings.llm_fallbacks]
    seen: set[str] = set()
    last_error: Exception | None = None

    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)

        payload = {
            "model": candidate,
            "messages": messages,
            "temperature": settings.llm_temperature if temperature is None else temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        if settings.llm_reasoning_effort:
            payload["reasoning_effort"] = settings.llm_reasoning_effort
        started = time.monotonic()
        try:
            with httpx.Client(timeout=timeout or settings.llm_timeout) as client:
                response = client.post(
                    f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                    headers=_headers(),
                    json=payload,
                )
            if response.status_code >= 400:
                raise LLMError(f"HTTP {response.status_code}: {response.text[:200]}")

            text = _parse_body(response.text)
            if not text:
                raise LLMError("empty completion")

            return LLMResult(
                text=text,
                model=candidate,
                latency_ms=int((time.monotonic() - started) * 1000),
            )
        except (httpx.HTTPError, LLMError) as exc:
            last_error = exc
            log.warning("model %s failed: %s", candidate, exc)
            continue

    raise LLMError(f"all models failed; last error: {last_error}")


@dataclass
class Delta:
    """One piece of a streaming completion.

    The final delta carries no text. It names the model that answered and how
    long the whole stream took, so the caller can report both in the response
    without a second call.
    """

    text: str = ""
    model: str | None = None
    latency_ms: int | None = None


def _sse_deltas(first: str, rest: Iterator[str]) -> Iterator[str]:
    for line in itertools.chain([first], rest):
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload in ("", "[DONE]"):
            continue
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            continue
        for choice in event.get("choices", []):
            delta = choice.get("delta") or {}
            content = delta.get("content")
            if isinstance(content, str) and content:
                yield content


def chat_stream(
    messages: list[dict],
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int = 900,
    timeout: float | None = None,
    client: httpx.Client | None = None,
) -> Iterator[Delta]:
    """Yield a completion as it is generated.

    Only the first candidate streams. If it fails before yielding anything, the
    non-streaming `chat()` takes over and walks the whole fallback chain. A
    failure after the first token cannot be retried, because the browser has
    already been shown that text; it is raised instead of silently restarted.
    """
    if not settings.llm_api_key:
        raise LLMError("LLM_API_KEY is not set")

    candidate = model or settings.llm_model
    started = time.monotonic()
    payload = {
        "model": candidate,
        "messages": messages,
        "temperature": settings.llm_temperature if temperature is None else temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    if settings.llm_reasoning_effort:
        payload["reasoning_effort"] = settings.llm_reasoning_effort

    emitted = False
    owns_client = client is None
    http = client or httpx.Client(timeout=timeout or settings.llm_timeout)
    try:
        with http.stream(
            "POST",
            f"{settings.llm_base_url.rstrip('/')}/chat/completions",
            headers=_headers(),
            json=payload,
        ) as response:
            if response.status_code >= 400:
                response.read()
                raise LLMError(f"HTTP {response.status_code}: {response.text[:200]}")

            lines = response.iter_lines()
            first = next((line for line in lines if line.strip()), None)
            if first is None:
                raise LLMError("empty completion")

            if first.lstrip().startswith("data:"):
                for piece in _sse_deltas(first, lines):
                    emitted = True
                    yield Delta(text=piece)
            else:
                # Some gateways answer a streaming request with one plain JSON
                # body. That is a complete answer, not an error.
                text = _parse_body("\n".join([first, *lines]))
                if not text:
                    raise LLMError("empty completion")
                emitted = True
                yield Delta(text=text)
    except (httpx.HTTPError, LLMError) as exc:
        if emitted:
            raise LLMError(f"stream failed after the first token: {exc}") from exc
        log.warning("streaming model %s failed: %s; falling back", candidate, exc)
        result = chat(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
        )
        yield Delta(text=result.text)
        yield Delta(model=result.model, latency_ms=result.latency_ms)
        return
    finally:
        if owns_client:
            http.close()

    yield Delta(model=candidate, latency_ms=int((time.monotonic() - started) * 1000))
