# Migrations

Alembic database migration management.

## Overview

Alembic handles schema versioning and evolution:
- `001_initial.py` - Initial schema (products, price_records, anomaly_events)
- Future migrations track changes over time

## Running Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade 001_initial

# Rollback to previous version
alembic downgrade -1

# View current version
alembic current

# View history
alembic history
```

## Within Docker

```bash
# Apply migrations
docker-compose exec api alembic upgrade head

# Create new migration (auto-detect changes)
docker-compose exec api alembic revision --autogenerate -m "description"
```

## Creating New Migrations

Manual migration:
```bash
alembic revision -m "Add new column"
```

Then edit the generated file in `versions/`.

Auto-detection (requires SQLAlchemy models):
```bash
alembic revision --autogenerate -m "description"
```

## Implementation Status

- [x] Alembic initialization
- [x] 001_initial migration
- [ ] Future migrations
