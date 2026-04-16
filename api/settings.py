"""Application settings and configuration."""
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    environment: str = "development"

    # Database
    database_url: str = "postgresql://finup:finup@localhost:5432/finup_db"

    # CoinGecko API
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"
    coingecko_api_key: Optional[str] = None

    # ETL Configuration
    etl_products: str = "bitcoin,ethereum,solana,cardano"
    etl_lookback_days: int = 90
    etl_interval_days: int = 1

    # ML Configuration
    ml_contamination: float = 0.05
    ml_lookback_days: int = 90
    ml_opportunity_delta_threshold: float = 0.15
    ml_anomaly_window_hours: int = 1

    # Qdrant Configuration
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "product_corpus"

    # LLM Configuration
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # n8n Configuration
    n8n_webhook_url: str = "http://localhost:5678"
    n8n_basic_auth_user: str = "admin"
    n8n_basic_auth_password: str = "admin"

    class Config:
        """Pydantic settings configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @property
    def etl_products_list(self) -> list[str]:
        """Get list of products to monitor."""
        return [p.strip() for p in self.etl_products.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment.lower() == "production"
