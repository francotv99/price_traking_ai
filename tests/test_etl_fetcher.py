"""Tests for ETL fetcher module."""
import pytest
import httpx
from unittest.mock import AsyncMock, patch

from etl.fetcher import CoinGeckoFetcher
from etl.models import CoinGeckoPrice


@pytest.mark.asyncio
class TestCoinGeckoFetcher:
    """Test suite for CoinGecko fetcher."""

    @pytest.fixture
    async def fetcher(self):
        """Create a fetcher instance."""
        async with CoinGeckoFetcher() as f:
            yield f

    @pytest.mark.asyncio
    async def test_fetcher_context_manager(self):
        """Test fetcher context manager initialization."""
        async with CoinGeckoFetcher() as fetcher:
            assert fetcher._client is not None
            assert isinstance(fetcher._client, httpx.AsyncClient)

    @pytest.mark.asyncio
    async def test_fetcher_without_context_manager_raises(self):
        """Test that using fetcher without context manager raises error."""
        fetcher = CoinGeckoFetcher()

        with pytest.raises(RuntimeError, match="Must use async context manager"):
            await fetcher.fetch_market_chart("bitcoin")

    @pytest.mark.asyncio
    async def test_convert_timestamp(self):
        """Test timestamp conversion utility."""
        ts_ms = 1713175200000  # 2024-04-15 10:00:00 UTC
        dt = CoinGeckoFetcher.convert_timestamp(ts_ms)

        assert dt.year == 2024
        assert dt.month == 4
        assert dt.day == 15

    @pytest.mark.asyncio
    async def test_coingecko_price_model(self):
        """Test CoinGeckoPrice model."""
        price = CoinGeckoPrice(
            timestamp=1713175200000,
            price=42500.50,
        )

        assert price.timestamp == 1713175200000
        assert price.price == 42500.50

    def test_fetcher_configuration(self):
        """Test fetcher configuration."""
        fetcher = CoinGeckoFetcher(
            base_url="https://api.coingecko.com/api/v3",
            api_key="test_key",
            timeout=60,
        )

        assert fetcher.base_url == "https://api.coingecko.com/api/v3"
        assert fetcher.api_key == "test_key"
        assert fetcher.timeout == 60

    def test_base_url_trailing_slash_removed(self):
        """Test that trailing slash is removed from base URL."""
        fetcher = CoinGeckoFetcher(base_url="https://api.coingecko.com/api/v3/")

        assert fetcher.base_url == "https://api.coingecko.com/api/v3"
