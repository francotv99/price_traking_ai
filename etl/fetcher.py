"""CoinGecko API client for price fetching."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

import httpx

from etl.models import CoinGeckoPrice

logger = logging.getLogger(__name__)


class CoinGeckoFetcher:
    """Async HTTP client for CoinGecko API with retry and rate-limit handling."""

    def __init__(
        self,
        base_url: str = "https://api.coingecko.com/api/v3",
        api_key: str | None = None,
        timeout: int = 30,
        max_retries: int = 4,
        retry_base_delay: float = 1.5,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_base_delay = retry_base_delay
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> CoinGeckoFetcher:
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            headers={
                "User-Agent": "finup-price-tracker/0.1.0",
                "Accept": "application/json",
            },
        )
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        if self._client:
            await self._client.aclose()

    async def fetch_market_chart(
        self,
        product_id: str,
        days: int = 90,
        vs_currency: str = "usd",
    ) -> list[CoinGeckoPrice]:
        """Fetch historical price data for a product from CoinGecko."""
        if not self._client:
            raise RuntimeError("CoinGeckoFetcher must be used as an async context manager.")

        url = f"{self.base_url}/coins/{product_id}/market_chart"
        params: dict[str, object] = {
            "vs_currency": vs_currency,
            "days": days,
            "interval": "daily",
        }
        if self.api_key:
            params["x_cg_pro_api_key"] = self.api_key

        logger.info("Fetching %d days of %s prices from CoinGecko", days, product_id)
        response = await self._get_with_retry(url=url, params=params)
        prices = response.json().get("prices", [])
        result = [CoinGeckoPrice(timestamp=ts, price=float(price)) for ts, price in prices]
        logger.info("Fetched %d price points for %s", len(result), product_id)
        return result

    async def fetch_coin_info(self, product_id: str) -> dict:
        """Fetch coin metadata for RAG corpus building."""
        if not self._client:
            raise RuntimeError("CoinGeckoFetcher must be used as an async context manager.")

        url = f"{self.base_url}/coins/{product_id}"
        params: dict[str, object] = {
            "localization": False,
            "community_data": True,
            "market_data": True,
        }
        if self.api_key:
            params["x_cg_pro_api_key"] = self.api_key

        logger.info("Fetching coin info for %s", product_id)
        response = await self._get_with_retry(url=url, params=params)
        return dict(response.json())

    async def _get_with_retry(self, url: str, params: dict) -> httpx.Response:
        """GET with exponential backoff for 429 and 5xx responses."""
        if not self._client:
            raise RuntimeError("CoinGeckoFetcher must be used as an async context manager.")

        for attempt in range(1, self.max_retries + 1):
            response = await self._client.get(url, params=params)

            if response.status_code < 400:
                return response

            retryable = response.status_code in {429, 500, 502, 503, 504}
            if not retryable or attempt == self.max_retries:
                response.raise_for_status()

            retry_after = response.headers.get("Retry-After")
            delay = (
                float(retry_after)
                if retry_after is not None and retry_after.isdigit()
                else self.retry_base_delay * (2 ** (attempt - 1))
            )
            logger.warning(
                "CoinGecko %s — retrying in %.1fs (%d/%d)",
                response.status_code,
                delay,
                attempt,
                self.max_retries,
            )
            await asyncio.sleep(delay)

        raise RuntimeError("Unexpected exit from retry loop.")

    @staticmethod
    def convert_timestamp(ts_ms: int) -> datetime:
        """Convert CoinGecko millisecond timestamp to UTC datetime."""
        return datetime.utcfromtimestamp(ts_ms / 1000)
