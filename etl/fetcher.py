"""CoinGecko API client for price fetching."""
import asyncio
import httpx
import logging
from datetime import datetime
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
        max_retries: int = 4,
        retry_base_delay: float = 1.5,
    ):
        """Initialize CoinGecko fetcher.
        
        Args:
            base_url: CoinGecko API base URL
            api_key: Optional API key (free tier doesn't require it)
            timeout: Request timeout in seconds
            max_retries: Maximum retries for 429/5xx errors
            retry_base_delay: Base delay in seconds for exponential backoff
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                "User-Agent": "finup-price-tracker/0.1.0",
                "Accept": "application/json",
            },
        )
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
            response = await self._get_with_retry(url=url, params=params)

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
            response = await self._get_with_retry(url=url, params=params)
            return response.json()

        except httpx.HTTPError as e:
            logger.error(f"Failed to fetch coin info for {product_id}: {str(e)}")
            raise

    async def _get_with_retry(self, url: str, params: dict) -> httpx.Response:
        """GET with retries for transient errors and CoinGecko rate limits."""
        if not self._client:
            raise RuntimeError("Must use async context manager or call __aenter__")

        for attempt in range(1, self.max_retries + 1):
            response = await self._client.get(url, params=params)

            if response.status_code < 400:
                return response

            retryable = response.status_code in {429, 500, 502, 503, 504}
            if not retryable or attempt == self.max_retries:
                response.raise_for_status()

            retry_after = response.headers.get("Retry-After")
            if retry_after is not None and retry_after.isdigit():
                delay = float(retry_after)
            else:
                delay = self.retry_base_delay * (2 ** (attempt - 1))

            logger.warning(
                "CoinGecko transient error %s. Retrying in %.1fs (%s/%s)",
                response.status_code,
                delay,
                attempt,
                self.max_retries,
            )
            await asyncio.sleep(delay)

        raise RuntimeError("Unexpected retry flow in _get_with_retry")

    @staticmethod
    def convert_timestamp(ts_ms: int) -> datetime:
        """Convert CoinGecko timestamp (milliseconds) to datetime.
        
        Args:
            ts_ms: Timestamp in milliseconds
            
        Returns:
            Datetime object in UTC
        """
        return datetime.utcfromtimestamp(ts_ms / 1000)
