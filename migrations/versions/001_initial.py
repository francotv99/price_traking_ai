"""Initial migration - Create products, price_records, and anomaly_events tables

Revision ID: 001_initial
Revises:
Create Date: 2026-04-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create products table
    op.create_table(
        'products',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.func.gen_random_uuid()),
        sa.Column('external_id', sa.String(100), nullable=False, unique=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_products_external_id'), 'products', ['external_id'], unique=True)

    # Create price_records table
    op.create_table(
        'price_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.func.gen_random_uuid()),
        sa.Column('product_id', sa.String(100), nullable=False),
        sa.Column('price_usd', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('raw_payload', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_id', 'recorded_at', name='uq_product_recorded_time')
    )
    op.create_index(op.f('ix_price_records_product_id'), 'price_records', ['product_id'])
    op.create_index(op.f('ix_price_records_recorded_at'), 'price_records', ['recorded_at'])

    # Create anomaly_events table
    op.create_table(
        'anomaly_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.func.gen_random_uuid()),
        sa.Column('product_id', sa.String(100), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('score', sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column('price_actual', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('price_expected', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('delta_pct', sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('notified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_anomaly_events_product_id'), 'anomaly_events', ['product_id'])
    op.create_index(op.f('ix_anomaly_events_detected_at'), 'anomaly_events', ['detected_at'])


def downgrade() -> None:
    op.drop_index(op.f('ix_anomaly_events_detected_at'), table_name='anomaly_events')
    op.drop_index(op.f('ix_anomaly_events_product_id'), table_name='anomaly_events')
    op.drop_table('anomaly_events')
    
    op.drop_index(op.f('ix_price_records_recorded_at'), table_name='price_records')
    op.drop_index(op.f('ix_price_records_product_id'), table_name='price_records')
    op.drop_table('price_records')
    
    op.drop_index(op.f('ix_products_external_id'), table_name='products')
    op.drop_table('products')
