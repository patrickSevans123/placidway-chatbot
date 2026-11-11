"""Thin OpenAI-compatible chat client with a model fallback chain.

The endpoint is any server that speaks `/v1/chat/completions`. In this
deployment it is a local router in front of several providers, which is why the
client tolerates two response shapes: a normal JSON body, and a server-sent
event stream that some upstreams return even when `stream` was not requested.
"""

from __future__ import annotations

import json
import logging
import time
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
        started = time.monotonic()
        try:
            with httpx.Client(timeout=timeout or settings.llm_timeout) as client:
                response = client.post(
                    f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.llm_api_key}",
                        "Content-Type": "application/json",
                    },
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
