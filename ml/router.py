"""FastAPI router for ML endpoints."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from api.dependencies import get_session, get_settings
from ml.detector import AnomalyDetector
from ml.models import AnomalyEventCreate, AnomalyResult, DetectAnomalyRequest, PricePoint
from ml.repository import MLRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ml", tags=["ml"])


@router.post("/detect", response_model=AnomalyResult)
async def detect_anomaly(
    payload: DetectAnomalyRequest,
    session=Depends(get_session),
    settings=Depends(get_settings),
) -> AnomalyResult:
    """Run anomaly detection for one product."""
    repository = MLRepository(session)

    try:
        history = await repository.get_price_history(
            product_id=payload.product_id,
            lookback_days=payload.lookback_days,
            lookback_minutes=payload.lookback_minutes,
        )

        detector = AnomalyDetector(
            contamination=settings.ml_contamination,
            opportunity_delta_threshold=settings.ml_opportunity_delta_threshold,
            anomaly_window_hours=settings.ml_anomaly_window_hours,
        )

        result = detector.detect(product_id=payload.product_id, series=history)

        if result.anomaly:
            assert result.category is not None
            assert result.score is not None
            assert result.price_actual is not None
            assert result.price_expected is not None
            assert result.delta_pct is not None
            await repository.create_anomaly_event(
                AnomalyEventCreate(
                    product_id=result.product_id,
                    detected_at=datetime.now(timezone.utc),
                    category=result.category,
                    score=result.score,
                    price_actual=result.price_actual,
                    price_expected=result.price_expected,
                    delta_pct=result.delta_pct,
                    explanation=result.explanation,
                )
            )
            logger.info(
                "Anomaly detected for %s: category=%s score=%s",
                result.product_id,
                result.category,
                result.score,
            )

        return result

    except (ValueError, RuntimeError) as exc:
        logger.exception("ML detection failed for %s", payload.product_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ML detection failed: {exc}",
        ) from exc


class SimulateRequest(BaseModel):
    product_id: str = Field(default="bitcoin")
    base_price: float = Field(default=76000.0, description="Precio base estable en USD")
    spike_pct: float = Field(default=0.15, ge=0.02, le=2.0, description="Porcentaje de spike (0.15 = 15%)")
    history_days: int = Field(default=89, ge=10, le=365)


@router.post("/detect/simulate", response_model=AnomalyResult, tags=["ml"])
async def simulate_anomaly(
    payload: SimulateRequest,
    settings=Depends(get_settings),
) -> AnomalyResult:
    """Simulate an OPPORTUNITY anomaly with synthetic data for demo purposes.

    Generates a stable price history and injects a spike on the latest point
    so the detector reliably returns OPPORTUNITY without needing real market movement.
    """
    now = datetime.now(timezone.utc)

    series = [
        PricePoint(
            product_id=payload.product_id,
            price_usd=Decimal(str(round(payload.base_price + i * (payload.base_price * 0.0001), 2))),
            recorded_at=now - timedelta(days=payload.history_days - i),
        )
        for i in range(payload.history_days)
    ]

    spike_price = round(payload.base_price * (1 + payload.spike_pct), 2)
    series.append(
        PricePoint(
            product_id=payload.product_id,
            price_usd=Decimal(str(spike_price)),
            recorded_at=now,
        )
    )

    detector = AnomalyDetector(
        contamination=0.1,
        opportunity_delta_threshold=settings.ml_opportunity_delta_threshold,
        anomaly_window_hours=settings.ml_anomaly_window_hours,
    )
    return detector.detect(product_id=payload.product_id, series=series)
