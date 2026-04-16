"""SQLAlchemy ORM models for database."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import Column, String, DateTime, Numeric, Boolean, JSONB, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class ProductORM(Base):
    """Product (cryptocurrency) ORM model."""

    __tablename__ = "products"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    external_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    source = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Product {self.external_id}>"


class PriceRecordORM(Base):
    """Price record ORM model."""

    __tablename__ = "price_records"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    product_id = Column(String(100), nullable=False, index=True)
    price_usd = Column(Numeric(precision=20, scale=8), nullable=False)
    recorded_at = Column(DateTime(timezone=True), nullable=False, index=True)
    source = Column(String(50), nullable=False)
    raw_payload = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Unique constraint to prevent duplicates
    __table_args__ = (
        UniqueConstraint("product_id", "recorded_at", name="uq_product_recorded_time"),
    )

    def __repr__(self):
        return f"<PriceRecord {self.product_id}@{self.recorded_at}>"


class AnomalyEventORM(Base):
    """Anomaly event ORM model."""

    __tablename__ = "anomaly_events"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    product_id = Column(String(100), nullable=False, index=True)
    detected_at = Column(DateTime(timezone=True), nullable=False, index=True)
    category = Column(String(50), nullable=False)  # OPPORTUNITY or DATA_ERROR
    score = Column(Numeric(precision=5, scale=4), nullable=False)
    price_actual = Column(Numeric(precision=20, scale=8), nullable=False)
    price_expected = Column(Numeric(precision=20, scale=8), nullable=False)
    delta_pct = Column(Numeric(precision=10, scale=4), nullable=False)
    explanation = Column(String(2000), nullable=True)
    notified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<AnomalyEvent {self.product_id}@{self.detected_at}>"
