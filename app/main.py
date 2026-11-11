"""FastAPI application: chat API, lead capture, health, admin refresh."""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

from . import db, refresh
from .answer import answer as generate_answer
from .config import ROOT, settings
from .sources import SOURCES
from .store import store

logging.basicConfig(level=logging.INFO, format="%(levelname)-7s %(name)s: %(message)s")
log = logging.getLogger("api")


class UTF8JSONResponse(JSONResponse):
    """Declare the charset explicitly.

    FastAPI's default is bare `application/json`. Older clients (PowerShell 5.1
    among them) then decode the body as Latin-1 and mangle every non-ASCII
    character, which turns an en dash in a price range into garbage.
    """

    media_type = "application/json; charset=utf-8"

app = FastAPI(title="PlacidWay Knowledge Chatbot", version="1.0.0", default_response_class=UTF8JSONResponse)

WEB_DIR = ROOT / "web"


@app.on_event("startup")
def _startup() -> None:
    db.init()
    log.info(
        "ready: %d pages, %d chunks, dense=%s, model=%s",
        store.corpus.get("page_count", 0),
        len(store.chunks),
        store.dense_ready,
        settings.llm_model,
    )


@app.middleware("http")
async def cache_headers(request, call_next):
    """Keep the HTML fresh and let the versioned assets be cached.

    The site sits behind Cloudflare, which caches by file extension. Without
    this, a 404 served once for /app.js is cached at the edge and the page stays
    broken long after the origin is fixed.
    """
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    elif path.endswith((".css", ".js")):
        response.headers["Cache-Control"] = "public, max-age=3600"
    else:
        response.headers["Cache-Control"] = "no-cache"
    return response


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1, max_length=2000)


class LeadRequest(BaseModel):
    session_id: str | None = None
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    message: str | None = Field(default=None, max_length=2000)


@app.get("/")
def index():
    page = WEB_DIR / "index.html"
    if not page.exists():
        return JSONResponse({"error": "front end not built"}, status_code=500)
    return FileResponse(page)


@app.get("/api/health")
def health():
    corpus = store.corpus
    return {
        "status": "ok" if store.ready else "degraded",
        "pages": corpus.get("page_count", 0),
        "chunks": len(store.chunks),
        "prices": len(corpus.get("prices", [])),
        "faqs": len(corpus.get("faqs", [])),
        "model": settings.llm_model,
        "dense_retrieval": store.dense_ready,
        "last_ingest": corpus.get("built_at"),
        "refresh": refresh.status(),
        "stats": db.stats(),
    }


@app.get("/api/sources")
def sources():
    return {
        "sources": [
            {
                "title": page["title"],
                "url": page["url"],
                "page_type": page["page_type"],
                "chunks": page["chunks"],
                "prices": page["prices"],
            }
            for page in store.corpus.get("pages", [])
        ]
    }


@app.post("/api/chat")
def chat(request: ChatRequest):
    started = time.monotonic()
    session_id = request.session_id or uuid.uuid4().hex

    db.touch_session(session_id)
    history = db.history(session_id, limit=settings.max_history_turns * 2)
    db.add_message(session_id, "user", request.message)

    try:
        result = generate_answer(request.message, history)
    except Exception as exc:  # never leak a stack trace to the browser
        log.exception("chat failed")
        return JSONResponse(
            {
                "session_id": session_id,
                "answer": "Something went wrong on my side. Please try again, or request a free quote and the team will reply directly.",
                "sources": [],
                "language": "en",
                "intent": "error",
                "grounded": False,
                "show_disclaimer": False,
                "show_lead_form": True,
                "latency_ms": int((time.monotonic() - started) * 1000),
                "error": str(exc)[:200],
            },
            status_code=200,
        )

    db.add_message(
        session_id,
        "assistant",
        result.answer,
        intent=result.intent,
        grounded=result.grounded,
        confidence=result.confidence,
    )

    if not result.grounded:
        db.log_unanswered(session_id, request.message, result.intent, result.confidence)

    return {
        "session_id": session_id,
        "answer": result.answer,
        "sources": [
            {"id": s.id, "title": s.title, "url": s.url, "page_type": s.page_type} for s in result.sources
        ],
        "language": result.language,
        "intent": result.intent,
        "grounded": result.grounded,
        "show_disclaimer": result.show_disclaimer,
        "show_lead_form": result.show_lead_form,
        "latency_ms": int((time.monotonic() - started) * 1000),
        "model": result.model,
        "confidence": result.confidence,
    }


@app.post("/api/lead")
def lead(request: LeadRequest):
    db.add_lead(request.session_id, request.name, request.email, request.message)
    log.info("lead captured for session %s", request.session_id)
    return {"ok": True}


def _require_admin(token: str | None) -> None:
    if not settings.admin_token:
        raise HTTPException(status_code=503, detail="admin endpoints disabled: ADMIN_TOKEN not set")
    if token != settings.admin_token:
        raise HTTPException(status_code=401, detail="bad token")


@app.post("/api/admin/refresh")
def refresh_now(
    force: bool = False,
    x_admin_token: str | None = Header(default=None),
):
    """Re-check the seven pages and rebuild the index only if something changed.

    Returns 409 when another refresh is already running, and 503 when the new
    corpus failed the sanity gate. In both cases the live index is untouched.
    """
    _require_admin(x_admin_token)
    try:
        outcome = refresh.run(force=force)
    except refresh.RefreshBusy as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except refresh.RefreshRejected as exc:
        raise HTTPException(status_code=503, detail=f"refresh rejected: {exc}") from exc
    return outcome.as_dict()


@app.get("/api/admin/refresh/status")
def refresh_status(x_admin_token: str | None = Header(default=None)):
    _require_admin(x_admin_token)
    return refresh.status()


@app.get("/api/admin/unanswered")
def unanswered(x_admin_token: str | None = Header(default=None)):
    _require_admin(x_admin_token)
    return {"unanswered": db.unanswered()}


@app.get("/api/admin/stats")
def admin_stats(x_admin_token: str | None = Header(default=None)):
    _require_admin(x_admin_token)
    return db.stats()


# The front end is served from the root, not from /static, because index.html
# references styles.css and app.js by relative path. This mount is registered
# last so every /api route above is matched first.
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
