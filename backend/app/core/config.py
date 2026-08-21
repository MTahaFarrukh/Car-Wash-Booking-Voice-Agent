"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Monorepo root (carwash-ai/)
BASE_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Central settings for the FastAPI backend."""

    model_config = SettingsConfigDict(
        # Load defaults from .env.example first, then override with real .env.
        env_file=(BASE_DIR / ".env.example", BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql://user:pass@localhost:5432/carwash_ai"
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    uplift_api_key: str = ""
    uplift_agent_id: str = ""
    cors_origins: str = "http://localhost:3000"
    environment: str = "development"
    whatsapp_bridge_secret: str = ""

    # Phase 7 — LLM WhatsApp agent
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 800
    llm_timeout_seconds: float = 45.0
    llm_max_tool_calls: int = 8
    # auto = LLM when configured, else rule-based; llm = require LLM; rule = force Phase 6 agent
    whatsapp_agent_mode: str = "auto"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def llm_is_configured(self) -> bool:
        provider = (self.llm_provider or "").strip().lower()
        return bool(self.llm_api_key) and provider not in {"", "none", "off", "rule"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
