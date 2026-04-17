"""Tests for RAG corpus chunking utilities and retriever."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from rag.corpus import CorpusBuilder
from rag.retriever import RAGRetriever


# ---------------------------------------------------------------------------
# RAGRetriever
# ---------------------------------------------------------------------------

@pytest.fixture()
def retriever() -> RAGRetriever:
    return RAGRetriever(
        qdrant_host="localhost",
        qdrant_port=6333,
        qdrant_collection="crypto_chunks",
        openai_api_key="test-key",
        top_k=3,
    )


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


@pytest.mark.asyncio
async def test_query_returns_answer_and_sources(retriever: RAGRetriever) -> None:
    embed_resp = _mock_response({"data": [{"embedding": [0.1] * 1536}]})
    search_resp = _mock_response({
        "result": [
            {"payload": {"source": "market_data", "text": "Bitcoin price is 50k"}},
            {"payload": {"source": "description", "text": "Bitcoin is a decentralized currency"}},
        ]
    })
    generate_resp = _mock_response({
        "choices": [{"message": {"content": "Bitcoin market cap is large."}}]
    })

    async_client = AsyncMock()
    async_client.post = AsyncMock(side_effect=[embed_resp, search_resp, generate_resp])
    async_client.__aenter__ = AsyncMock(return_value=async_client)
    async_client.__aexit__ = AsyncMock(return_value=False)

    with patch("rag.retriever.httpx.AsyncClient", return_value=async_client):
        answer, sources, resolved_ids = await retriever.query("What is Bitcoin's market cap?", product_id="bitcoin")

    assert "Bitcoin" in answer
    assert "market_data" in sources
    assert "description" in sources
    assert resolved_ids == ["bitcoin"]


@pytest.mark.asyncio
async def test_query_infers_product_from_question(retriever: RAGRetriever) -> None:
    extract_resp = _mock_response({"choices": [{"message": {"content": "bitcoin"}}]})
    embed_resp = _mock_response({"data": [{"embedding": [0.1] * 1536}]})
    search_resp = _mock_response({
        "result": [{"payload": {"source": "market_data", "text": "Bitcoin price is 50k"}}]
    })
    generate_resp = _mock_response({"choices": [{"message": {"content": "Bitcoin is at 50k."}}]})

    async_client = AsyncMock()
    async_client.post = AsyncMock(side_effect=[extract_resp, embed_resp, search_resp, generate_resp])
    async_client.__aenter__ = AsyncMock(return_value=async_client)
    async_client.__aexit__ = AsyncMock(return_value=False)

    with patch("rag.retriever.httpx.AsyncClient", return_value=async_client):
        answer, sources, resolved_ids = await retriever.query("cómo está el btc hoy?")

    assert resolved_ids == ["bitcoin"]
    assert answer == "Bitcoin is at 50k."


@pytest.mark.asyncio
async def test_query_handles_multiple_products(retriever: RAGRetriever) -> None:
    extract_resp = _mock_response({"choices": [{"message": {"content": "bitcoin,ethereum"}}]})
    embed_resp = _mock_response({"data": [{"embedding": [0.1] * 1536}]})
    search_btc = _mock_response({"result": [{"payload": {"source": "market_data", "text": "BTC at 50k"}}]})
    search_eth = _mock_response({"result": [{"payload": {"source": "market_data", "text": "ETH at 3k"}}]})
    generate_resp = _mock_response({"choices": [{"message": {"content": "BTC y ETH muestran tendencia alcista."}}]})

    async_client = AsyncMock()
    async_client.post = AsyncMock(side_effect=[extract_resp, embed_resp, search_btc, search_eth, generate_resp])
    async_client.__aenter__ = AsyncMock(return_value=async_client)
    async_client.__aexit__ = AsyncMock(return_value=False)

    with patch("rag.retriever.httpx.AsyncClient", return_value=async_client):
        answer, sources, resolved_ids = await retriever.query("tendencia del ETH y BTC?")

    assert "bitcoin" in resolved_ids
    assert "ethereum" in resolved_ids
    assert "alcista" in answer


@pytest.mark.asyncio
async def test_query_returns_unknown_message_when_no_crypto(retriever: RAGRetriever) -> None:
    extract_resp = _mock_response({"choices": [{"message": {"content": "unknown"}}]})

    async_client = AsyncMock()
    async_client.post = AsyncMock(side_effect=[extract_resp])
    async_client.__aenter__ = AsyncMock(return_value=async_client)
    async_client.__aexit__ = AsyncMock(return_value=False)

    with patch("rag.retriever.httpx.AsyncClient", return_value=async_client):
        answer, sources, resolved_ids = await retriever.query("qué tiempo hace hoy?")

    assert resolved_ids == ["unknown"]
    assert sources == []
    assert "criptomoneda" in answer.lower()


@pytest.mark.asyncio
async def test_query_returns_reindex_message_when_no_chunks(retriever: RAGRetriever) -> None:
    embed_resp = _mock_response({"data": [{"embedding": [0.0] * 1536}]})
    search_resp = _mock_response({"result": []})

    async_client = AsyncMock()
    async_client.post = AsyncMock(side_effect=[embed_resp, search_resp])
    async_client.__aenter__ = AsyncMock(return_value=async_client)
    async_client.__aexit__ = AsyncMock(return_value=False)

    with patch("rag.retriever.httpx.AsyncClient", return_value=async_client):
        answer, sources, _ = await retriever.query("What is this?", product_id="unknown-coin")

    assert "reindex" in answer.lower() or "POST /rag/reindex" in answer
    assert sources == []


@pytest.mark.asyncio
async def test_query_deduplicates_sources(retriever: RAGRetriever) -> None:
    embed_resp = _mock_response({"data": [{"embedding": [0.1] * 1536}]})
    search_resp = _mock_response({
        "result": [
            {"payload": {"source": "market_data", "text": "chunk 1"}},
            {"payload": {"source": "market_data", "text": "chunk 2"}},
            {"payload": {"source": "description", "text": "chunk 3"}},
        ]
    })
    generate_resp = _mock_response({
        "choices": [{"message": {"content": "Answer."}}]
    })

    async_client = AsyncMock()
    async_client.post = AsyncMock(side_effect=[embed_resp, search_resp, generate_resp])
    async_client.__aenter__ = AsyncMock(return_value=async_client)
    async_client.__aexit__ = AsyncMock(return_value=False)

    with patch("rag.retriever.httpx.AsyncClient", return_value=async_client):
        _, sources, _ = await retriever.query("Price?", product_id="bitcoin")

    assert sources.count("market_data") == 1


def test_build_context_formats_chunks() -> None:
    chunks = [
        {"payload": {"source": "description", "text": "Bitcoin is decentralized."}},
        {"payload": {"source": "market_data", "text": "Price: 50000 USD"}},
    ]
    context = RAGRetriever._build_context(chunks)

    assert "[1] Fuente: description" in context
    assert "[2] Fuente: market_data" in context
    assert "Bitcoin is decentralized." in context


# ---------------------------------------------------------------------------
# CorpusBuilder
# ---------------------------------------------------------------------------

def test_chunk_text_splits_long_input() -> None:
    builder = CorpusBuilder(chunk_size=50, overlap=10)
    text = "a" * 140

    chunks = builder._chunk_text(text)

    assert len(chunks) >= 3
    assert all(len(c) <= 50 for c in chunks)


def test_extract_sections_contains_expected_keys() -> None:
    builder = CorpusBuilder()
    payload = {
        "description": {"en": "<p>Bitcoin description</p>"},
        "market_data": {
            "current_price": {"usd": 100.0},
            "market_cap": {"usd": 1000.0},
            "total_volume": {"usd": 10.0},
            "ath": {"usd": 200.0},
        },
        "community_data": {
            "reddit_subscribers": 123,
            "twitter_followers": 456,
        },
        "links": {
            "homepage": ["https://bitcoin.org"],
            "subreddit_url": "https://reddit.com/r/bitcoin",
        },
    }

    sections = builder._extract_sections("bitcoin", payload)

    assert set(sections.keys()) == {"description", "market_data", "community", "links"}
    assert "Bitcoin description" in sections["description"]
