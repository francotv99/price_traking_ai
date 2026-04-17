"""Database repository for ETL operations."""
import logging
from typing import Optional, List
from datetime import datetime

from sqlalchemy import insert, select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from etl.models import PriceRecord, Product
from api.models import ProductORM

logger = logging.getLogger(__name__)


# SQLAlchemy ORM models (will be defined in api/models.py)
# Importing here to avoid circular imports


class ETLRepository:
    """Repository for ETL database operations."""

    def __init__(self, session: AsyncSession):
        """Initialize repository with database session.
        
        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def insert_price_records(
        self,
        records: list[PriceRecord],
    ) -> dict:
        """Insert price records with conflict handling.
        
        Uses PostgreSQL INSERT ... ON CONFLICT DO NOTHING
        for idempotent inserts.
        
        Args:
            records: List of PriceRecord objects to insert
            
        Returns:
            Dict with counts: {'inserted': int, 'skipped': int}
            
        Raises:
            Exception: If database operation fails
        """
        if not records:
            return {"inserted": 0, "skipped": 0}

        try:
            # Import here to avoid circular imports
            from api.models import PriceRecordORM

            # Convert Pydantic models to dict
            values = [record.model_dump() for record in records]

            # Create PostgreSQL insert with conflict handling
            stmt = pg_insert(PriceRecordORM).values(values)
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["product_id", "recorded_at"]
            )

            result = await self.session.execute(stmt)
            await self.session.commit()

            # PostgreSQL ON CONFLICT DO NOTHING doesn't return row count directly
            # so we estimate: total - duplicates (by checking if all inserted)
            inserted = min(result.rowcount or 0, len(records))
            skipped = len(records) - inserted

            logger.info(
                f"Inserted {inserted} price records, skipped {skipped} duplicates"
            )

            return {"inserted": inserted, "skipped": skipped}

        except Exception as e:
            logger.error(f"Failed to insert price records: {str(e)}")
            await self.session.rollback()
            raise

    async def get_active_products(self) -> list[Product]:
        """Get all active products for ETL processing.
        
        Returns:
            List of active Product objects
            
        Raises:
            Exception: If database query fails
        """
        try:
            
            stmt = select(ProductORM).where(ProductORM.is_active == True)
            result = await self.session.execute(stmt)
            products = result.scalars().all()

            logger.info(f"Found {len(products)} active products")

            return [
                Product(
                    id=str(p.id),
                    external_id=p.external_id,
                    name=p.name,
                    source=p.source,
                    is_active=p.is_active,
                    created_at=p.created_at,
                )
                for p in products
            ]

        except Exception as e:
            logger.error(f"Failed to get active products: {str(e)}")
            raise

    async def get_latest_price(
        self,
        product_id: str,
    ) -> Optional[PriceRecord]:
        """Get the latest price record for a product.
        
        Args:
            product_id: Product ID
            
        Returns:
            Latest PriceRecord or None if not found
        """
        try:
            from api.models import PriceRecordORM

            stmt = (
                select(PriceRecordORM)
                .where(PriceRecordORM.product_id == product_id)
                .order_by(desc(PriceRecordORM.recorded_at))
                .limit(1)
            )

            result = await self.session.execute(stmt)
            price_row = result.scalar_one_or_none()

            if not price_row:
                return None

            return PriceRecord(
                product_id=price_row.product_id,
                price_usd=price_row.price_usd,
                recorded_at=price_row.recorded_at,
                source=price_row.source,
            )

        except Exception as e:
            logger.error(f"Failed to get latest price for {product_id}: {str(e)}")
            return None

    async def count_records_for_product(
        self,
        product_id: str,
    ) -> int:
        """Count total price records for a product.
        
        Args:
            product_id: Product ID
            
        Returns:
            Number of price records
        """
        try:
            from api.models import PriceRecordORM

            stmt = select(PriceRecordORM).where(
                PriceRecordORM.product_id == product_id
            )
            result = await self.session.execute(stmt)
            count = len(result.scalars().all())

            return count

        except Exception as e:
            logger.error(f"Failed to count records for {product_id}: {str(e)}")
            return 0
