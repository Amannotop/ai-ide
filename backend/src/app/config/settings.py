"""Application configuration management."""
from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # App
    app_name: str = "ai-ide"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"

    # Server
    host: str = "127.0.0.1"
    port: int = 3001
    workers: int = 1
    reload: bool = True

    # Database
    database_path: str = "./data/ai-ide.db"

    # AI
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "qwen2.5-coder:7b"
    embedding_model: str = "nomic-embed-text"

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:5174"]

    # Auth (disabled by default for local dev)
    auth_enabled: bool = False
    secret_key: str = "dev-secret-key-change-in-production"

    # Logging
    log_level: str = "INFO"
    log_file: str | None = "./logs/ai-ide.log"

    # Workspace
    workspace_root: str = "./workspace"

    # Indexing
    indexing_enabled: bool = True
    index_interval_seconds: int = 300

    # Rate limiting
    rate_limit_per_minute: int = 60


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()