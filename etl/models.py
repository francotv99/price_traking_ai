"""Data models for ETL module."""
from datetime import datetime
from typing import Optional, Any
from enum import Enum
from decimal import Decimal

from pydantic import BaseModel, Field


class PriceRecord(BaseModel):
    """Single cryptocurrency price record."""
    
    product_id: str = Field(..., description="CoinGecko ID (e.g., 'bitcoin')")
    price_usd: Decimal = Field(..., description="Price in USD")
    recorded_at: datetime = Field(..., description="UTC timestamp of price")
    source: str = Field(default="coingecko", description="Data source")
    raw_payload: Optional[dict[str, Any]] = Field(
        default=None, description="Raw API response"
    )

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "product_id": "bitcoin",
                "price_usd": "42500.50",
                "recorded_at": "2026-04-15T10:00:00Z",
                "source": "coingecko",
            }
        }


class ETLResult(BaseModel):
    """Result of ETL ingestion run."""
    
    status: str = Field(..., description="'ok' or 'error'")
    products_processed: int = Field(default=0, description="Products attempted")
    product_ids: list[str] = Field(default_factory=list, description="Product IDs processed")
    records_inserted: int = Field(default=0, description="New records inserted")
    records_skipped: int = Field(default=0, description="Duplicate records")
    errors: list[str] = Field(default_factory=list, description="Error messages")
    triggered_at: datetime = Field(
        default_factory=datetime.utcnow, description="Execution timestamp"
    )

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "status": "ok",
                "products_processed": 4,
                "records_inserted": 47,
                "records_skipped": 12,
                "errors": [],
                "triggered_at": "2026-04-15T10:00:00Z",
            }
        }


class CoinGeckoPrice(BaseModel):
    """CoinGecko market chart data point."""
    
    timestamp: int = Field(..., description="Unix timestamp in milliseconds")
    price: float = Field(..., description="Price in USD")

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "timestamp": 1713175200000,
                "price": 42500.50,
            }
        }


class Product(BaseModel):
    """Product (cryptocurrency) definition."""
    
    id: Optional[str] = None
    external_id: str = Field(..., description="CoinGecko ID")
    name: str = Field(..., description="Display name")
    source: str = Field(default="coingecko", description="Data source")
    is_active: bool = Field(default=True, description="Active status")
    created_at: Optional[datetime] = None

    class Config:
        """Pydantic config."""
        json_schema_extra = {
            "example": {
                "external_id": "bitcoin",
                "name": "Bitcoin",
                "source": "coingecko",
                "is_active": True,
            }
        }
