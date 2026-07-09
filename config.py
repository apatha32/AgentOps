"""Application settings loaded from environment variables."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    postgres_dsn: str = "postgresql+asyncpg://agentops:agentops@localhost:5432/agentops"
    redis_url: str = "redis://localhost:6379/0"
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    app_env: str = "development"
    log_level: str = "INFO"


settings = Settings()
