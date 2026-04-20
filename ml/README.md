# ML Module

Anomaly detection in cryptocurrency prices using Isolation Forest.

## Overview

The ML module handles:
- Reading historical price data from PostgreSQL
- Running Isolation Forest algorithm
- Classifying anomalies (OPPORTUNITY vs DATA_ERROR)
- Computing anomaly scores and deltas
- Persisting events for alerting

## How the detector works

The detector trains on the **N-1 historical points** and evaluates only the **latest price as a new unseen data point**:

```python
model.fit(x[:-1])           # train on history
predictions = model.predict(x[-1:])  # evaluate latest point cold
```

This is the correct approach: the model learns what "normal" looks like from the past, and the new incoming price is genuinely unknown to it. If the latest price doesn't fit the learned distribution, it's flagged as anomalous.

> The previous approach (training and predicting on the same 90-day window) caused the model to treat all historical moves as normal, making anomaly detection ineffective.

## Anomaly classification

Once Isolation Forest flags a point as anomalous, it's classified by two rules:

```
delta > 40% in <= 1h   → DATA_ERROR   (fast spike, likely bad data)
delta >= 2% over >= 6h → OPPORTUNITY  (sustained real market move)
any other case         → DATA_ERROR
```

## Endpoints

### POST /ml/detect

**Request:**
```json
{
  "product_id": "bitcoin",
  "lookback_days": 90
}
```

**Response (no anomaly):**
```json
{
  "anomaly": false,
  "product_id": "bitcoin",
  "explanation": "Latest point is within normal range according to Isolation Forest."
}
```

**Response (anomaly):**
```json
{
  "anomaly": true,
  "product_id": "bitcoin",
  "category": "OPPORTUNITY",
  "score": 0.42,
  "price_actual": 85000.00,
  "price_expected": 76000.00,
  "delta_pct": 11.84,
  "explanation": "Sustained move of 11.84% over 24.00h exceeds the 2.0% opportunity threshold."
}
```

## Configuration

| Variable | Description | Default |
|---|---|---|
| `ML_CONTAMINATION` | Expected anomaly ratio for Isolation Forest | `0.05` |
| `ML_LOOKBACK_DAYS` | Historical window in days | `90` |
| `ML_OPPORTUNITY_DELTA_THRESHOLD` | Minimum delta to classify as OPPORTUNITY | `0.014` |
| `ML_ANOMALY_WINDOW_HOURS` | Max hours for fast-spike DATA_ERROR rule | `1` |

## Module Structure

- `detector.py` — Isolation Forest implementation
- `repository.py` — Database queries
- `router.py` — FastAPI endpoint
- `models.py` — Data models (AnomalyResult, AnomalyCategory)
- `evaluation.ipynb` — Model evaluation with synthetic data
