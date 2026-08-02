"""Application settings loaded from environment variables."""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


def _postgres_dsn_default() -> str:
    """Railway injects DATABASE_URL as postgres://... — convert to asyncpg scheme."""
    raw = os.environ.get("DATABASE_URL", "")
    if raw:
        return raw.replace("postgres://", "postgresql+asyncpg://", 1).replace(
            "postgresql://", "postgresql+asyncpg://", 1
        )
    return "postgresql+asyncpg://agentops:agentops@localhost:5432/agentops"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    postgres_dsn: str = ""
    redis_url: str = "redis://localhost:6379/0"
    # Set to empty string to disable OTel export (safe when no collector is running)
    otel_exporter_otlp_endpoint: str = ""
    app_env: str = "development"
    log_level: str = "INFO"
    api_key: str = ""
    cors_origins: str = "*"

    def model_post_init(self, __context: object) -> None:
        if not self.postgres_dsn:
            object.__setattr__(self, "postgres_dsn", _postgres_dsn_default())


settings = Settings()
