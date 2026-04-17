"""Isolation Forest based anomaly detector."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import numpy as np
from sklearn.ensemble import IsolationForest

from ml.models import AnomalyCategory, AnomalyResult, PricePoint


class AnomalyDetector:
    """Detect anomalies on price time series using Isolation Forest."""

    def __init__(
        self,
        contamination: float = 0.05,
        opportunity_delta_threshold: float = 0.15,
        anomaly_window_hours: int = 1,
    ) -> None:
        self.contamination = contamination
        self.opportunity_delta_threshold = opportunity_delta_threshold
        self.anomaly_window_hours = anomaly_window_hours
        self.model = IsolationForest(
            contamination=self.contamination,
            random_state=42,
            n_estimators=200,
        )

    def detect(self, product_id: str, series: list[PricePoint]) -> AnomalyResult:
        """Detect whether the latest point in a series is anomalous."""
        if len(series) < 10:
            return AnomalyResult(
                anomaly=False,
                product_id=product_id,
                explanation="Not enough historical points (minimum 10) to evaluate anomalies.",
            )

        prices = np.array([float(point.price_usd) for point in series], dtype=float)
        times = np.array([point.recorded_at.timestamp() for point in series], dtype=float)

        diffs = np.diff(prices, prepend=prices[0])
        x = np.column_stack([prices, np.abs(diffs), times - times.min()])

        self.model.fit(x)
        predictions = self.model.predict(x)
        anomaly_scores = -self.model.decision_function(x)

        is_anomaly = predictions[-1] == -1
        latest_price = Decimal(str(prices[-1]))

        baseline_window = prices[:-1][-24:] if len(prices) > 1 else prices
        expected = float(np.median(baseline_window)) if len(baseline_window) else float(prices[-1])
        expected_price = Decimal(str(round(expected, 8)))

        if expected == 0:
            delta_pct = 0.0
        else:
            delta_pct = ((float(latest_price) - expected) / expected) * 100.0

        if not is_anomaly:
            return AnomalyResult(
                anomaly=False,
                product_id=product_id,
                explanation="Latest point is within normal range according to Isolation Forest.",
            )

        category = self._classify_category(series, delta_pct)
        forced_by_soft_guard = False

        if abs(delta_pct) < self.opportunity_delta_threshold * 100 and category == AnomalyCategory.OPPORTUNITY:
            category = AnomalyCategory.DATA_ERROR
            forced_by_soft_guard = True

        explanation = self._build_explanation(
            series=series,
            delta_pct=delta_pct,
            category=category,
            forced_by_soft_guard=forced_by_soft_guard,
        )

        return AnomalyResult(
            anomaly=True,
            product_id=product_id,
            category=category,
            score=float(round(anomaly_scores[-1], 4)),
            price_actual=latest_price,
            price_expected=expected_price,
            delta_pct=round(delta_pct, 4),
            explanation=explanation,
        )

    def _classify_category(self, series: list[PricePoint], delta_pct: float) -> AnomalyCategory:
        """Classify anomaly between opportunity and likely data error."""
        if len(series) < 2:
            return AnomalyCategory.DATA_ERROR

        last_time = series[-1].recorded_at
        prev_time = series[-2].recorded_at
        elapsed_hours = max((last_time - prev_time).total_seconds() / 3600.0, 0.0)

        if abs(delta_pct) > 40.0 and elapsed_hours <= float(self.anomaly_window_hours):
            return AnomalyCategory.DATA_ERROR

        if abs(delta_pct) > 40.0 and elapsed_hours >= 6.0:
            return AnomalyCategory.OPPORTUNITY

        return AnomalyCategory.OPPORTUNITY

    def _build_explanation(
        self,
        series: list[PricePoint],
        delta_pct: float,
        category: AnomalyCategory,
        forced_by_soft_guard: bool,
    ) -> str:
        """Provide a readable explanation for classification outcomes."""
        if len(series) < 2:
            return "Anomaly classified as DATA_ERROR due to insufficient temporal context."

        last_time = series[-1].recorded_at
        prev_time = series[-2].recorded_at
        elapsed_hours = max((last_time - prev_time).total_seconds() / 3600.0, 0.0)
        abs_delta_pct = abs(delta_pct)
        opportunity_threshold_pct = self.opportunity_delta_threshold * 100

        if forced_by_soft_guard:
            return (
                "Outlier detected, but delta_pct "
                f"({abs_delta_pct:.4f}%) is below opportunity threshold "
                f"({opportunity_threshold_pct:.2f}%), so it was classified as DATA_ERROR."
            )

        if abs_delta_pct > 40.0 and elapsed_hours <= float(self.anomaly_window_hours):
            return (
                "Large jump detected "
                f"({abs_delta_pct:.4f}% in {elapsed_hours:.2f}h), treated as potential data error."
            )

        if abs_delta_pct > 40.0 and elapsed_hours >= 6.0:
            return (
                "Large sustained move detected "
                f"({abs_delta_pct:.4f}% over {elapsed_hours:.2f}h), classified as OPPORTUNITY."
            )

        return (
            "Outlier detected with delta_pct "
            f"{abs_delta_pct:.4f}% and category {category.value}."
        )
