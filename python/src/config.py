# Modified for the English text/TXT demo; scope and behavior are documented in README.md.
"""Read provider and local application settings from the environment."""

import os
from pathlib import Path

from dotenv import load_dotenv
from .harness.errors import ReviewStageError

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class Settings:
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto").strip().lower()
    MINIMAX_API_KEY: str = os.getenv("MINIMAX_API_KEY", "")
    MINIMAX_API_BASE: str = os.getenv("MINIMAX_API_BASE", "https://api.minimax.chat/v1")

    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")

    APP_HOST: str = os.getenv("APP_HOST", "127.0.0.1")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    PROJECT_ROOT: Path = Path(__file__).parent.parent
    RULES_DIR: Path = PROJECT_ROOT / "src" / "rules" / "definitions"

    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 4096
    LLM_MODEL: str = os.getenv("LLM_MODEL", "")


settings = Settings()


def get_llm():
    """Select a provider explicitly, or use the first real configured key."""
    from langchain_openai import ChatOpenAI

    def usable(key):
        return bool(key.strip()) and not key.strip().startswith("your_")

    provider = settings.LLM_PROVIDER
    if provider == "auto":
        provider = "minimax" if usable(settings.MINIMAX_API_KEY) else "openai"
    if provider == "minimax":
        key, base, default_model = (
            settings.MINIMAX_API_KEY, settings.MINIMAX_API_BASE, "MiniMax-M2.7"
        )
    elif provider == "openai":
        key, base, default_model = (
            settings.OPENAI_API_KEY, settings.OPENAI_API_BASE, "gpt-4o-mini"
        )
    else:
        raise ReviewStageError("INVALID_PROVIDER")
    if not usable(key):
        raise ReviewStageError("PROVIDER_NOT_CONFIGURED")
    if provider == "openai" and "api.openai.com" not in base and not settings.LLM_MODEL:
        raise ReviewStageError("MODEL_NOT_CONFIGURED")
    return ChatOpenAI(
        model=settings.LLM_MODEL or default_model,
        api_key=key,
        base_url=base,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        request_timeout=30,
        max_retries=0,
    )
