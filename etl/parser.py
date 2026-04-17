"""Parser for CoinGecko API responses."""
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

from etl.models import PriceRecord, CoinGeckoPrice

logger = logging.getLogger(__name__)


class ETLParser:
    """Parses and normalizes CoinGecko API responses."""

    @staticmethod
    def parse_price_data(
        product_id: str,
        coingecko_prices: list[CoinGeckoPrice],
        source: str = "coingecko",
        raw_payload: Optional[dict] = None,
    ) -> list[PriceRecord]:
        """Parse CoinGecko price data into PriceRecord models.
        
        Args:
            product_id: Product ID (e.g., 'bitcoin')
            coingecko_prices: List of CoinGeckoPrice data points
            source: Data source identifier
            raw_payload: Raw API response for storage
            
        Returns:
            List of normalized PriceRecord objects
            
        Raises:
            ValueError: If data is invalid or incomplete
        """
        if not coingecko_prices:
            logger.warning(f"No price data provided for {product_id}")
            return []

        records = []

        for price_data in coingecko_prices:
            try:
                # Convert timestamp from milliseconds to datetime
                recorded_at = datetime.utcfromtimestamp(price_data.timestamp / 1000)

                # Create normalized record
                record = PriceRecord(
                    product_id=product_id,
                    price_usd=Decimal(str(price_data.price)),
                    recorded_at=recorded_at,
                    source=source,
                    raw_payload=raw_payload,
                )

                records.append(record)

            except (ValueError, TypeError) as e:
                logger.error(
                    f"Failed to parse price for {product_id}: {str(e)}"
                )
                continue

        logger.info(f"Parsed {len(records)} price records for {product_id}")
        return records

    @staticmethod
    def validate_price_record(record: PriceRecord) -> bool:
        """Validate a single price record.
        
        Args:
            record: PriceRecord to validate
            
        Returns:
            True if valid, raises ValueError otherwise
            
        Raises:
            ValueError: If record is invalid
        """
        if not record.product_id:
            raise ValueError("product_id is required")

        if record.price_usd <= 0:
            raise ValueError(f"price_usd must be positive, got {record.price_usd}")

        if not record.recorded_at:
            raise ValueError("recorded_at is required")

        if record.recorded_at.tzinfo is None:
            logger.warning(f"recorded_at is not timezone-aware: {record.recorded_at}")

        return True

    @staticmethod
    def validate_price_range(
        price: Decimal,
        product_id: str,
        min_price: Decimal = Decimal("0.0001"),
        max_price: Decimal = Decimal("999999999"),
    ) -> bool:
        """Validate price is within reasonable range.
        
        Helps detect data errors or API issues.
        
        Args:
            price: Price value to validate
            product_id: Product for context in logging
            min_price: Minimum acceptable price
            max_price: Maximum acceptable price
            
        Returns:
            True if valid, False otherwise
        """
        if price < min_price or price > max_price:
            logger.warning(
                f"Price {price} for {product_id} outside reasonable range "
                f"[{min_price}, {max_price}]"
            )
            return False

        return True
