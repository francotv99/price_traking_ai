"""FastAPI router for ETL endpoints."""
import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from etl.models import ETLResult
from api.dependencies import get_session, get_settings

from etl.fetcher import CoinGeckoFetcher
from etl.parser import ETLParser
from etl.repository import ETLRepository


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/etl", tags=["etl"])


@router.post("/run", response_model=ETLResult)
async def run_etl(
    session=Depends(get_session),
    settings=Depends(get_settings),
) -> ETLResult:
    """Execute ETL pipeline for all active products.
    
    Fetches prices from CoinGecko and stores in PostgreSQL.
    
    Returns:
        ETLResult with ingestion statistics
        
    Raises:
        HTTPException: If ETL execution fails
    """
    
    result = ETLResult(status="ok")
    repository = ETLRepository(session)

    try:
        # Get active products
        products = await repository.get_active_products()
        result.products_processed = len(products)
        result.product_ids = [p.external_id for p in products]

        logger.info(f"Starting ETL for {len(products)} products")
        # Fetch and process each product
        async with CoinGeckoFetcher(
            base_url=settings.coingecko_base_url,
            api_key=settings.coingecko_api_key,
        ) as fetcher:
            for product in products:
                try:
                    # Fetch price data
                    price_data = await fetcher.fetch_market_chart(
                        product_id=product.external_id,
                        days=settings.etl_lookback_days,
                    )

                    # Parse prices
                    parsed_records = ETLParser.parse_price_data(
                        product_id=product.external_id,
                        coingecko_prices=price_data,
                    )

                    # Insert into database
                    insert_result = await repository.insert_price_records(
                        parsed_records
                    )

                    result.records_inserted += insert_result["inserted"]
                    result.records_skipped += insert_result["skipped"]

                    logger.info(
                        f"ETL for {product.external_id}: "
                        f"{insert_result['inserted']} inserted, "
                        f"{insert_result['skipped']} skipped"
                    )

                except Exception as e:
                    error_msg = f"Failed to process {product.external_id}: {str(e)}"
                    logger.error(error_msg)
                    result.errors.append(error_msg)

                # CoinGecko free tier is strict; pace requests to reduce 429s.
                await asyncio.sleep(1.2)

        logger.info(
            f"ETL completed: {result.records_inserted} inserted, "
            f"{result.records_skipped} skipped, {len(result.errors)} errors"
        )
        return result

    except Exception as e:
        error_msg = f"ETL pipeline failed: {str(e)}"
        logger.error(error_msg)
        result.status = "error"
        result.errors.append(error_msg)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_msg,
        )
