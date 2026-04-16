# ML Module

Anomaly detection in cryptocurrency prices using Isolation Forest.

## Overview

The ML module handles:
- Reading historical price data from PostgreSQL
- Running Isolation Forest algorithm
- Classifying anomalies (OPPORTUNITY vs DATA_ERROR)
- Computing anomaly scores and deltas
- Persisting events for alerting

## Endpoints

### POST /ml/detect

Run anomaly detection on historical price data.

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
  "product_id": "bitcoin"
}
```

**Response (with anomaly):**
```json
{
  "anomaly": true,
  "product_id": "bitcoin",
  "category": "OPPORTUNITY",
  "score": 0.92,
  "price_actual": 98000.00,
  "price_expected": 67000.00,
  "delta_pct": 46.27
}
```

## Anomaly Categories

- **OPPORTUNITY**: Real market opportunity (delta > 40% over > 6 hours)
- **DATA_ERROR**: Suspected data source error (delta > 40% in < 1 hour)

## Module Structure

- `router.py` - FastAPI endpoint
- `detector.py` - Isolation Forest implementation
- `repository.py` - Database queries
- `models.py` - Data models (AnomalyResult, AnomalyCategory)
- `evaluation.ipynb` - Model evaluation with synthetic data

## Configuration

Via environment variables:
- `ML_CONTAMINATION` - Expected anomaly percentage (default: 0.05)
- `ML_LOOKBACK_DAYS` - Historical window (default: 90)
- `ML_OPPORTUNITY_DELTA_THRESHOLD` - Minimum delta for OPPORTUNITY
- `ML_ANOMALY_WINDOW_HOURS` - Time window for classification

## Model Evaluation

See `evaluation.ipynb` for:
- Synthetic data generation
- Precision, recall, F1 metrics
- Feature importance analysis
- Confusion matrix

## Implementation Status

- [ ] detector.py
- [ ] repository.py
- [ ] router.py
- [ ] models.py
- [ ] evaluation.ipynb
- [ ] Unit tests
