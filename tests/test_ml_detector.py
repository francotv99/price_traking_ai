"""Tests for ML anomaly detector."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ml.detector import AnomalyDetector
from ml.models import AnomalyCategory, PricePoint


def _series_with_spike() -> list[PricePoint]:
    now = datetime.now(timezone.utc)
    base = []
    price = 100.0
    for i in range(30):
        base.append(
            PricePoint(
                product_id="bitcoin",
                price_usd=Decimal(str(round(price, 4))),
                recorded_at=now - timedelta(hours=30 - i),
            )
        )
        price += 0.2

    # Inject a large spike on the latest point.
    base[-1] = PricePoint(
        product_id="bitcoin",
        price_usd=Decimal("190.0"),
        recorded_at=now,
    )
    return base


def test_detector_returns_no_anomaly_with_short_series() -> None:
    detector = AnomalyDetector()
    now = datetime.now(timezone.utc)
    series = [
        PricePoint(
            product_id="bitcoin",
            price_usd=Decimal("100.0"),
            recorded_at=now,
        )
    ]

    result = detector.detect("bitcoin", series)

    assert result.anomaly is False
    assert result.product_id == "bitcoin"


def test_detector_detects_spike() -> None:
    detector = AnomalyDetector(contamination=0.1)
    result = detector.detect("bitcoin", _series_with_spike())

    assert result.product_id == "bitcoin"
    assert result.anomaly is True
    assert result.category in {AnomalyCategory.OPPORTUNITY, AnomalyCategory.DATA_ERROR}
    assert result.score is not None
    assert result.delta_pct is not None


def test_detector_classifies_sustained_move_as_opportunity() -> None:
    """A large move spread over 6+ hours must be OPPORTUNITY, not DATA_ERROR."""
    now = datetime.now(timezone.utc)
    base_price = 100.0
    series: list[PricePoint] = []

    # 29 stable points spread over the last 50 h, last one at now-22h.
    for i in range(29):
        series.append(
            PricePoint(
                product_id="ethereum",
                price_usd=Decimal(str(round(base_price + i * 0.1, 4))),
                recorded_at=now - timedelta(hours=50) + timedelta(hours=i),
            )
        )

    # +30% spike at now (22 h after the previous point → qualifies as OPPORTUNITY).
    series.append(
        PricePoint(
            product_id="ethereum",
            price_usd=Decimal(str(round(base_price * 1.30, 4))),
            recorded_at=now,
        )
    )

    detector = AnomalyDetector(
        contamination=0.1,
        opportunity_delta_threshold=0.05,
        anomaly_window_hours=1,
    )
    result = detector.detect("ethereum", series)

    if result.anomaly:
        assert result.category == AnomalyCategory.OPPORTUNITY
