"""Application settings and configuration."""
from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    environment: str = "development"

    # Database
    database_url: str = "postgresql://finup:finup@localhost:5432/finup_db"

    # CoinGecko
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"
    coingecko_api_key: str | None = None

    # ETL
    etl_products: str = "bitcoin,ethereum,solana,cardano"
    etl_lookback_days: int = 90
    etl_interval_days: int = 1

    # ML
    ml_contamination: float = 0.05
    ml_lookback_days: int = 90
    ml_opportunity_delta_threshold: float = 0.15
    ml_anomaly_window_hours: int = 1

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "crypto_chunks"

    # LLM
    anthropic_api_key: str | None = None
    openai_api_key: str | None = None

    # n8n
    n8n_webhook_url: str = "http://localhost:5678"
    n8n_basic_auth_user: str = "admin"
    n8n_basic_auth_password: str = "admin"

    @property
    def etl_products_list(self) -> list[str]:
        return [p.strip() for p in self.etl_products.split(",")]

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"
