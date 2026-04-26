# ML Training Guide — PotholeIQ

**Last updated:** 2026-04-26  
**Trains 3 XGBoost models:** risk regressor, urgency classifier, and accident probability classifier

---

## Quick Start

```bash
cd MainProject/Backend
source .venv/bin/activate
PYTHONPATH=. python -m Backend.cortex.train
```

This runs the **deep training mode** by default — RandomizedSearchCV with 500 iterations, 5-fold CV (~2-3 hours).

---

## Training Modes

| Flag | Mode | Duration | Description |
|------|------|----------|-------------|
| (default) | Deep | ~2-3 hours | RandomizedSearchCV, n_iter=150, cv=5 |
| `--quick` | Quick | ~2 min | GridSearchCV with small param grid |
| `--no-tune` | Defaults | ~30 sec | No hyperparameter search |
| `--no-cache` | Re-fetch | varies | Re-fetch all data from NYC APIs instead of cached parquet |
| `--limit N` | Custom limit | varies | Fetch N pothole records (default: 50,000) |
| `--n-iter N` | Custom iterations | varies | Override RandomizedSearchCV iterations (default: 500) |
| `--cv N` | Custom folds | varies | Override cross-validation folds (default: 5) |

### Examples

```bash
# Full deep training (2-3 hours)
PYTHONPATH=. python -m Backend.cortex.train

# Quick iteration (~2 min)
PYTHONPATH=. python -m Backend.cortex.train --quick

# Deep training with more iterations (4-5 hours)
PYTHONPATH=. python -m Backend.cortex.train --n-iter 300

# Re-fetch data and train
PYTHONPATH=. python -m Backend.cortex.train --no-cache

# Fast iteration with small dataset
PYTHONPATH=. python -m Backend.cortex.train --quick --limit 5000
```

---

## Three Models

### 1. risk_model (XGBRegressor)
- **Target:** risk_score (0-100, continuous)
- **Features:** All 11 FEATURE_COLS
- **Objective:** `reg:squarederror`
- **Metric:** RMSE on 20% hold-out set

### 2. urgency_model (XGBClassifier, 4-class)
- **Target:** urgency_tier (0=Low, 1=Medium, 2=High, 3=Critical)
- **Features:** All 11 FEATURE_COLS
- **Objective:** `multi:softmax`, num_class=4
- **Metrics:** ROC-AUC (OvR weighted), accuracy on 20% hold-out set

### 3. accident_model (XGBClassifier, binary)
- **Target:** has_accident (1 if nearby_crashes >= 1, else 0)
- **Features:** 9 ACCIDENT_FEATURE_COLS (excludes nearby_crashes and pavement_crash_nearby)
- **Objective:** `binary:logistic`
- **Metrics:** ROC-AUC, F1 score, accuracy on 20% hold-out set
- **Output:** accident_probability (0-1, probability of a traffic crash near this pothole)

---

## Feature Engineering

### Full features (11 columns, used by risk + urgency models)

| Feature | Description |
|---------|-------------|
| `age_days` | Days since pothole was reported |
| `latitude` | GPS latitude |
| `longitude` | GPS longitude |
| `borough_code` | Encoded borough (0-4) |
| `traffic_volume` | Street-level daily vehicle count (ATR) |
| `aadt` | Annual average daily traffic (NY State DOT) |
| `is_highway` | 1 if highway/expressway/bridge/tunnel |
| `descriptor_severity` | Severity weight from complaint descriptor (0-1) |
| `month_opened` | Month the pothole was reported |
| `nearby_crashes` | Collision count within 500m radius |
| `pavement_crash_nearby` | 1 if pavement-specific crash within 1000m |

### Accident model features (9 columns, excludes crash-derived features)

Same as above but WITHOUT `nearby_crashes` and `pavement_crash_nearby` — because those directly encode collision data and would leak the target. The accident model predicts crash probability from intrinsic pothole features alone.

---

## Data Sources

| Dataset | NYC Open Data ID | Records | Description |
|---------|-----------------|---------|-------------|
| 311 Pothole Reports | `erm2-nwe9` | up to 50,000 | Pothole complaints (last 5 years) |
| Traffic Volume | `7ym2-wayt` | up to 200,000 | Automated traffic counts per street segment |
| Motor Vehicle Collisions | `h9gi-nx95` | up to 100,000 | Crash proximity features |
| NY State AADT | `6amx-2pbv` | up to 100,000 | Annual avg daily traffic by road segment |

No API token needed — all NYC Open Data endpoints are public.

---

## Deep Training Param Grid

The `--deep` mode uses RandomizedSearchCV over this parameter space:

```python
_DEEP_GRID = {
    "max_depth":         [3, 4, 5, 6, 7, 8, 9],           # 7 options
    "learning_rate":     [0.01, 0.02, 0.03, 0.05, 0.08, 0.1, 0.15, 0.2],  # 8 options
    "n_estimators":      [200, 300, 400, 600, 800, 1000, 1200],  # 7 options
    "subsample":         [0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0],  # 8 options
    "colsample_bytree":  [0.5, 0.6, 0.7, 0.8, 0.9, 1.0],   # 6 options
    "min_child_weight":  [1, 3, 5, 7, 10],                   # 5 options
    "gamma":             [0, 0.01, 0.05, 0.1, 0.2, 0.3],     # 6 options
    "reg_alpha":         [0, 0.001, 0.01, 0.05, 0.1, 0.5],  # 6 options
    "reg_lambda":        [0.5, 1.0, 1.5, 2.0],               # 4 options
}
```

With n_iter=500 and cv=5: 500 random combinations × 5 folds × 3 models = **7,500 model fits**

---

## Output Files

| File | Description |
|------|-------------|
| `cortex/models/risk_model.joblib` | Risk score regressor |
| `cortex/models/urgency_model.joblib` | Urgency tier classifier (4-class) |
| `cortex/models/accident_model.joblib` | Accident probability classifier (binary) |
| `cortex/models/pothole_cache.parquet` | Cached 311 pothole data |
| `cortex/models/traffic_cache.parquet` | Cached traffic volume data |
| `cortex/models/collision_cache.parquet` | Cached collision data |
| `cortex/models/aadt_cache.parquet` | Cached AADT data |
| `cortex/models/enriched_cache.parquet` | Full enriched dataset |

---

## Monitoring Training

Watch stdout for progress messages:
```
[model] RandomizedSearchCV (deep, n_iter=150, cv=5) — risk model …
       best params: {...}
       best RMSE:   2.XXX
[model] RandomizedSearchCV (deep, n_iter=150, cv=5) — urgency model …
       best params: {...}
       best accuracy: 0.XXXX
[model] RandomizedSearchCV (deep, n_iter=150, cv=5) — accident model …
       best params: {...}
       best ROC-AUC: 0.XXXX
```

Feature importances are printed after all models are trained.

---

## Verify Trained Models

After training, restart the backend and test:

```bash
# Restart backend
cd MainProject/Backend
source .venv/bin/activate
PYTHONPATH=.. uvicorn Backend.app.main:app --reload --port 8000
```

```bash
# Test /predict endpoint
curl http://localhost:8000/predict -X POST \
  -H "Content-Type: application/json" \
  -d '{"potholes": [{"unique_key": "test", "age_days": 30, "borough": "MANHATTAN", "risk_score": 55, "nearby_crashes": 5, "traffic_volume": 8000, "aadt": 50000, "is_highway": 0, "descriptor": "Pothole", "location_type": "", "latitude": 40.75, "longitude": -73.99, "created_date": "2026-01-01", "month_opened": 1, "pavement_crash_nearby": 0, "borough_code": 0, "descriptor_severity": 0.7, "status": "Open"}]}'
```

Response should include `accident_probability` field (0-1):
```json
{
  "predictions": [{
    "risk_score": 55.2,
    "urgency_label": "Medium",
    "urgency_tier": 1,
    "fix_days_estimate": 14,
    "prob_low": 0.25,
    "prob_medium": 0.45,
    "prob_high": 0.20,
    "prob_critical": 0.10,
    "accident_probability": 0.35
  }]
}
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Data fetch fails | Check internet connection, or use `--no-cache` to re-fetch |
| XGBoost import fails | `pip install xgboost scikit-learn` |
| Models dir missing | Auto-created on first run |
| Clear cached data | `rm MainProject/Backend/cortex/models/*.parquet` |
| After training | Restart backend to load new models |
| Training too slow | Use `--quick` for fast iteration, `--deep` for production |
| Training too fast | Increase `--n-iter 300` or `--cv 10` for more thorough search |
| Heuristic fallback | If model files don't exist, API returns heuristic predictions |

---

## Expected Training Metrics

| Model | Metric | Typical Range |
|-------|--------|---------------|
| risk_model | RMSE | 2-5 pts |
| urgency_model | ROC-AUC | 0.85-0.97 |
| urgency_model | Accuracy | 0.75-0.90 |
| accident_model | ROC-AUC | 0.80-0.95 |
| accident_model | F1 | 0.70-0.90 |

---

## Architecture

```
NYC Open Data (4 sources)
  → cortex/data.py (fetch, cache, join)
    → cortex/features.py (build_features, compute_risk_labels, compute_accident_label)
      → cortex/model.py (PotholeRiskModel.fit → 3 XGBoost models)
        → cortex/models/*.joblib (saved models)

API layer:
  app/models/ml_models.py → predict_for_pothole()
    → loads saved models or uses heuristic fallback
    → returns {accident_risk, accident_risk_probability, accident_probability, ...}
```