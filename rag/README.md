# RAG Module

Retrieval-Augmented Generation for price anomaly explanations.

## Overview

The RAG module handles:
- Fetching product metadata from CoinGecko
- Building document corpus (descriptions, market data, community)
- Chunking documents for vector storage
- Indexing chunks in Qdrant
- Retrieving relevant context for explanations

## Endpoints

### POST /rag/reindex

Reindex corpus for one product or all products.

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

## Corpus Structure

Per-product corpus includes:
- Project description from CoinGecko
- Market data (market cap, volume, dominance)
- Community metrics (Reddit, Twitter)
- Links and official pages

## Qdrant Collection

- **Collection name:** `product_corpus`
- **Metadata per chunk:**
  - `product_id` - Cryptocurrency ID
  - `source` - Content source (description, market_data, community, etc.)
  - `indexed_at` - Indexing timestamp

## Module Structure

- `router.py` - FastAPI endpoint
- `corpus.py` - Document fetching and chunking
- `models.py` - Data models (Document, ChunkResult)

## LLM Prompt

See `../prompts/alert_explanation.txt` for the system prompt used to generate explanations with RAG context.

## Implementation Status

- [ ] corpus.py
- [ ] router.py
- [ ] models.py
- [ ] Unit tests
