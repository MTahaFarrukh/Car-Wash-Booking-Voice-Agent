"""LLM provider factory."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.llm.base import LLMProvider
from app.llm.openai_provider import OpenAIProvider


def create_llm_provider(settings: Settings | None = None) -> LLMProvider | None:
    """Return a configured LLM provider, or None when LLM is unavailable."""
    cfg = settings or get_settings()
    provider = (cfg.llm_provider or "").strip().lower()
    if not provider or provider in {"none", "off", "rule"}:
        return None
    if not cfg.llm_api_key:
        return None

    if provider in {"openai", "openai-compatible"}:
        return OpenAIProvider(
            api_key=cfg.llm_api_key,
            model=cfg.llm_model,
            base_url=cfg.llm_base_url,
            timeout_seconds=cfg.llm_timeout_seconds,
            default_temperature=cfg.llm_temperature,
            default_max_tokens=cfg.llm_max_tokens,
        )

    raise ValueError(f"Unsupported LLM_PROVIDER: {cfg.llm_provider}")
