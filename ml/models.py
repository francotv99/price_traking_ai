"""Data models for ML anomaly detection module."""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AnomalyCategory(str, Enum):
    """Anomaly classification categories."""

    OPPORTUNITY = "OPPORTUNITY"
    DATA_ERROR = "DATA_ERROR"


class DetectAnomalyRequest(BaseModel):
    """Request payload for anomaly detection endpoint."""

    product_id: str = Field(..., description="Product ID (e.g. bitcoin)")
    lookback_days: int = Field(default=90, ge=1, le=3650)


class PricePoint(BaseModel):
    """Normalized price point for model input."""

    product_id: str
    price_usd: Decimal
    recorded_at: datetime


class AnomalyResult(BaseModel):
    """Result from anomaly detection execution."""

    anomaly: bool
    product_id: str
    category: Optional[AnomalyCategory] = None
    score: Optional[float] = None
    price_actual: Optional[Decimal] = None
    price_expected: Optional[Decimal] = None
    delta_pct: Optional[float] = None


class AnomalyEventCreate(BaseModel):
    """Payload used to persist anomaly events."""

    product_id: str
    detected_at: datetime
    category: AnomalyCategory
    score: float
    price_actual: Decimal
    price_expected: Decimal
    delta_pct: float
    explanation: Optional[str] = None
