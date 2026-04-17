"""Data models for RAG corpus reindexing."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class ReindexRequest(BaseModel):
    product_id: str | None = Field(
        default=None,
        description="If null, reindex all configured products; otherwise only one product",
    )


class ChunkResult(BaseModel):
    product_id: str
    source: str
    chunk_id: str
    text: str
    metadata: dict[str, Any]


class ProductReindexResult(BaseModel):
    product_id: str
    chunks: list[ChunkResult]


class ReindexResponse(BaseModel):
    status: str
    products_reindexed: list[str]
    chunks_indexed: int
    errors: list[str]
    products: list[ProductReindexResult]
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class QueryRequest(BaseModel):
    product_id: str | None = Field(default=None, description="CoinGecko ID (optional — inferred from question if omitted)")
    question: str = Field(..., min_length=3, description="Free-form question about the product")


class QueryResponse(BaseModel):
    product_ids: list[str]
    question: str
    answer: str
    sources: list[str] = Field(description="Corpus sections used to build the answer")
    answered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
