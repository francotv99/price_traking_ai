"""CoinGecko API client for price fetching."""
import httpx
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from etl.models import CoinGeckoPrice

logger = logging.getLogger(__name__)


class CoinGeckoFetcher:
    """Fetches price data from CoinGecko API."""

    def __init__(
        self,
        base_url: str = "https://api.coingecko.com/api/v3",
        api_key: Optional[str] = None,
        timeout: int = 30,
    ):
        """Initialize CoinGecko fetcher.
        
        Args:
            base_url: CoinGecko API base URL
            api_key: Optional API key (free tier doesn't require it)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.aclose()

    async def fetch_market_chart(
        self,
        product_id: str,
        days: int = 90,
        vs_currency: str = "usd",
    ) -> list[CoinGeckoPrice]:
        """Fetch historical price data for a product.
        
        Args:
            product_id: CoinGecko product ID (e.g., 'bitcoin')
            days: Number of days of historical data
            vs_currency: Target currency (default: 'usd')
            
        Returns:
            List of price data points sorted by timestamp
            
        Raises:
            httpx.HTTPError: On API errors
        """
        if not self._client:
            raise RuntimeError("Must use async context manager or call __aenter__")

        url = f"{self.base_url}/coins/{product_id}/market_chart"
        params = {
            "vs_currency": vs_currency,
            "days": days,
            "interval": "daily",
        }

        if self.api_key:
            params["x_cg_pro_api_key"] = self.api_key

        try:
            logger.info(
                f"Fetching {days} days of {product_id} price data from CoinGecko"
            )
            response = await self._client.get(url, params=params)
            response.raise_for_status()

            data = response.json()
            prices = data.get("prices", [])

            # Convert to CoinGeckoPrice objects
            result = [
                CoinGeckoPrice(timestamp=ts, price=float(price))
                for ts, price in prices
            ]

            logger.info(f"Successfully fetched {len(result)} price points for {product_id}")
            return result

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch {product_id}: {str(e)}")
            raise

    async def fetch_coin_info(self, product_id: str) -> dict:
        """Fetch general coin information.
        
        Used for RAG corpus building.
        
        Args:
            product_id: CoinGecko product ID
            
        Returns:
            Coin information dictionary
            
        Raises:
            httpx.HTTPError: On API errors
        """
        if not self._client:
            raise RuntimeError("Must use async context manager or call __aenter__")

        url = f"{self.base_url}/coins/{product_id}"
        params = {
            "localization": False,
            "community_data": True,
            "market_data": True,
        }

        if self.api_key:
            params["x_cg_pro_api_key"] = self.api_key

        try:
            logger.info(f"Fetching coin info for {product_id}")
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch coin info for {product_id}: {str(e)}")
            raise

    @staticmethod
    def convert_timestamp(ts_ms: int) -> datetime:
        """Convert CoinGecko timestamp (milliseconds) to datetime.
        
        Args:
            ts_ms: Timestamp in milliseconds
            
        Returns:
            Datetime object in UTC
        """
        return datetime.utcfromtimestamp(ts_ms / 1000)
