"""FastAPI router for RAG endpoints."""
from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_settings
from etl.fetcher import CoinGeckoFetcher
from rag.corpus import CorpusBuilder
from rag.models import QueryRequest, QueryResponse, ReindexRequest, ReindexResponse
from rag.retriever import RAGRetriever

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag", tags=["rag"])


@router.post("/reindex", response_model=ReindexResponse)
async def reindex_corpus(payload: ReindexRequest, settings=Depends(get_settings)) -> ReindexResponse:
    """Build corpus chunks for one or all products.

    This endpoint is designed for n8n consumption. It returns chunks so n8n can:
    1) generate embeddings
    2) insert/update vectors in Qdrant
    """
    products = [payload.product_id] if payload.product_id else settings.etl_products_list
    builder = CorpusBuilder()

    products_results = []
    products_reindexed = []
    errors: list[str] = []

    qdrant_url = f"http://{settings.qdrant_host}:{settings.qdrant_port}"

    try:
        async with CoinGeckoFetcher(
            base_url=settings.coingecko_base_url,
            api_key=settings.coingecko_api_key,
        ) as fetcher, httpx.AsyncClient(timeout=15) as qdrant_client:
            for product_id in products:
                try:
                    # Delete stale chunks for this product before reindexing.
                    await qdrant_client.post(
                        f"{qdrant_url}/collections/{settings.qdrant_collection}/points/delete",
                        json={"filter": {"must": [{"key": "product_id", "match": {"value": product_id}}]}},
                    )
                    result = await builder.build_for_product(product_id=product_id, fetcher=fetcher)
                    products_results.append(result)
                    products_reindexed.append(product_id)
                except (httpx.HTTPError, OSError, RuntimeError) as exc:
                    msg = f"Failed to reindex {product_id}: {exc}"
                    logger.exception(msg)
                    errors.append(msg)

        total_chunks = sum(len(result.chunks) for result in products_results)

        return ReindexResponse(
            status="ok" if not errors else "partial",
            products_reindexed=products_reindexed,
            chunks_indexed=total_chunks,
            errors=errors,
            products=products_results,
        )

    except Exception as exc:
        logger.exception("RAG reindex failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG reindex failed: {exc}",
        ) from exc


@router.post("/query", response_model=QueryResponse)
async def conversational_query(
    payload: QueryRequest,
    settings=Depends(get_settings),
) -> QueryResponse:
    """Answer a free-form question about a registered product using RAG.

    Generates an embedding for the question, retrieves semantically similar
    chunks from Qdrant filtered by product, and calls the LLM with the
    versioned prompt from prompts/conversational_query.txt.

    If no chunks are indexed for the product, returns an actionable message
    instead of hallucinating an answer.
    """
    if not settings.openai_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY is not configured.",
        )

    retriever = RAGRetriever(
        qdrant_host=settings.qdrant_host,
        qdrant_port=settings.qdrant_port,
        qdrant_collection=settings.qdrant_collection,
        openai_api_key=settings.openai_api_key,
    )

    try:
        answer, sources = await retriever.query(
            product_id=payload.product_id,
            question=payload.question,
        )
        return QueryResponse(
            product_id=payload.product_id,
            question=payload.question,
            answer=answer,
            sources=sources,
        )

    except Exception as exc:
        logger.exception("RAG query failed for product=%s", payload.product_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"RAG query failed: {exc}",
        ) from exc
