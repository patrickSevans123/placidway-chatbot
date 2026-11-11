"""Configuration, read once from the environment.

Every value has a working default so the app starts with no .env file at all.
The only value that must be supplied in production is LLM_API_KEY.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value not in (None, "") else default


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env(name, str(default)))
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    return _env(name, "1" if default else "0").lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # --- LLM -------------------------------------------------------------
    llm_base_url: str = field(default_factory=lambda: _env("LLM_BASE_URL", "https://api.mistral.ai/v1"))
    llm_api_key: str = field(default_factory=lambda: _env("LLM_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL", "deepseek-v4-1-flash-1017"))
    # Tried in order when the primary model errors out.
    llm_fallbacks: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            m.strip()
            for m in _env("LLM_FALLBACKS", "mistral-large-latest,mistral-small-latest").split(",")
            if m.strip()
        )
    )
    llm_timeout: float = field(default_factory=lambda: _env_float("LLM_TIMEOUT", 60.0))
    llm_temperature: float = field(default_factory=lambda: _env_float("LLM_TEMPERATURE", 0.0))

    # --- Retrieval -------------------------------------------------------
    top_k: int = field(default_factory=lambda: _env_int("TOP_K", 8))
    candidate_k: int = field(default_factory=lambda: _env_int("CANDIDATE_K", 24))
    use_dense: bool = field(default_factory=lambda: _env_bool("USE_DENSE", True))
    # "api" uses the same OpenAI-compatible endpoint as the chat model.
    # "local" uses fastembed (optional dependency, works offline).
    # "none" disables dense retrieval entirely.
    embedding_backend: str = field(default_factory=lambda: _env("EMBEDDING_BACKEND", "api").lower())
    embedding_model: str = field(default_factory=lambda: _env("EMBEDDING_MODEL", "mistral-embed"))
    embedding_batch: int = field(default_factory=lambda: _env_int("EMBEDDING_BATCH", 64))
    # Below this fused score the bot refuses instead of guessing.
    min_retrieval_score: float = field(default_factory=lambda: _env_float("MIN_RETRIEVAL_SCORE", 0.40))

    # --- Ingestion -------------------------------------------------------
    crawl_delay: float = field(default_factory=lambda: _env_float("CRAWL_DELAY", 3.0))
    user_agent: str = field(
        default_factory=lambda: _env(
            "USER_AGENT",
            "PlacidWayAssessmentBot/1.0 (+https://github.com/patrickSevans123/placidway-chatbot; assessment)",
        )
    )
    fetch_timeout: float = field(default_factory=lambda: _env_float("FETCH_TIMEOUT", 30.0))

    # --- Storage ---------------------------------------------------------
    data_dir: Path = field(default_factory=lambda: Path(_env("DATA_DIR", str(ROOT / "data"))))
    db_path: Path = field(default_factory=lambda: Path(_env("DB_PATH", str(ROOT / "data" / "app.db"))))

    # --- App -------------------------------------------------------------
    admin_token: str = field(default_factory=lambda: _env("ADMIN_TOKEN", ""))
    max_history_turns: int = field(default_factory=lambda: _env_int("MAX_HISTORY_TURNS", 6))

    @property
    def corpus_path(self) -> Path:
        return self.data_dir / "corpus.json"

    @property
    def embeddings_path(self) -> Path:
        return self.data_dir / "embeddings.npy"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"


settings = Settings()
