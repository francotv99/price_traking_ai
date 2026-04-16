# ETL Module

Data ingestion pipeline for cryptocurrency prices from CoinGecko.

## Overview

The ETL module handles:
- Fetching price data from CoinGecko API
- Parsing and normalizing responses
- Storing prices in PostgreSQL
- Idempotent inserts with conflict handling
- Rate limiting and retry logic

## Endpoints

### POST /etl/run

Execute the complete ingestion pipeline for all active products.

**Request:**
```json
{}
```

**Response:**
```json
{
  "status": "ok",
  "products_processed": 4,
  "records_inserted": 47,
  "records_skipped": 12,
  "errors": [],
  "triggered_at": "2026-04-15T10:00:00Z"
}
```

## Module Structure

- `router.py` - FastAPI endpoint definition
- `fetcher.py` - CoinGecko API client
- `parser.py` - Response normalization
- `repository.py` - Database operations
- `models.py` - Data models (PriceRecord, ETLResult)

## Configuration

Via environment variables:
- `ETL_PRODUCTS` - Comma-separated list of products
- `ETL_LOOKBACK_DAYS` - Historical data window
- `ETL_INTERVAL_DAYS` - Minimum interval between checks
- `COINGECKO_BASE_URL` - API endpoint
- `COINGECKO_API_KEY` - Optional API key

## Implementation Status

- [ ] fetcher.py
- [ ] parser.py
- [ ] repository.py
- [ ] router.py
- [ ] models.py
- [ ] Unit tests
