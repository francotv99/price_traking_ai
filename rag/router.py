"""FastAPI router for RAG endpoints."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_settings
from etl.fetcher import CoinGeckoFetcher
from rag.corpus import CorpusBuilder
from rag.models import ReindexRequest, ReindexResponse

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

    try:
        async with CoinGeckoFetcher(
            base_url=settings.coingecko_base_url,
            api_key=settings.coingecko_api_key,
        ) as fetcher:
            for product_id in products:
                try:
                    result = await builder.build_for_product(product_id=product_id, fetcher=fetcher)
                    products_results.append(result)
                    products_reindexed.append(product_id)
                except Exception as exc:
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
