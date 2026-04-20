"""FastAPI router for ETL endpoints."""
from __future__ import annotations

import asyncio
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies import get_session, get_settings
from etl.fetcher import CoinGeckoFetcher
from etl.models import ETLResult
from etl.parser import ETLParser
from etl.repository import ETLRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/etl", tags=["etl"])


@router.post("/run", response_model=ETLResult)
async def run_etl(
    session=Depends(get_session),
    settings=Depends(get_settings),
) -> ETLResult:
    """Ingest prices from CoinGecko for all active products and persist to PostgreSQL."""
    result = ETLResult(status="ok")
    repository = ETLRepository(session)

    try:
        products = await repository.get_active_products()
        result.products_processed = len(products)
        result.product_ids = [p.external_id for p in products]

        logger.info("Starting ETL for %d products", len(products))

        async with CoinGeckoFetcher(
            base_url=settings.coingecko_base_url,
            api_key=settings.coingecko_api_key,
        ) as fetcher:
            for product in products:
                try:
                    price_data = await fetcher.fetch_market_chart(
                        product_id=product.external_id,
                        days=settings.etl_lookback_days,
                    )
                    parsed_records = ETLParser.parse_price_data(
                        product_id=product.external_id,
                        coingecko_prices=price_data,
                    )
                    insert_result = await repository.insert_price_records(parsed_records)
                    result.records_inserted += insert_result["inserted"]
                    result.records_skipped += insert_result["skipped"]
                    logger.info(
                        "ETL %s: inserted=%d skipped=%d",
                        product.external_id,
                        insert_result["inserted"],
                        insert_result["skipped"],
                    )
                except (httpx.HTTPError, OSError) as exc:
                    logger.error("ETL failed for %s: %s", product.external_id, exc)
                    result.errors.append(f"{product.external_id}: {exc}")

                # CoinGecko free tier rate limit mitigation.
                await asyncio.sleep(1.2)

        logger.info(
            "ETL completed: inserted=%d skipped=%d errors=%d",
            result.records_inserted,
            result.records_skipped,
            len(result.errors),
        )
        return result

    except (httpx.HTTPError, OSError, RuntimeError) as exc:
        logger.exception("ETL pipeline failed")
        result.status = "error"
        result.errors.append(str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ETL pipeline failed: {exc}",
        ) from exc
