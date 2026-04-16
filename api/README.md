# API

FastAPI application entry point.

## Overview

The API module includes:
- Main FastAPI application setup
- Router registration (ETL, ML, RAG)
- Dependency injection
- Configuration management
- Health checks and status endpoints

## Endpoints

- `GET /` - Welcome message
- `GET /health` - Health check
- `GET /docs` - Swagger UI
- `GET /redoc` - ReDoc

### Sub-routers

- `POST /etl/run` - Data ingestion (from etl module)
- `POST /ml/detect` - Anomaly detection (from ml module)
- `POST /rag/reindex` - RAG reindexing (from rag module)

## Module Structure

- `main.py` - FastAPI application
- `settings.py` - Configuration (Pydantic)
- `dependencies.py` - Dependency injection (DB connections, etc.)

## Configuration

Via `.env` file (see `.env.example`):
- `API_HOST` - Bind host (default: 0.0.0.0)
- `API_PORT` - Bind port (default: 8000)
- `LOG_LEVEL` - Logging level (default: INFO)
- `DATABASE_URL` - PostgreSQL connection

## Running Locally

```bash
# With hot reload
uvicorn api.main:app --reload

# Production
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

## Implementation Status

- [ ] main.py
- [ ] settings.py
- [ ] dependencies.py
