"""Database repository for ML anomaly detection operations."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import AnomalyEventORM, PriceRecordORM
from ml.models import AnomalyEventCreate, PricePoint

logger = logging.getLogger(__name__)


class MLRepository:
    """Repository for ML read/write operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_price_history(self, product_id: str, lookback_days: int) -> list[PricePoint]:
        """Fetch historical price series for a product."""
        since = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        stmt = (
            select(PriceRecordORM)
            .where(PriceRecordORM.product_id == product_id)
            .where(PriceRecordORM.recorded_at >= since)
            .order_by(PriceRecordORM.recorded_at.asc())
        )

        result = await self.session.execute(stmt)
        rows = result.scalars().all()

        return [
            PricePoint(
                product_id=row.product_id,
                price_usd=row.price_usd,
                recorded_at=row.recorded_at,
            )
            for row in rows
        ]

    async def create_anomaly_event(self, payload: AnomalyEventCreate) -> None:
        """Persist a new anomaly event."""
        event = AnomalyEventORM(
            product_id=payload.product_id,
            detected_at=payload.detected_at,
            category=payload.category.value,
            score=payload.score,
            price_actual=payload.price_actual,
            price_expected=payload.price_expected,
            delta_pct=payload.delta_pct,
            explanation=payload.explanation,
        )

        self.session.add(event)
        await self.session.commit()
