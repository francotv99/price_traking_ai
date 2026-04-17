"""Builds product corpus and chunks from CoinGecko data."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from etl.fetcher import CoinGeckoFetcher
from rag.models import ChunkResult, ProductReindexResult


class CorpusBuilder:
    """Fetches product information and generates chunked corpus."""

    def __init__(self, chunk_size: int = 800, overlap: int = 80) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    async def build_for_product(
        self,
        product_id: str,
        fetcher: CoinGeckoFetcher,
    ) -> ProductReindexResult:
        """Fetch and build chunks for a single product."""
        payload = await fetcher.fetch_coin_info(product_id)

        sections = self._extract_sections(product_id, payload)
        chunks: list[ChunkResult] = []

        for source, text in sections.items():
            if not text.strip():
                continue

            for idx, chunk_text in enumerate(self._chunk_text(text)):
                chunk_id = f"{product_id}:{source}:{idx}"
                chunks.append(
                    ChunkResult(
                        product_id=product_id,
                        source=source,
                        chunk_id=chunk_id,
                        text=chunk_text,
                        metadata={
                            "product_id": product_id,
                            "source": source,
                            "indexed_at": datetime.utcnow().isoformat() + "Z",
                        },
                    )
                )

        return ProductReindexResult(product_id=product_id, chunks=chunks)

    def _extract_sections(self, product_id: str, payload: dict[str, Any]) -> dict[str, str]:
        """Extract meaningful text sections from CoinGecko coin payload."""
        description = (payload.get("description") or {}).get("en") or ""
        description = self._clean_text(description)

        market_data = payload.get("market_data") or {}
        community_data = payload.get("community_data") or {}
        links = payload.get("links") or {}

        market_text = self._format_market_data(product_id, market_data)
        community_text = self._format_community_data(product_id, community_data)
        links_text = self._format_links(product_id, links)

        return {
            "description": description,
            "market_data": market_text,
            "community": community_text,
            "links": links_text,
        }

    def _chunk_text(self, text: str) -> list[str]:
        """Chunk long text with small overlap to preserve context."""
        cleaned = self._clean_text(text)
        if not cleaned:
            return []

        chunks: list[str] = []
        start = 0
        total = len(cleaned)

        while start < total:
            end = min(start + self.chunk_size, total)
            chunk = cleaned[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end == total:
                break
            start = max(end - self.overlap, start + 1)

        return chunks

    @staticmethod
    def _clean_text(text: str) -> str:
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    @staticmethod
    def _format_market_data(product_id: str, market_data: dict[str, Any]) -> str:
        def usd(key: str) -> object:
            return (market_data.get(key) or {}).get("usd")

        def pct(key: str) -> object:
            return (market_data.get(key) or {}).get("usd")

        return (
            f"Product: {product_id}. "
            f"Current USD price: {usd('current_price')}. "
            f"Market cap USD: {usd('market_cap')}. "
            f"Market cap rank: {market_data.get('market_cap_rank')}. "
            f"24h volume USD: {usd('total_volume')}. "
            f"Price change 24h: {pct('price_change_percentage_24h_in_currency')}%. "
            f"Price change 7d: {pct('price_change_percentage_7d_in_currency')}%. "
            f"Price change 30d: {pct('price_change_percentage_30d_in_currency')}%. "
            f"Circulating supply: {market_data.get('circulating_supply')}. "
            f"All-time-high USD: {usd('ath')}."
        )

    @staticmethod
    def _format_community_data(product_id: str, community_data: dict[str, Any]) -> str:
        reddit_subscribers = community_data.get("reddit_subscribers")
        twitter_followers = community_data.get("twitter_followers")

        return (
            f"Product: {product_id}. "
            f"Reddit subscribers: {reddit_subscribers}. "
            f"Twitter followers: {twitter_followers}."
        )

    @staticmethod
    def _format_links(product_id: str, links: dict[str, Any]) -> str:
        homepage_list = links.get("homepage") or []
        homepage = homepage_list[0] if homepage_list else None
        subreddit_url = links.get("subreddit_url")

        return (
            f"Product: {product_id}. "
            f"Official homepage: {homepage}. "
            f"Subreddit: {subreddit_url}."
        )
