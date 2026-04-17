# Decisiones técnicas y trade-offs

## 1. Isolation Forest como modelo de detección de anomalías

**Decisión:** Se usa `IsolationForest` de scikit-learn con `n_estimators=200` y `contamination=0.05`.

**Alternativas consideradas:** Z-score, LSTM autoencoder, DBSCAN.

**Por qué Isolation Forest:**
- No requiere datos etiquetados (unsupervised) — no existe un dataset de anomalías de precios crypto pre-etiquetado.
- Funciona bien con series de tiempo no estacionarias como precios de criptomonedas.
- Bajo costo computacional: entrena en milisegundos sobre 90 días de datos.
- Devuelve un `decision_function` que usamos como score de confianza.

**Por qué no Z-score:** Asume distribución normal. Los precios crypto tienen colas pesadas (fat tails) que generan muchos falsos positivos con Z-score.

**Por qué no LSTM:** Requiere datos etiquetados o ventanas de entrenamiento largas. Excesivo para el volumen de datos actual y agrega complejidad de infraestructura (GPU, TensorFlow/PyTorch).

**Trade-off:** Isolation Forest no distingue bien entre anomalías de magnitud pequeña. Se mitiga con el soft guard: si `delta_pct < 15%`, la anomalía se reclasifica como `DATA_ERROR` aunque el modelo la marque como `OPPORTUNITY`.

---

## 2. Clasificación en dos categorías: OPPORTUNITY vs DATA_ERROR

**Decisión:** Toda anomalía se clasifica en una de dos categorías usando tiempo transcurrido y magnitud del delta.

```
delta > 40% en < 1h  → DATA_ERROR  (probablemente error de la fuente)
delta > 40% en >= 6h → OPPORTUNITY (movimiento real de mercado)
delta < threshold     → DATA_ERROR  (soft guard, no es relevante como oportunidad)
```

**Por qué:** Una caída o subida de 50% en un minuto es casi siempre un spike de datos o error de la API. La misma variación en 6+ horas tiene mucha más probabilidad de ser un movimiento real de mercado.

**Trade-off:** El umbral de 1h/6h es heurístico. En mercados de alta volatilidad (ej. flash crash) puede clasificar un evento real como `DATA_ERROR`. El threshold es configurable via `ML_ANOMALY_WINDOW_HOURS` en `.env`.

---

## 3. RAG: el backend genera chunks, n8n genera embeddings

**Decisión:** El endpoint `/rag/reindex` devuelve chunks de texto plano. n8n es quien los vectoriza e indexa en Qdrant usando su nodo de embeddings nativo.

**Por qué:**
- Evita tener una dependencia de modelo de embeddings en el backend Python.
- Permite cambiar el modelo de embeddings (OpenAI, local, etc.) solo desde n8n sin tocar el backend.
- El `CorpusBuilder` aplica chunking con overlap (800 chars / 80 overlap) para no partir contexto semántico entre chunks.

**Trade-off:** La respuesta de `/rag/reindex` puede ser grande si hay muchos productos. Aceptable porque es un proceso batch, no en el camino crítico de latencia.

---

## 4. Qdrant como base vectorial

**Decisión:** Qdrant self-hosted via Docker como almacenamiento de vectores del corpus RAG.

**Alternativas consideradas:** Pinecone, Weaviate, pgvector.

**Por qué Qdrant:**
- Self-hosted: corre en el mismo `docker-compose`, sin dependencias externas ni API keys.
- n8n tiene nodo nativo para Qdrant (insert, search, delete), lo que simplifica el workflow.
- Soporta metadata filtering por `product_id` y `source`, útil para recuperar solo chunks del producto afectado.

**Por qué no pgvector:** Hubiera sido más simple (ya usamos PostgreSQL), pero n8n no tiene nodo nativo para pgvector, lo que requeriría SQL custom en cada paso del workflow.

**Por qué no Pinecone:** Servicio externo gestionado, requiere API key y tiene costos. Para un sistema self-hosted en prueba técnica no aplica.

---

## 5. PostgreSQL como base de datos principal

**Decisión:** PostgreSQL 15 con constraint `UNIQUE(product_id, recorded_at)` para garantizar idempotencia en el ETL.

**Por qué:**
- El `INSERT ... ON CONFLICT DO NOTHING` permite re-ejecutar el ETL sin duplicar datos, lo que es crítico cuando n8n reintenta el workflow.
- `TIMESTAMPTZ` para todos los campos de tiempo garantiza consistencia en zonas horarias.
- `JSONB` en `raw_payload` para guardar la respuesta cruda de CoinGecko sin perder información.

**Trade-off:** Para series de tiempo puras, TimescaleDB sería más eficiente en queries de ventana temporal. Se usa PostgreSQL estándar por simplicidad del stack y porque el volumen de datos (4 productos × 90 días) no justifica la complejidad adicional.

---

## 6. Notificaciones via Telegram en n8n

**Decisión:** El Workflow 2 envía notificaciones de anomalías via Telegram usando el nodo nativo de n8n.

**Alternativas consideradas:** Email (SMTP), Slack.

**Por qué Telegram:**
- El nodo de Telegram en n8n no requiere configuración de servidor SMTP ni workspace de Slack.
- Fácil de configurar con un bot token y chat ID.
- Permite recibir alertas en tiempo real en el móvil.

**Trade-off:** Telegram no es la herramienta estándar en entornos enterprise. El nodo de n8n es intercambiable por Slack o Email sin cambios en el backend.

---

## 7. CoinGecko free tier sin autenticación

**Decisión:** Se usa el tier gratuito de CoinGecko API sin API key. El fetcher implementa retry con backoff exponencial para manejar el rate limit (429).

**Por qué:**
- El sistema monitorea solo 4 productos con frecuencia de 6 horas, muy por debajo del límite del free tier.
- El fetcher acepta `api_key` opcional: si se provee en `.env`, se envía en cada request para mayor límite.

**Trade-off:** En producción con más productos o mayor frecuencia, se requeriría el tier Pro de CoinGecko. El parámetro `COINGECKO_API_KEY` en `.env.example` está preparado para eso.
