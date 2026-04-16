# Infrastructure

Docker and deployment configuration.

## docker-compose.yml

Services:
- **postgres** - PostgreSQL 15 database
- **qdrant** - Vector database
- **n8n** - Workflow orchestration
- **api** - FastAPI backend

All services have health checks and proper dependency ordering.

## Dockerfile

Builds the FastAPI backend container:
- Base: python:3.11-slim
- Installs system dependencies (gcc, postgresql-client)
- Copies and installs Python dependencies
- Exposes port 8000

## Environment Setup

1. Copy `.env.example` to `.env`
2. Update with your actual API keys:
   - `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`
   - `COINGECKO_API_KEY` (optional)
   - `N8N_BASIC_AUTH_PASSWORD`

## Quick Start

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop all services
docker-compose down

# Remove volumes (clean slate)
docker-compose down -v
```

## Database Backups

PostgreSQL data persists in the `postgres_data` volume.

To backup:
```bash
docker-compose exec postgres pg_dump -U finup finup_db > backup.sql
```

To restore:
```bash
docker-compose exec -T postgres psql -U finup finup_db < backup.sql
```

## Implementation Status

- [x] docker-compose.yml
- [x] infra/Dockerfile
- [ ] Deployment to production
- [ ] SSL/TLS configuration
