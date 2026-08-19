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

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
