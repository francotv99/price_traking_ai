# FinUp Price Tracker

Sistema de monitoreo de precios de criptomonedas con detección de anomalías mediante Machine Learning y alertas enriquecidas con RAG (Retrieval-Augmented Generation).

## Demo

[Ver demostración en video (Loom)](https://www.loom.com/share/519dc7c628ab4882b93fc4b550dd384b)

---

## Descripción del problema

Los precios de criptomonedas fluctúan constantemente. Distinguir una variación relevante (oportunidad real de mercado) de un spike de datos o ruido estadístico requiere análisis cuantitativo continuo. Cuando se detecta una anomalía, el usuario necesita más que un número: necesita contexto accionable que explique qué ocurrió y por qué.

Este sistema automatiza ese ciclo completo: ingesta de precios → detección de anomalías → generación de explicación fundamentada en corpus documental → notificación.

---

## Arquitectura

```
[Cron cada 6h]
      ↓
Workflow 1 — Ingesta
  n8n → POST /etl/run
  Backend → CoinGecko API → PostgreSQL
      ↓ dispara Workflow 2
Workflow 2 — Detección y alerta
  n8n → POST /ml/detect (por producto)
  Backend → Isolation Forest sobre histórico PostgreSQL
      ↓ si anomaly = true
  n8n → Qdrant (búsqueda semántica del corpus)
  n8n → LLM (explicación con citas)
  n8n → Telegram (notificación)
      ↓ dispara Workflow 3
Workflow 3 — Reindexación RAG
  n8n → POST /rag/reindex (producto afectado)
  Backend → CoinGecko → chunks de texto → n8n → embeddings → Qdrant

[Cron semanal]
  Workflow 3 → reindexar todos los productos
```

Ver diagramas detallados en [docs/diagrams/](docs/diagrams/).

---

## Stack tecnológico

| Categoría | Tecnología | Justificación |
|-----------|-----------|---------------|
| Lenguaje | Python 3.11+ | Ecosistema ML maduro, tipado estático con mypy |
| API HTTP | FastAPI | Validación automática con Pydantic, async nativo, OpenAPI incluido |
| Base de datos | PostgreSQL 15 | Soporte JSONB para payload crudo, constraint UNIQUE para idempotencia ETL |
| Base vectorial | Qdrant | Self-hosted en Docker, nodo nativo en n8n, filtrado por metadata |
| ML | scikit-learn (Isolation Forest) | Unsupervised, bajo costo computacional, interpretable via score |
| Orquestación | n8n self-hosted | Manejo de errores, retry, nodos nativos para Qdrant y LLM |
| LLM | OpenAI / Anthropic | Generación de explicaciones con citas verificables |
| Contenedores | Docker + docker-compose | Despliegue local reproducible en un solo comando |
| Migraciones | Alembic | Versionado del schema, rollback seguro |
| Calidad | ruff, black, mypy, pre-commit | Consistencia de estilo y tipado estático |

---

## Despliegue local

### Prerequisitos

- Docker y docker-compose instalados
- Python 3.11+
- Git

### 1. Clonar el repositorio

```bash
git clone git@github.com:francotv99/price_traking_ai.git
cd price_traking_ai
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
```

Editar `.env` y completar las API keys requeridas (ver sección [Variables de entorno](#variables-de-entorno)).

### 3. Levantar la infraestructura

```bash
docker-compose up -d
```

Esto levanta: PostgreSQL (puerto 5433), Qdrant (puerto 6333), n8n (puerto 5678) y la API (puerto 8000).

Verificar que todos los servicios estén saludables:

```bash
docker-compose ps
```

### 4. Aplicar migraciones de base de datos

```bash
# Con el entorno virtual activado
pip install -e ".[dev]"

# Aplicar migraciones
alembic upgrade head
```

### 5. Importar workflows en n8n

1. Abrir `http://localhost:5678` (credenciales: `admin` / `admin`)
2. Ir a **Settings → Import workflow**
3. Importar los tres archivos en orden:
   - `n8n/workflow_1_ingesta.json`
   - `n8n/workflow_2_deteccion_alerta.json`
   - `n8n/workflow_3_reindexacion.json`
4. Activar cada workflow

### 6. Verificar que la API responde

```bash
curl http://localhost:8000/health
```

---

## Variables de entorno

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `DATABASE_URL` | Cadena de conexión PostgreSQL | `postgresql://finup:finup@localhost:5433/finup_db` |
| `QDRANT_HOST` | Host de Qdrant | `localhost` |
| `QDRANT_PORT` | Puerto de Qdrant | `6333` |
| `QDRANT_COLLECTION` | Nombre de la colección vectorial | `crypto_chunks` |
| `ANTHROPIC_API_KEY` | API key de Anthropic (Claude) | `sk-ant-...` |
| `OPENAI_API_KEY` | API key de OpenAI (embeddings + GPT) | `sk-proj-...` |
| `COINGECKO_BASE_URL` | URL base de CoinGecko | `https://api.coingecko.com/api/v3` |
| `COINGECKO_API_KEY` | API key de CoinGecko (opcional, free tier) | *(vacío)* |
| `ETL_PRODUCTS` | Productos a monitorear, separados por coma | `bitcoin,ethereum,solana,cardano` |
| `ETL_LOOKBACK_DAYS` | Días de histórico a descargar por ejecución | `90` |
| `ML_CONTAMINATION` | Proporción esperada de anomalías (Isolation Forest) | `0.05` |
| `ML_LOOKBACK_DAYS` | Ventana de días para el modelo ML | `90` |
| `ML_OPPORTUNITY_DELTA_THRESHOLD` | Delta mínimo para clasificar como OPPORTUNITY | `0.15` |
| `ML_ANOMALY_WINDOW_HOURS` | Ventana temporal para clasificar DATA_ERROR | `1` |
| `N8N_WEBHOOK_URL` | URL base de n8n para webhooks | `http://localhost:5678` |
| `N8N_BASIC_AUTH_USER` | Usuario de n8n | `admin` |
| `N8N_BASIC_AUTH_PASSWORD` | Contraseña de n8n | `admin` |
| `API_HOST` | Host de la API | `0.0.0.0` |
| `API_PORT` | Puerto de la API | `8000` |
| `LOG_LEVEL` | Nivel de logging | `INFO` |
| `ENVIRONMENT` | Entorno de ejecución | `development` |

---

## Ejecución de pruebas, linter y verificador de tipos

### Pruebas unitarias

```bash
# Ejecutar todas las pruebas
pytest

# Con cobertura
pytest --cov=. --cov-report=term-missing

# Solo pruebas unitarias
pytest -m unit

# Solo pruebas lentas (omitir en CI rápido)
pytest -m "not slow"
```

### Linter y formateo

```bash
# Verificar estilo con ruff
ruff check .

# Formatear con black
black .

# Verificar imports con isort
isort --check-only .

# Aplicar todos los fixers automáticos
ruff check --fix . && black . && isort .
```

### Verificador de tipos

```bash
mypy api/ etl/ ml/ rag/
```

### Pre-commit (ejecuta todo lo anterior en cada commit)

```bash
pre-commit install
pre-commit run --all-files
```

---

## Ejecución manual del ETL

```bash
# Disparar ingesta de todos los productos activos
curl -X POST http://localhost:8000/etl/run \
  -H "Content-Type: application/json" \
  -d '{}'
```

Respuesta esperada:

```json
{
  "status": "ok",
  "products_processed": 4,
  "records_inserted": 91,
  "records_skipped": 0,
  "errors": [],
  "triggered_at": "2026-04-16T10:00:00Z"
}
```

Verificar que los datos llegaron a PostgreSQL:

```bash
docker exec -it finup_postgres psql -U finup -d finup_db \
  -c "SELECT product_id, COUNT(*), MIN(recorded_at), MAX(recorded_at) FROM price_records GROUP BY product_id;"
```

---

## Endpoint conversacional

Consultas libres sobre cualquier producto registrado. No requiere que n8n esté corriendo.

```bash
curl -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "bitcoin",
    "question": "¿Cuál es el market cap actual de bitcoin?"
  }'
```

Respuesta esperada:

```json
{
  "product_id": "bitcoin",
  "question": "¿Cuál es el market cap actual de bitcoin?",
  "answer": "Según los datos indexados, el market cap de Bitcoin es...",
  "sources": ["market_data", "description"],
  "answered_at": "2026-04-16T..."
}
```

> Requiere que el corpus esté indexado en Qdrant. Ejecutar `POST /rag/reindex` primero si es la primera vez.

También disponible en el Swagger: `http://localhost:8000/docs`

---

## Disparar una alerta de prueba end-to-end

```bash
# 1. Correr detección de anomalías sobre bitcoin
curl -X POST http://localhost:8000/ml/detect \
  -H "Content-Type: application/json" \
  -d '{"product_id": "bitcoin", "lookback_days": 90}'
```

Si el modelo detecta una anomalía, n8n recibirá la respuesta y ejecutará automáticamente:
1. Búsqueda semántica en Qdrant sobre el corpus de bitcoin
2. Generación de explicación con el LLM usando el prompt versionado en `prompts/alert_explanation.txt`
3. Envío de notificación por Telegram

Para verificar que el corpus de Qdrant está indexado antes de la prueba:

```bash
# Reindexar corpus de bitcoin
curl -X POST http://localhost:8000/rag/reindex \
  -H "Content-Type: application/json" \
  -d '{"product_id": "bitcoin"}'
```

---

## Modelo de datos

### Tabla `products`
Registro de los activos monitoreados. `external_id` es el identificador de CoinGecko (ej. `"bitcoin"`).

### Tabla `price_records`
Histórico de precios. El constraint `UNIQUE(product_id, recorded_at)` garantiza idempotencia: re-ejecutar el ETL no duplica registros (`INSERT ... ON CONFLICT DO NOTHING`).

### Tabla `anomaly_events`
Registro de cada anomalía detectada. Almacena el score del modelo, el precio actual vs esperado, el delta porcentual, la categoría (`OPPORTUNITY` o `DATA_ERROR`) y la explicación generada por el LLM.

Ver diagrama ERD completo en [docs/diagrams/erd.png](docs/diagrams/erd.png).

---

## Limitaciones conocidas y trade-offs aceptados

| Limitación | Descripción |
|------------|-------------|
| CoinGecko free tier | Límite de ~30 requests/min. El fetcher implementa retry con backoff exponencial, pero en producción con más productos se requiere el tier Pro. |
| Isolation Forest sin reentrenamiento incremental | El modelo se entrena en cada llamada a `/ml/detect` sobre los últimos N días. No hay persistencia del modelo entrenado. Aceptable para el volumen actual (4 productos). |
| Clasificación heurística de anomalías | Los umbrales de `delta_pct > 40%` y `elapsed_hours` son heurísticos, no aprendidos. En mercados extremadamente volátiles pueden generar falsos positivos. |
| Corpus sin reseñas de usuarios | El corpus RAG se construye desde la API de CoinGecko (descripción, market data, community). No incluye reseñas externas. |
| n8n como punto único de orquestación | Si n8n no está disponible, el pipeline se detiene aunque el backend esté operativo. Mitigado con healthchecks en docker-compose. |
| Sin autenticación en la API | Los endpoints no requieren autenticación. En producción se requiere API key o JWT. |

---

## Estructura del proyecto

```
├── api/            FastAPI app principal y configuración
├── etl/            Ingesta de datos desde CoinGecko
├── ml/             Detección de anomalías con Isolation Forest
├── rag/            Construcción de corpus y reindexación en Qdrant
├── n8n/            Workflows exportados en JSON
├── migrations/     Migraciones de base de datos con Alembic
├── prompts/        Prompts del LLM versionados
├── tests/          Pruebas unitarias con pytest
├── docs/           Diagramas y documento de decisiones técnicas
├── infra/          Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── .env.example
```
