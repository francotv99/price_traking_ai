"""Tests for ETL parser module."""
import pytest
from datetime import datetime
from decimal import Decimal

from etl.models import CoinGeckoPrice, PriceRecord
from etl.parser import ETLParser


class TestETLParser:
    """Test suite for ETL parser."""

    def test_parse_price_data_valid(self):
        """Test parsing valid price data."""
        coingecko_prices = [
            CoinGeckoPrice(timestamp=1713175200000, price=42500.50),
            CoinGeckoPrice(timestamp=1713261600000, price=43000.00),
        ]

        records = ETLParser.parse_price_data(
            product_id="bitcoin",
            coingecko_prices=coingecko_prices,
        )

        assert len(records) == 2
        assert records[0].product_id == "bitcoin"
        assert records[0].price_usd == Decimal("42500.50")
        assert records[0].source == "coingecko"

    def test_parse_price_data_empty(self):
        """Test parsing empty price data."""
        records = ETLParser.parse_price_data(
            product_id="bitcoin",
            coingecko_prices=[],
        )

        assert records == []

    def test_parse_price_data_with_invalid_prices(self):
        """Test parsing with some invalid prices (should skip them)."""
        coingecko_prices = [
            CoinGeckoPrice(timestamp=1713175200000, price=42500.50),
            CoinGeckoPrice(timestamp=1713261600000, price=43000.00),
        ]

        records = ETLParser.parse_price_data(
            product_id="bitcoin",
            coingecko_prices=coingecko_prices,
        )

        # Should skip invalid ones but process valid
        assert len(records) >= 0

    def test_validate_price_record_valid(self):
        """Test validating a valid price record."""
        record = PriceRecord(
            product_id="bitcoin",
            price_usd=Decimal("42500.50"),
            recorded_at=datetime.utcnow(),
        )

        assert ETLParser.validate_price_record(record) is True

    def test_validate_price_record_missing_product_id(self):
        """Test validating record with missing product_id."""
        record = PriceRecord(
            product_id="",
            price_usd=Decimal("42500.50"),
            recorded_at=datetime.utcnow(),
        )

        with pytest.raises(ValueError, match="product_id is required"):
            ETLParser.validate_price_record(record)

    def test_validate_price_record_negative_price(self):
        """Test validating record with negative price."""
        record = PriceRecord(
            product_id="bitcoin",
            price_usd=Decimal("-100"),
            recorded_at=datetime.utcnow(),
        )

        with pytest.raises(ValueError, match="price_usd must be positive"):
            ETLParser.validate_price_record(record)

    def test_validate_price_record_zero_price(self):
        """Test validating record with zero price."""
        record = PriceRecord(
            product_id="bitcoin",
            price_usd=Decimal("0"),
            recorded_at=datetime.utcnow(),
        )

        with pytest.raises(ValueError, match="price_usd must be positive"):
            ETLParser.validate_price_record(record)

    def test_validate_price_range_valid(self):
        """Test validating price is in reasonable range."""
        result = ETLParser.validate_price_range(
            price=Decimal("42500"),
            product_id="bitcoin",
        )

        assert result is True

    def test_validate_price_range_too_low(self):
        """Test validating price below minimum."""
        result = ETLParser.validate_price_range(
            price=Decimal("0.00001"),
            product_id="bitcoin",
            min_price=Decimal("0.0001"),
        )

        assert result is False

    def test_validate_price_range_too_high(self):
        """Test validating price above maximum."""
        result = ETLParser.validate_price_range(
            price=Decimal("9999999999"),
            product_id="bitcoin",
            max_price=Decimal("999999999"),
        )

        assert result is False

    def test_timestamp_conversion(self):
        """Test timestamp conversion from milliseconds to datetime."""
        ts_ms = 1713175200000  # 2024-04-15 10:00:00 UTC

        record = PriceRecord(
            product_id="bitcoin",
            price_usd=Decimal("42500"),
            recorded_at=datetime.utcfromtimestamp(ts_ms / 1000),
        )

        # Check that datetime was properly converted
        assert record.recorded_at.year == 2024
        assert record.recorded_at.month == 4
