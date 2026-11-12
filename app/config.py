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
    # OpenCode Go: an OpenAI-compatible gateway with a monthly allowance, which
    # is why it replaced the per-token Mistral endpoint. Any compatible server
    # still works by setting LLM_BASE_URL.
    llm_base_url: str = field(
        default_factory=lambda: _env("LLM_BASE_URL", "https://opencode.ai/inference/go/openai/v1")
    )
    llm_api_key: str = field(default_factory=lambda: _env("LLM_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL", "deepseek-v4.1-flash"))
    # Tried in order when the primary model errors out.
    llm_fallbacks: tuple[str, ...] = field(
        default_factory=lambda: tuple(
            m.strip()
            for m in _env("LLM_FALLBACKS", "glm-5.3-flash,minimax-m3.1-flash").split(",")
            if m.strip()
        )
    )
    llm_timeout: float = field(default_factory=lambda: _env_float("LLM_TIMEOUT", 60.0))
    llm_temperature: float = field(default_factory=lambda: _env_float("LLM_TEMPERATURE", 0.0))
    # A reasoning model can spend a small `max_tokens` budget before writing
    # anything and return an empty completion. These prompts ask for one JSON
    # object or two sentences, so the reasoning is off unless a deployment wants
    # it. Empty means the field is not sent at all, for providers that reject it.
    llm_reasoning_effort: str = field(
        default_factory=lambda: _env("LLM_REASONING_EFFORT", "none").strip().lower()
    )
    # Gateways ask to be told who is calling, rather than seeing a bare SDK
    # user agent, and to receive a stable conversation id so requests can be
    # routed and cached together.
    llm_user_agent: str = field(
        default_factory=lambda: _env("LLM_USER_AGENT", "PlacidWayAssessmentBot/1.0")
    )
    llm_session_id: str = field(default_factory=lambda: _env("LLM_SESSION_ID", "placidway-guide"))


    # --- Retrieval -------------------------------------------------------
    # The chat gateway serves chat models only, so embeddings have their own
    # endpoint and key. Both default to the chat ones for a single-provider
    # deployment.
    embedding_base_url: str = field(
        default_factory=lambda: _env("EMBEDDING_BASE_URL", _env("LLM_BASE_URL", "https://opencode.ai/inference/go/openai/v1"))
    )
    embedding_api_key: str = field(
        default_factory=lambda: _env("EMBEDDING_API_KEY", _env("LLM_API_KEY", ""))
    )
    top_k: int = field(default_factory=lambda: _env_int("TOP_K", 8))
    candidate_k: int = field(default_factory=lambda: _env_int("CANDIDATE_K", 24))
    # On, and the two evaluations disagree about whether it should be. The
    # retrieval benchmark finds BM25 better at rank 8 (92.7% vs 87.8%) and at the
    # refusal gate (7/10 vs 4/10), but the answer-level evaluation scores 24/24
    # with the dense half on and 22/24 with it off: two comparison questions fall
    # under the refusal threshold once the extra candidates stop lifting their
    # coverage score. The threshold is calibrated against the hybrid
    # distribution, so the hybrid ships and docs/EVALUATION.md records the gap.
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
    # The refresh history is not baked into the image, so it can be moved into a
    # volume: otherwise every redeploy resets `last_checked` to null and the
    # admin status endpoint looks like the scheduler never ran. Empty means
    # "next to the corpus".
    refresh_state_override: str = field(
        default_factory=lambda: _env("REFRESH_STATE_PATH", "")
    )

    # --- App -------------------------------------------------------------
    admin_token: str = field(default_factory=lambda: _env("ADMIN_TOKEN", ""))
    max_history_turns: int = field(default_factory=lambda: _env_int("MAX_HISTORY_TURNS", 6))

    # --- Spend guards ----------------------------------------------------
    rate_limit_enabled: bool = field(default_factory=lambda: _env_bool("RATE_LIMIT_ENABLED", True))
    rate_limit_requests: int = field(default_factory=lambda: _env_int("RATE_LIMIT_REQUESTS", 20))
    rate_limit_window: int = field(default_factory=lambda: _env_int("RATE_LIMIT_WINDOW", 60))

    @property
    def corpus_path(self) -> Path:
        return self.data_dir / "corpus.json"

    @property
    def embeddings_path(self) -> Path:
        return self.data_dir / "embeddings.npy"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def refresh_state_path(self) -> Path:
        if self.refresh_state_override:
            return Path(self.refresh_state_override)
        return self.data_dir / "refresh_state.json"


settings = Settings()
