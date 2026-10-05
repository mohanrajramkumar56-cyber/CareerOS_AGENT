"""
CareerOS API - Core configuration
Uses pydantic-settings for environment-driven config.
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Environment ─────────────────────────────────────────────
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # ── API ──────────────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_secret_key: str = "insecure-dev-key-CHANGE-IN-PROD"
    # Plain string — avoids pydantic-settings JSON pre-parsing.
    # Use allowed_origins_list property wherever a list is needed.
    api_allowed_origins: str = "http://localhost:3000"

    # ── Database ─────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://careeros:careeros@localhost:5432/careeros"
    database_url_sync: str = "postgresql://careeros:careeros@localhost:5432/careeros"
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # ── Redis ────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Auth ─────────────────────────────────────────────────────
    jwt_secret: str = "insecure-jwt-secret-CHANGE-IN-PROD"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 30

    # ── Storage ──────────────────────────────────────────────────
    storage_backend: str = "local"
    storage_local_path: str = "./storage"
    s3_endpoint_url: str = ""
    s3_bucket_name: str = "careeros"
    s3_access_key_id: str = ""
    s3_secret_access_key: str = ""
    s3_region: str = "us-east-1"

    # ── Model Router ─────────────────────────────────────────────
    model_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_default_model: str = "llama3"
    ollama_embedding_model: str = "nomic-embed-text"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_default_model: str = "gpt-4o-mini"

    # ── Observability ────────────────────────────────────────────
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "careeros-api"

    # ── Rate Limiting ────────────────────────────────────────────
    rate_limit_job_discovery_per_hour: int = 100
    rate_limit_api_per_minute: int = 60

    @field_validator("api_allowed_origins", mode="before")
    @classmethod
    def _parse_origins(cls, v: object) -> str:
        """Accept comma-string or JSON array, always store as comma-string."""
        if isinstance(v, list):
            return ",".join(str(i) for i in v)
        if isinstance(v, str):
            stripped = v.strip()
            if stripped.startswith("["):
                import json as _json
                try:
                    return ",".join(_json.loads(stripped))
                except Exception:
                    pass
            return stripped
        return "http://localhost:3000"

    @property
    def allowed_origins_list(self) -> List[str]:
        """Origins as a list — use this in CORS middleware."""
        return [o.strip() for o in self.api_allowed_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
