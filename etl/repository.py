"""Database repository for ETL operations."""
from __future__ import annotations

import logging

from sqlalchemy import select, desc
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import ProductORM
from etl.models import PriceRecord, Product

logger = logging.getLogger(__name__)


class ETLRepository:
    """Repository for ETL database operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert_price_records(self, records: list[PriceRecord]) -> dict:
        """Insert price records using ON CONFLICT DO NOTHING for idempotency."""
        if not records:
            return {"inserted": 0, "skipped": 0}

        from api.models import PriceRecordORM

        values = [record.model_dump() for record in records]
        stmt = pg_insert(PriceRecordORM).values(values).on_conflict_do_nothing(
            index_elements=["product_id", "recorded_at"]
        )

        result = await self.session.execute(stmt)
        await self.session.commit()

        inserted = min(getattr(result, "rowcount", None) or 0, len(records))
        skipped = len(records) - inserted

        logger.info("Inserted %d price records, skipped %d duplicates", inserted, skipped)
        return {"inserted": inserted, "skipped": skipped}

    async def get_active_products(self) -> list[Product]:
        stmt = select(ProductORM).where(ProductORM.is_active == True)  # noqa: E712
        result = await self.session.execute(stmt)
        products = result.scalars().all()

        logger.info("Found %d active products", len(products))
        return [
            Product(
                id=str(p.id),
                external_id=p.external_id,  # type: ignore[arg-type]
                name=p.name,  # type: ignore[arg-type]
                source=p.source,  # type: ignore[arg-type]
                is_active=p.is_active,  # type: ignore[arg-type]
                created_at=p.created_at,
            )
            for p in products
        ]

    async def get_latest_price(self, product_id: str) -> PriceRecord | None:
        from api.models import PriceRecordORM

        stmt = (
            select(PriceRecordORM)
            .where(PriceRecordORM.product_id == product_id)
            .order_by(desc(PriceRecordORM.recorded_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()

        if not row:
            return None

        return PriceRecord(
            product_id=row.product_id,  # type: ignore[arg-type]
            price_usd=row.price_usd,  # type: ignore[arg-type]
            recorded_at=row.recorded_at,  # type: ignore[arg-type]
            source=row.source,  # type: ignore[arg-type]
        )

    async def count_records_for_product(self, product_id: str) -> int:
        from api.models import PriceRecordORM

        stmt = select(PriceRecordORM).where(PriceRecordORM.product_id == product_id)
        result = await self.session.execute(stmt)
        return len(result.scalars().all())
