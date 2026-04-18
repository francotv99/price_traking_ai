"""FastAPI integration tests using TestClient."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app

@pytest.fixture(scope="module")
def client():
    with patch("api.dependencies.init_db", new_callable=AsyncMock), \
         patch("api.dependencies.close_db", new_callable=AsyncMock), \
         patch("api.dependencies.get_session"):
        with TestClient(app) as c:
            yield c


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------

def test_root_returns_welcome(client) -> None:
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "FinUp" in data["message"]
    assert "docs" in data


def test_health_returns_healthy(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_status_returns_ok(client) -> None:
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "database" in data


# ---------------------------------------------------------------------------
# ETL endpoint
# ---------------------------------------------------------------------------

def test_etl_run_calls_fetcher_and_returns_result(client) -> None:
    from etl.models import CoinGeckoPrice

    mock_products = [
        MagicMock(external_id="bitcoin", id="1", name="Bitcoin", source="coingecko", is_active=True, created_at=None)
    ]
    mock_prices = [
        CoinGeckoPrice(timestamp=1700000000000, price=50000.0),
        CoinGeckoPrice(timestamp=1700086400000, price=51000.0),
    ]

    with (
        patch("etl.router.ETLRepository") as MockRepo,
        patch("etl.router.CoinGeckoFetcher") as MockFetcher,
    ):
        repo_instance = AsyncMock()
        repo_instance.get_active_products.return_value = mock_products
        repo_instance.insert_price_records.return_value = {"inserted": 2, "skipped": 0}
        MockRepo.return_value = repo_instance

        fetcher_instance = AsyncMock()
        fetcher_instance.fetch_market_chart.return_value = mock_prices
        fetcher_instance.__aenter__ = AsyncMock(return_value=fetcher_instance)
        fetcher_instance.__aexit__ = AsyncMock(return_value=False)
        MockFetcher.return_value = fetcher_instance

        response = client.post("/etl/run")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["records_inserted"] == 2
    assert "bitcoin" in data["product_ids"]


def test_etl_run_returns_partial_on_fetch_error(client) -> None:
    import httpx

    mock_products = [
        MagicMock(external_id="bitcoin", id="1", name="Bitcoin", source="coingecko", is_active=True, created_at=None)
    ]

    with (
        patch("etl.router.ETLRepository") as MockRepo,
        patch("etl.router.CoinGeckoFetcher") as MockFetcher,
    ):
        repo_instance = AsyncMock()
        repo_instance.get_active_products.return_value = mock_products
        MockRepo.return_value = repo_instance

        fetcher_instance = AsyncMock()
        fetcher_instance.fetch_market_chart.side_effect = httpx.HTTPError("timeout")
        fetcher_instance.__aenter__ = AsyncMock(return_value=fetcher_instance)
        fetcher_instance.__aexit__ = AsyncMock(return_value=False)
        MockFetcher.return_value = fetcher_instance

        response = client.post("/etl/run")

    assert response.status_code == 200
    data = response.json()
    assert len(data["errors"]) > 0


# ---------------------------------------------------------------------------
# ML endpoint
# ---------------------------------------------------------------------------

def test_ml_detect_returns_no_anomaly_for_short_series(client) -> None:
    from datetime import datetime, timezone
    from decimal import Decimal
    from ml.models import PricePoint

    short_series = [
        PricePoint(product_id="bitcoin", price_usd=Decimal("50000"), recorded_at=datetime.now(timezone.utc))
    ]

    with patch("ml.router.MLRepository") as MockRepo:
        repo_instance = AsyncMock()
        repo_instance.get_price_history.return_value = short_series
        MockRepo.return_value = repo_instance

        response = client.post("/ml/detect", json={"product_id": "bitcoin", "lookback_days": 90})

    assert response.status_code == 200
    data = response.json()
    assert data["anomaly"] is False
    assert "Not enough" in data["explanation"]


def test_ml_detect_rejects_missing_product_id(client) -> None:
    response = client.post("/ml/detect", json={"lookback_days": 90})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# RAG endpoint
# ---------------------------------------------------------------------------

def test_rag_query_returns_503_without_openai_key(client) -> None:
    from api.dependencies import get_settings as real_get_settings
    from api.settings import Settings

    settings_no_key = MagicMock(spec=Settings)
    settings_no_key.openai_api_key = None
    settings_no_key.etl_products_list = ["bitcoin"]
    settings_no_key.qdrant_host = "localhost"
    settings_no_key.qdrant_port = 6333
    settings_no_key.qdrant_collection = "crypto_chunks"

    app.dependency_overrides[real_get_settings] = lambda: settings_no_key
    try:
        response = client.post("/rag/query", json={"question": "What is bitcoin?"})
    finally:
        app.dependency_overrides.pop(real_get_settings, None)

    assert response.status_code == 503


def test_rag_query_returns_answer(client) -> None:
    with patch("rag.router.get_settings") as mock_settings, \
         patch("rag.router.RAGRetriever") as MockRetriever:
        settings = MagicMock()
        settings.openai_api_key = "test-key"
        settings.qdrant_host = "localhost"
        settings.qdrant_port = 6333
        settings.qdrant_collection = "crypto_chunks"
        settings.etl_products_list = ["bitcoin"]
        mock_settings.return_value = settings

        retriever_instance = MagicMock()
        retriever_instance.query = AsyncMock(return_value=("Bitcoin es una cripto.", ["market_data"], ["bitcoin"]))
        MockRetriever.return_value = retriever_instance

        response = client.post("/rag/query", json={"question": "Qué es bitcoin?"})

    assert response.status_code == 200
    data = response.json()
    assert "bitcoin" in data["answer"].lower()
    assert data["product_ids"] == ["bitcoin"]
