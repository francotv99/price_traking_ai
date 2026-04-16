"""FastAPI router for ML endpoints."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_session, get_settings
from ml.detector import AnomalyDetector
from ml.models import AnomalyEventCreate, AnomalyResult, DetectAnomalyRequest
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
        )

        detector = AnomalyDetector(
            contamination=settings.ml_contamination,
            opportunity_delta_threshold=settings.ml_opportunity_delta_threshold,
            anomaly_window_hours=settings.ml_anomaly_window_hours,
        )

        result = detector.detect(product_id=payload.product_id, series=history)

        if result.anomaly:
            await repository.create_anomaly_event(
                AnomalyEventCreate(
                    product_id=result.product_id,
                    detected_at=datetime.now(timezone.utc),
                    category=result.category,
                    score=result.score,
                    price_actual=result.price_actual,
                    price_expected=result.price_expected,
                    delta_pct=result.delta_pct,
                )
            )
            logger.info(
                "Anomaly detected for %s: category=%s score=%s",
                result.product_id,
                result.category,
                result.score,
            )

        return result

    except Exception as exc:
        logger.exception("ML detection failed for %s", payload.product_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ML detection failed: {exc}",
        ) from exc
