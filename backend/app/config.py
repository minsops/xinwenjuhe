"""Application settings loaded from environment variables."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for API, workers, collectors, and AI providers."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/truthpuzzle"
    redis_url: str = "redis://localhost:6379/0"
    search_engine_url: str | None = None
    search_engine_api_key: str | None = None
    backend_cors_origins: str = "http://localhost:3000"

    llm_provider: str = "ollama"
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-pro"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    mbfc_rapidapi_key: str | None = None

    collect_interval_minutes: int = 15
    regular_collect_interval_minutes: int = 60
    hot_event_collect_interval_minutes: int = 15
    hot_event_threshold: float = 70.0
    google_news_enabled: bool = True
    max_concurrent_scrapers: int = 10

    cluster_similarity_threshold: float = 0.75
    cluster_time_window_hours: int = 72
    consensus_threshold: float = 0.70
    reanalyze_threshold: float = 0.10

    request_timeout_seconds: float = 20.0
    app_name: str = Field(default="TruthPuzzle")

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return cached settings for dependency injection."""
    return Settings()


settings = get_settings()
