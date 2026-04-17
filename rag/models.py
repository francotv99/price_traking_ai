"""Data models for RAG corpus reindexing."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ReindexRequest(BaseModel):
    """Request payload for RAG reindex endpoint."""

    product_id: Optional[str] = Field(
        default=None,
        description="If null, reindex all configured products; otherwise only one product",
    )


class ChunkResult(BaseModel):
    """Single chunk entry returned for embedding/indexing in n8n."""

    product_id: str
    source: str
    chunk_id: str
    text: str
    metadata: dict[str, Any]


class ProductReindexResult(BaseModel):
    """Chunks returned for one product."""

    product_id: str
    chunks: list[ChunkResult]


class ReindexResponse(BaseModel):
    """RAG reindex response consumed by n8n."""

    status: str
    products_reindexed: list[str]
    chunks_indexed: int
    errors: list[str]
    products: list[ProductReindexResult]
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class QueryRequest(BaseModel):
    """Request payload for the conversational RAG endpoint."""

    product_id: str = Field(..., description="Product to query (e.g. bitcoin)")
    question: str = Field(..., min_length=3, description="Free-form question about the product")


class QueryResponse(BaseModel):
    """Response from the conversational RAG endpoint."""

    product_id: str
    question: str
    answer: str
    sources: list[str] = Field(description="Corpus sections used to build the answer")
    answered_at: datetime = Field(default_factory=datetime.utcnow)
