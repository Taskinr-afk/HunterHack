# ML Training Guide — PotholeIQ

## Quick Start

```bash
cd MainProject/Backend
source .venv/bin/activate   # or your virtualenv
PYTHONPATH=.. python -m Backend.cortex.train
```

This runs the full XGBoost training pipeline: fetches data from 4 NYC Open Data APIs, engineers 11 features, trains both XGBoost models with GridSearchCV, and saves serialized models to `cortex/models/`.

Default: fetches up to 10,000 pothole records, runs 3-fold CV grid search over 8 hyperparameter combinations, evaluates on a 20% hold-out set.

## Training Modes

| Flag | Effect | Time |
|------|--------|------|
| *(default)* | GridSearchCV with small param grid (8 combos × 3-fold CV) | ~2 min |
| `--no-tune` | Skip grid search, use default XGBoost params | ~30 sec |
| `--no-cache` | Re-fetch all data from APIs instead of cached parquet files | +10-30 sec |
| `--limit N` | Fetch N pothole records (default 10,000, max ~500,000) | scales linearly |

Examples:

```bash
# Fast iteration with cached data
PYTHONPATH=.. python -m Backend.cortex.train --no-tune

# Full refresh from NYC APIs
PYTHONPATH=.. python -m Backend.cortex.train --no-cache

# Small test run
PYTHONPATH=.. python -m Backend.cortex.train --limit 2000 --no-tune
```

## Models

### 1. risk_model — XGBRegressor
- **Target**: `risk_score` (0–100 continuous)
- **Metric**: RMSE — expected < 5.0 points on hold-out set
- **Param grid**: `max_depth` [4, 6], `learning_rate` [0.05, 0.1], `n_estimators` [200, 400], `subsample` [0.8]

### 2. urgency_model — XGBClassifier (4-class)
- **Target**: `urgency_tier` (0=Low, 1=Medium, 2=High, 3=Critical)
- **Metric**: ROC-AUC (OvR weighted) — expected > 0.90; Accuracy — expected > 0.90
- **Param grid**: same as risk model
- **Output probabilities**: `prob_low`, `prob_medium`, `prob_high`, `prob_critical`

### accident_probability (derived)
- Computed from urgency model outputs: `prob_high + prob_critical`
- Represents the probability of a traffic crash near this pothole
- Served in API responses as `accident_probability` and `accident_risk_probability`

Both models use `colsample_bytree=0.8`, `random_state=42`, `n_jobs=-1`.

## Data Sources

### 1. 311 Pothole Reports (erm2-nwe9)
- **URL**: `https://data.cityofnewyork.us/resource/erm2-nwe9.json`
- **Provides**: Core pothole complaint data — location (lat/lon), status, dates (created/closed), descriptor (pothole type), borough, street name, location type
- **Filter**: `descriptor LIKE '%othole%' OR descriptor LIKE '%ave-in%'`, last 2 years
- **Cache**: `cortex/models/pothole_cache.parquet`

### 2. Automated Traffic Volume (7ym2-wayt)
- **URL**: `https://data.cityofnewyork.us/resource/7ym2-wayt.json`
- **Provides**: Street-level daily vehicle counts (ATR data), joined to potholes by street name
- **Used for**: `traffic_volume` feature — higher traffic = higher risk
- **Cache**: `cortex/models/traffic_cache.parquet`

### 3. Motor Vehicle Collisions (h9gi-nx95)
- **URL**: `https://data.cityofnewyork.us/resource/h9gi-nx95.json`
- **Provides**: Crash proximity features — collision counts within 200m of each pothole, and pavement-specific crashes within 500m
- **Used for**: `nearby_crashes` and `pavement_crash_nearby` features
- **Cache**: `cortex/models/collision_cache.parquet`

### 4. NY State AADT (6amx-2pbv)
- **URL**: `https://data.ny.gov/resource/6amx-2pbv.json`
- **Provides**: Annual average daily traffic by road segment (secondary traffic source)
- **Used for**: `aadt` feature — fallback when street-level traffic data is missing
- **Cache**: `cortex/models/aadt_cache.parquet`

After joining all sources, the fully enriched dataset is cached as `cortex/models/enriched_cache.parquet`.

## Feature Engineering (11 features)

The `FEATURE_COLS` list in `cortex/features.py` defines the input to both XGBoost models:

| # | Feature | Type | Description | Source |
|---|---------|------|-------------|--------|
| 1 | `age_days` | float | Days since the pothole was reported | 311 created_date |
| 2 | `latitude` | float | Pothole latitude | 311 location |
| 3 | `longitude` | float | Pothole longitude | 311 location |
| 4 | `borough_code` | int | Numeric borough encoding (Manhattan=5, Brooklyn=4, Queens=3, Bronx=2, Staten Island=1) | 311 borough |
| 5 | `traffic_volume` | float | Street-level daily vehicle count (ATR) | Traffic volume |
| 6 | `aadt` | float | Annual average daily traffic | NY State AADT |
| 7 | `is_highway` | int | 1 if location_type contains highway/expressway/bridge/tunnel | 311 location_type |
| 8 | `descriptor_severity` | float | Severity weight (highway pothole=1.0, cave-in=0.95, street pothole=0.55-0.70) | 311 descriptor |
| 9 | `month_opened` | int | Month the pothole was reported (seasonality signal) | 311 created_date |
| 10 | `nearby_crashes` | int | Collision count within 200m radius | Collisions (h9gi-nx95) |
| 11 | `pavement_crash_nearby` | int | 1 if pavement-specific crash within 500m | Collisions (h9gi-nx95) |

**Important**: Feature order must match exactly what the saved models were trained on. Never reorder or add features without retraining.

### Derived labels (not input features)

Risk scores and urgency tiers are computed from features via `compute_risk_labels()`:

- **risk_score** (0–100): Weighted formula — age (40pts max) + traffic_ATR (15pts) + AADT (10pts) + descriptor_severity (15pts) + highway_bonus (8pts) + nearby_crashes (12pts) + noise (~2.5pts)
- **urgency_tier** (0–3): Binned from risk_score — Low [0-25), Medium [25-50), High [50-75), Critical [75-100]

### NaN handling

XGBoost handles NaN natively. When a street name doesn't match the traffic dataset, `traffic_volume` is left as NaN rather than zero-imputed, letting XGBoost learn the "missing" signal.

## Output Files

All saved to `MainProject/Backend/cortex/models/`:

| File | Description |
|------|-------------|
| `risk_model.joblib` | XGBRegressor — risk score predictor |
| `urgency_model.joblib` | XGBClassifier — urgency tier classifier |
| `pothole_cache.parquet` | Cached 311 pothole data |
| `traffic_cache.parquet` | Cached ATR traffic data |
| `collision_cache.parquet` | Cached collision data |
| `aadt_cache.parquet` | Cached AADT data |
| `enriched_cache.parquet` | Full joined dataset (all sources merged) |

To clear all caches: `rm MainProject/Backend/cortex/models/*.parquet`

## Monitoring Training

Watch stdout for progress messages:

```
=======================================================
  PotholeIQ — ML Training Pipeline
=======================================================

[1/3] Fetching enriched NYC dataset (limit=10000) …
      3,936 records in 12.4s
      traffic_volume : 78.3% filled
      aadt           : 45.2% filled
      nearby_crashes : mean=4.7
      pavement flag  : 12.1% of potholes

[2/3] Training XGBoost models (tune=True) …
  [model] GridSearchCV — risk model …
       best params: {'max_depth': 6, 'learning_rate': 0.1, ...}
  [model] GridSearchCV — urgency model …
       best params: {'max_depth': 6, 'learning_rate': 0.1, ...}

  ── Eval (20% hold-out, n=788) ──
  risk_score   RMSE    : 2.770 pts
  urgency_tier ROC-AUC : 0.9590  (OvR weighted)
  urgency_tier Accuracy: 0.9200

  ── Feature Importances ──
  risk_model:
    age_days                    0.3421
    descriptor_severity         0.1876
    ...
  urgency_model:
    age_days                    0.2890
    ...

[3/3] Saving models (joblib) …
  Models saved → cortex/models/

✓ Pipeline complete — models ready at cortex/models/
```

- Each GridSearchCV combination is tested with 3-fold cross-validation
- Final evaluation is on a 20% hold-out set (stratified split)
- Expected metrics: RMSE < 5.0 for risk, ROC-AUC > 0.90 for urgency
- Feature importances are printed for both models after training

## Verify Trained Models

```bash
curl http://localhost:8000/predict -X POST \
  -H "Content-Type: application/json" \
  -d '{"potholes": [{"unique_key": "test-001", "age_days": 30, "borough": "MANHATTAN", "risk_score": 55, "nearby_crashes": 5, "traffic_volume": 8000, "aadt": 50000, "is_highway": 0, "descriptor": "Pothole", "location_type": "", "latitude": 40.75, "longitude": -73.99, "created_date": "2026-01-01", "month_opened": 1, "pavement_crash_nearby": 0, "borough_code": 0, "descriptor_severity": 0.7, "status": "Open"}]}'
```

Response should include `accident_probability` field alongside `risk_score`, `urgency_label`, `prob_low`, etc.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Training fails on data fetch | Check internet connection. Use `--no-cache` to force re-fetch from APIs |
| XGBoost import fails | `pip install xgboost scikit-learn` |
| `models/` directory missing | Auto-created on first run — no action needed |
| NYC API rate limits (429 errors) | Wait a few minutes, re-run. APIs are rate-limited without an app token |
| NYC API timeouts | Use `--limit 2000` for a smaller dataset, or retry |
| Stale cached data | `rm MainProject/Backend/cortex/models/*.parquet` to clear all caches |
| Model file not found at startup | Backend falls back to heuristic predictions when `.joblib` files are missing |
| Feature order mismatch | Feature order is defined in `FEATURE_COLS` (features.py). Never reorder without retraining |
| NaN handling | XGBoost handles NaN natively — `traffic_volume` and `aadt` may be NaN when street names don't match |

## Integration with Backend

1. **Auto-loading**: Models are lazy-loaded by `app/main.py` via `_get_model()`. First `/predict` call loads from disk.

2. **Heuristic fallback**: When model `.joblib` files don't exist, `_get_model()` returns `"heuristic"` and the `/predict` endpoint uses rule-based predictions instead.

3. **After training**, restart the backend to pick up new models:
   ```bash
   # If using --reload, just save the models — uvicorn auto-restarts
   # Otherwise, manually restart:
   PYTHONPATH=.. uvicorn Backend.app.main:app --reload --port 8000
   ```

4. **Data refresh**: Use the admin endpoint to re-fetch data and re-score without restarting:
   ```bash
   curl -X POST "http://localhost:8000/admin/refresh?secret=potholeiq-dev"
   ```