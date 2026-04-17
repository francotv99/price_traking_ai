# RAG Module

Retrieval-Augmented Generation for price anomaly explanations and conversational queries.

## Overview

The RAG module handles:
- Fetching product metadata from CoinGecko
- Building document corpus (descriptions, market data, community data, links)
- Chunking documents with overlap for semantic coherence
- Returning chunks to n8n for embedding and Qdrant indexing
- Semantic retrieval and LLM-based answer generation for conversational queries

## Endpoints

### POST /rag/reindex

Builds and returns text chunks for one product or all products. n8n consumes
this response to generate embeddings (OpenAI) and index them in Qdrant.

**Request (single product):**
```json
{
  "product_id": "bitcoin"
}
```

**Request (all products):**
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

### POST /rag/query

Answers a free-form question about a registered product using RAG.
Does not require n8n — calls OpenAI and Qdrant directly.

**Request:**
```json
{
  "product_id": "bitcoin",
  "question": "¿Cuál es el market cap actual de bitcoin?"
}
```

**Response:**
```json
{
  "product_id": "bitcoin",
  "question": "¿Cuál es el market cap actual de bitcoin?",
  "answer": "Según los datos indexados, el market cap de Bitcoin es...",
  "sources": ["market_data", "description"],
  "answered_at": "2026-04-16T..."
}
```

> If no chunks are indexed for the product, returns an actionable message
> instead of hallucinating an answer.

## Corpus Structure

Per-product corpus includes four sections extracted from CoinGecko `/coins/{id}`:

| Section | CoinGecko field | Description |
|---------|----------------|-------------|
| `description` | `description.en` | Project overview |
| `market_data` | `market_data` | Price, market cap, volume, ATH |
| `community` | `community_data` | Reddit subscribers, Twitter followers |
| `links` | `links` | Official homepage, subreddit URL |

Chunking parameters: **800 chars per chunk, 80 char overlap**.

## Qdrant Collection

- **Collection name:** `crypto_chunks`
- **Metadata per chunk:**
  - `product_id` — cryptocurrency ID (e.g. `"bitcoin"`)
  - `source` — content section (`description`, `market_data`, `community`, `links`)
  - `indexed_at` — indexing timestamp (ISO 8601)

## Prompts

- `prompts/alert_explanation.txt` — used by n8n LLM node for anomaly alerts
- `prompts/conversational_query.txt` — used by `/rag/query` for free-form questions

Both prompts include an explicit anti-hallucination guard: if the retrieved
context is insufficient, the LLM is instructed to declare it explicitly.

## Module Structure

- `router.py` — FastAPI endpoints (`/reindex`, `/query`)
- `corpus.py` — CoinGecko fetching and text chunking
- `retriever.py` — Embedding generation, Qdrant search, LLM answer generation
- `models.py` — Pydantic models for requests and responses

## Implementation Status

- [x] corpus.py
- [x] retriever.py
- [x] router.py
- [x] models.py
- [x] Unit tests
