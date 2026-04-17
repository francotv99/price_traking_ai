"""Data models for ETL module."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PriceRecord(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "product_id": "bitcoin",
            "price_usd": "42500.50",
            "recorded_at": "2026-04-15T10:00:00Z",
            "source": "coingecko",
        }
    })

    product_id: str = Field(...)
    price_usd: Decimal
    recorded_at: datetime
    source: str = Field(default="coingecko")
    raw_payload: dict[str, Any] | None = None


class ETLResult(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "status": "ok",
            "products_processed": 4,
            "records_inserted": 47,
            "records_skipped": 12,
            "errors": [],
            "triggered_at": "2026-04-15T10:00:00Z",
        }
    })

    status: str
    products_processed: int = 0
    product_ids: list[str] = Field(default_factory=list)
    records_inserted: int = 0
    records_skipped: int = 0
    errors: list[str] = Field(default_factory=list)
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CoinGeckoPrice(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {"timestamp": 1713175200000, "price": 42500.50}
    })

    timestamp: int
    price: float


class Product(BaseModel):
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "external_id": "bitcoin",
            "name": "Bitcoin",
            "source": "coingecko",
            "is_active": True,
        }
    })

    id: str | None = None
    external_id: str
    name: str
    source: str = "coingecko"
    is_active: bool = True
    created_at: datetime | None = None
