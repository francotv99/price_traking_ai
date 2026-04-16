# FinUp Price Tracker — Instrucciones Completas del Proyecto
> Prueba Técnica AI Engineer · FU-RH-PT-AIE-001 · v1.0

---

## 1. Resumen del sistema

Sistema de monitoreo de precios de criptomonedas con alertas inteligentes. Monitorea precios desde CoinGecko, detecta anomalías con ML y genera explicaciones en lenguaje natural usando RAG.

**Productos monitoreados:** bitcoin, ethereum, solana, cardano  
**Fuente de datos:** CoinGecko API (gratuita, sin autenticación)

---

## 2. Stack tecnológico

| Categoría | Tecnología | Justificación |
|-----------|-----------|---------------|
| Lenguaje | Python 3.11+ | Requerido por el documento |
| API HTTP | FastAPI | Requerido por el documento |
| Base de datos | PostgreSQL 15+ | Persistencia del histórico de precios |
| Base vectorial | Qdrant | Almacenamiento de embeddings del corpus RAG |
| ML | scikit-learn (Isolation Forest) | Detección de anomalías en series de tiempo |
| LLM | Anthropic Claude / OpenAI | Generación de explicaciones |
| Orquestación | n8n self-hosted | Requerido por el documento |
| Contenedores | Docker + docker-compose | Despliegue local reproducible |
| Migraciones | Alembic | Versionado del schema de BD |
| Calidad | ruff, black, mypy, pre-commit | Requerido por el documento |

---

## 3. Arquitectura del sistema

### Flujo completo de punta a punta

```
[Cron cada 6h]
      ↓
Workflow 1: Ingesta
  n8n → POST /etl/run
  backend → CoinGecko API → PostgreSQL
      ↓ webhook al terminar
Workflow 2: Detección y alerta
  n8n → POST /ml/detect
  backend → lee histórico PostgreSQL → corre Isolation Forest
      ↓ si anomalía = true
  n8n → Qdrant node (busca chunks del producto)
  n8n → LLM node (genera explicación con citas)
  n8n → envía notificación (email/Slack)
      ↓ webhook
Workflow 3: Reindexación RAG (reactiva)
  n8n → reindexar solo el producto afectado en Qdrant

[Cron semanal aparte]
Workflow 3: Reindexación RAG (preventiva)
  n8n → reindexar TODOS los productos en Qdrant
```

### Separación de responsabilidades

| Tarea | Quién |
|-------|-------|
| Cuándo ejecutar cada proceso | n8n |
| Retry y manejo de errores de flujo | n8n |
| Envío de notificaciones | n8n |
| Búsqueda semántica en Qdrant | n8n (nodo nativo) |
| Llamada al LLM | n8n (nodo nativo) |
| Fetch y parseo de CoinGecko | Backend (Python) |
| Persistencia en PostgreSQL | Backend (Python) |
| Modelo ML de detección | Backend (Python) |
| Generación de embeddings | n8n (nodo embeddings) |

---

## 4. Estructura de directorios

```
finup-price-tracker/
├── etl/                    # Ingesta de datos
│   ├── router.py           # endpoint POST /etl/run
│   ├── fetcher.py          # llama a CoinGecko API
│   ├── parser.py           # normaliza respuesta al modelo interno
│   ├── repository.py       # INSERT en PostgreSQL
│   ├── models.py           # PriceRecord, ETLResult
│   └── README.md
├── ml/                     # Detección de anomalías
│   ├── router.py           # endpoint POST /ml/detect
│   ├── detector.py         # Isolation Forest sobre serie de tiempo
│   ├── repository.py       # lee histórico de PostgreSQL
│   ├── models.py           # AnomalyResult, AnomalyCategory
│   ├── evaluation.ipynb    # evaluación cuantitativa del modelo
│   └── README.md
├── rag/                    # Corpus y reindexación
│   ├── router.py           # endpoint POST /rag/reindex
│   ├── corpus.py           # fetch de descripción y datos de CoinGecko
│   ├── models.py           # Document, ChunkResult
│   └── README.md
├── api/                    # FastAPI principal
│   ├── main.py             # app FastAPI, registra routers
│   ├── dependencies.py     # inyección de dependencias
│   ├── settings.py         # configuración desde .env (pydantic-settings)
│   └── README.md
├── n8n/                    # Workflows exportados
│   ├── workflow_1_ingesta.json
│   ├── workflow_2_deteccion_alerta.json
│   ├── workflow_3_reindexacion.json
│   └── README.md
├── infra/                  # Docker y configuración
│   └── README.md
├── migrations/             # Alembic
│   ├── versions/
│   ├── env.py
│   └── README.md
├── tests/                  # Pruebas unitarias
│   ├── test_etl_parser.py
│   ├── test_ml_detector.py
│   ├── test_rag_retrieval.py
│   └── README.md
├── docs/                   # Diagramas y decisiones técnicas
│   ├── diagrams/
│   │   ├── architecture.png
│   │   ├── alert_sequence.png
│   │   ├── rag_pipeline.png
│   │   └── erd.png
│   ├── decisions.md        # Trade-offs y justificaciones
│   └── README.md
├── prompts/                # Prompts del LLM versionados
│   ├── alert_explanation.txt
│   └── README.md
├── docker-compose.yml
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

---

## 5. Base de datos PostgreSQL

### Tabla principal: price_records

```sql
CREATE TABLE price_records (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id    VARCHAR(100) NOT NULL,        -- ej: "bitcoin"
  price_usd     NUMERIC(20, 8) NOT NULL,      -- precio en USD
  recorded_at   TIMESTAMPTZ NOT NULL,          -- timestamp del precio
  source        VARCHAR(50) NOT NULL,          -- "coingecko"
  raw_payload   JSONB,                         -- respuesta cruda de la API
  created_at    TIMESTAMPTZ DEFAULT NOW(),

  UNIQUE (product_id, recorded_at)             -- garantiza idempotencia
);
```

### Tabla: products

```sql
CREATE TABLE products (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  external_id   VARCHAR(100) UNIQUE NOT NULL,  -- ej: "bitcoin"
  name          VARCHAR(200) NOT NULL,          -- ej: "Bitcoin"
  source        VARCHAR(50) NOT NULL,           -- "coingecko"
  is_active     BOOLEAN DEFAULT TRUE,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);
```

### Tabla: anomaly_events

```sql
CREATE TABLE anomaly_events (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id      VARCHAR(100) NOT NULL,
  detected_at     TIMESTAMPTZ NOT NULL,
  category        VARCHAR(50) NOT NULL,         -- "OPPORTUNITY" o "DATA_ERROR"
  score           NUMERIC(5, 4) NOT NULL,        -- score del modelo ML
  price_actual    NUMERIC(20, 8) NOT NULL,
  price_expected  NUMERIC(20, 8) NOT NULL,
  delta_pct       NUMERIC(10, 4) NOT NULL,
  explanation     TEXT,                          -- explicación generada por RAG
  notified_at     TIMESTAMPTZ,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 6. Endpoints del backend

### POST /etl/run
Ejecuta el proceso de ingesta para todos los productos activos.

**Request:**
```json
{}
```

**Response exitosa:**
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

**Lo que hace internamente:**
1. Lee lista de productos activos desde PostgreSQL
2. Por cada producto llama a CoinGecko `/coins/{id}/market_chart`
3. Parsea la respuesta al modelo `PriceRecord`
4. Hace `INSERT ... ON CONFLICT DO NOTHING` en `price_records`
5. Maneja paginación, rate limiting y errores transitorios
6. Devuelve resumen a n8n

---

### POST /ml/detect
Corre el modelo de detección de anomalías sobre el histórico de precios.

**Request:**
```json
{
  "product_id": "bitcoin",
  "lookback_days": 90
}
```

**Response sin anomalía:**
```json
{
  "anomaly": false,
  "product_id": "bitcoin"
}
```

**Response con anomalía:**
```json
{
  "anomaly": true,
  "product_id": "bitcoin",
  "category": "OPPORTUNITY",
  "score": 0.92,
  "price_actual": 98000.00,
  "price_expected": 67000.00,
  "delta_pct": 46.27
}
```

**Lo que hace internamente:**
1. Lee los últimos N días de `price_records` para ese producto
2. Corre Isolation Forest sobre la serie de tiempo
3. Clasifica la anomalía: `OPPORTUNITY` o `DATA_ERROR`
4. Guarda el evento en `anomaly_events`
5. Devuelve el resultado a n8n

---

### POST /rag/reindex
Reindexar el corpus de un producto o todos los productos en Qdrant.

**Request reindexar uno:**
```json
{
  "product_id": "bitcoin"
}
```

**Request reindexar todos:**
```json
{
  "product_id": null
}
```

**Response:**
```json
{
  "status": "ok",
  "products_reindexed": ["bitcoin"],
  "chunks_indexed": 34,
  "errors": []
}
```

**Lo que hace internamente:**
1. Llama a CoinGecko `/coins/{id}` para obtener descripción y datos
2. Segmenta el texto en chunks
3. Devuelve chunks a n8n para que el nodo de embeddings los procese
4. n8n los indexa en Qdrant

---

## 7. Los 3 workflows de n8n

### Workflow 1 — Ingesta programada

**Propósito:** Recolectar precios de CoinGecko y persistirlos en PostgreSQL.  
**Trigger:** Cron cada 6 horas.  
**Dependencias:** Backend `/etl/run`, PostgreSQL.

```
Cron trigger (cada 6h)
  → HTTP Request node: POST /etl/run
  → IF node: ¿status = "ok"?
      → SÍ: Execute Workflow node → dispara Workflow 2
      → NO: Send notification node → alerta de error
  → Error handler: retry 3x con backoff
```

---

### Workflow 2 — Detección y alerta

**Propósito:** Detectar anomalías en precios y notificar al usuario con explicación generada por RAG + LLM.  
**Trigger:** Webhook desde Workflow 1.  
**Dependencias:** Backend `/ml/detect`, Qdrant, LLM (Claude/OpenAI), email/Slack.

```
Webhook trigger (recibe de W1)
  → HTTP Request node: POST /ml/detect
  → IF node: ¿anomaly = true?
      → NO: termina silenciosamente
      → SÍ:
          → Qdrant node: busca chunks del producto afectado
          → LLM node: genera explicación con citas usando prompt versionado
          → Send Email / Slack node: envía notificación con explicación
          → Execute Workflow node: dispara Workflow 3
  → Error handler: retry 3x + log del error
```

---

### Workflow 3 — Reindexación del corpus RAG

**Propósito:** Mantener el corpus de Qdrant actualizado con información fresca de los productos.  
**Trigger A (reactivo):** Webhook desde Workflow 2 cuando hay anomalía.  
**Trigger B (preventivo):** Cron semanal.  
**Dependencias:** Backend `/rag/reindex`, CoinGecko API, Qdrant, modelo de embeddings.

```
Trigger A: Webhook desde W2 (product_id específico)
Trigger B: Cron semanal (todos los productos)
  → HTTP Request node: POST /rag/reindex
  → Loop node: por cada producto
      → Embeddings node: genera vectores de los chunks
      → Qdrant node: Insert Documents (reemplaza los anteriores)
  → Error handler: retry por producto fallido + log
```

---

## 8. Modelo ML — Isolation Forest

### ¿Por qué Isolation Forest?
- Funciona bien con series de tiempo de precios
- No requiere datos etiquetados (unsupervised)
- Interpretable: devuelve un score de anomalía
- Bajo costo computacional
- Disponible en scikit-learn

### Dos categorías de anomalía obligatorias

```python
class AnomalyCategory(str, Enum):
    OPPORTUNITY = "OPPORTUNITY"  # variación real de mercado
    DATA_ERROR  = "DATA_ERROR"   # sospecha de error en la fuente

# Criterio de clasificación:
# - delta > 40% en < 1h  → probablemente DATA_ERROR
# - delta > 40% en > 6h  → probablemente OPPORTUNITY
```

### Evaluación del modelo
- Generar datos sintéticos con anomalías conocidas
- Medir precisión, recall y F1
- Documentar en `ml/evaluation.ipynb`

---

## 9. Corpus RAG por producto

### Fuentes de datos desde CoinGecko

```
GET /coins/{id}?localization=false&community_data=true

Extraer:
  - description.en          → descripción del proyecto
  - market_data             → datos de mercado actuales
  - community_data          → reddit_subscribers, twitter_followers
  - links.homepage          → sitio oficial
  - links.subreddit_url     → comunidad Reddit
```

### Estructura del corpus por producto

```
bitcoin/
  - descripcion_proyecto.txt     (descripción de CoinGecko)
  - datos_mercado.txt            (market cap, volumen, etc.)
  - comunidad.txt                (datos de comunidad)
  - faqs.txt                     (preguntas frecuentes generadas)
```

### Colección en Qdrant

```
collection: "product_corpus"
metadata por chunk:
  - product_id: "bitcoin"
  - source: "description" | "market_data" | "community"
  - indexed_at: timestamp
```

---

## 10. Prompts versionados

### prompts/alert_explanation.txt

```
Eres un analista financiero experto en criptomonedas.

Se detectó una anomalía de precio para {product_id}:
- Precio actual: ${price_actual}
- Precio esperado: ${price_expected}  
- Variación: {delta_pct}%
- Categoría: {category}

Contexto recuperado del corpus del producto:
{retrieved_chunks}

Genera una explicación clara y accionable que:
1. Explique la variación detectada
2. Cite las fuentes del contexto recuperado
3. Indique si la evidencia es suficiente para concluir algo
4. Si la evidencia es insuficiente, decláralo explícitamente

IMPORTANTE: Solo afirmes lo que puedas respaldar con el contexto provisto.
```

---

## 11. Variables de entorno (.env.example)

```env
# PostgreSQL
DATABASE_URL=postgresql://finup:finup@localhost:5432/finup_db

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=product_corpus

# LLM
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here

# CoinGecko
COINGECKO_BASE_URL=https://api.coingecko.com/api/v3
COINGECKO_API_KEY=                        # opcional en free tier

# ETL
ETL_PRODUCTS=bitcoin,ethereum,solana,cardano
ETL_LOOKBACK_DAYS=90
ETL_INTERVAL_DAYS=1

# ML
ML_CONTAMINATION=0.05                     # % esperado de anomalías
ML_LOOKBACK_DAYS=90
ML_OPPORTUNITY_DELTA_THRESHOLD=0.15       # 15% de variación mínima

# n8n
N8N_WEBHOOK_URL=http://localhost:5678
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=your_password

# API
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

---

## 12. docker-compose.yml

```yaml
version: "3.9"

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: finup
      POSTGRES_PASSWORD: finup
      POSTGRES_DB: finup_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

  n8n:
    image: n8nio/n8n:latest
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=admin
      - N8N_HOST=localhost
      - WEBHOOK_URL=http://localhost:5678
    volumes:
      - n8n_data:/home/node/.n8n

  api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - postgres
      - qdrant

volumes:
  postgres_data:
  qdrant_data:
  n8n_data:
```

---

## 13. Orden de implementación recomendado

```
Fase 1 — Infraestructura base
  ✅ docker-compose con PostgreSQL + Qdrant + n8n
  ✅ estructura de carpetas del proyecto
  ✅ pyproject.toml con ruff, black, mypy
  ✅ .env.example completo
  ✅ migraciones Alembic con las 3 tablas

Fase 2 — ETL
  ✅ fetcher.py → llama a CoinGecko
  ✅ parser.py → normaliza a PriceRecord
  ✅ repository.py → INSERT idempotente en PostgreSQL
  ✅ router.py → endpoint POST /etl/run
  ✅ tests/test_etl_parser.py

Fase 3 — Modelo ML
  ✅ detector.py → Isolation Forest
  ✅ repository.py → lee histórico de PostgreSQL
  ✅ router.py → endpoint POST /ml/detect
  ✅ ml/evaluation.ipynb → evaluación con datos sintéticos
  ✅ tests/test_ml_detector.py

Fase 4 — RAG
  ✅ corpus.py → fetch descripción de CoinGecko
  ✅ router.py → endpoint POST /rag/reindex
  ✅ prompts/alert_explanation.txt
  ✅ tests/test_rag_retrieval.py

Fase 5 — n8n workflows
  ✅ Workflow 1: ingesta programada
  ✅ Workflow 2: detección + alerta
  ✅ Workflow 3: reindexación RAG
  ✅ exportar los 3 como JSON en /n8n

Fase 6 — Documentación y calidad
  ✅ README raíz completo
  ✅ READMEs por subdirectorio
  ✅ 4 diagramas en /docs/diagrams
  ✅ docs/decisions.md con trade-offs
  ✅ pasar ruff, black, mypy sin errores
  ✅ video demo de 5 minutos
```

---

## 14. Checklist de entregables obligatorios

```
□ Repositorio Git con código fuente completo
□ README raíz con todos los elementos requeridos
□ READMEs en cada subdirectorio relevante
□ Workflows n8n exportados en JSON en /n8n
□ 4 diagramas en PNG con fuente editable en /docs/diagrams
□ ml/evaluation.ipynb con métricas del modelo
□ docs/decisions.md con decisiones y trade-offs
□ Video demo máximo 5 minutos (Loom o MP4)
□ docker-compose.yml funcional
□ tests/ con pytest sobre ETL parser, detector ML y RAG retrieval
□ pyproject.toml con ruff, black, mypy configurados
□ .env.example completo
□ prompts/ con prompts versionados
□ migrations/ con Alembic versionado
```

---

## 15. Criterios de evaluación (referencia de prioridades)

| Criterio | Peso | Prioridad |
|----------|------|-----------|
| Arquitectura y diseño | 20% | 🔴 Alta |
| Calidad de código | 20% | 🔴 Alta |
| Documentación y READMEs | 15% | 🔴 Alta |
| Modelo ML | 15% | 🟡 Media |
| RAG y base vectorial | 15% | 🟡 Media |
| ETL, n8n y automatización | 10% | 🟡 Media |
| Pruebas e higiene del repo | 5% | 🟢 Normal |

> ⚠️ Arquitectura + calidad de código + documentación = **55% del total**.
> Siempre priorizar calidad sobre velocidad de implementación.