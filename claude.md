# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**PotholeIQ** — HunterHack 2026 hackathon project. NYC pothole risk intelligence map: real-time pothole tracking from NYC Open Data, ML-powered risk scoring, and automated alerts to the NYC DOT.

**Team folders:** `Taskin/` (frontend), `Kevin/` (ML + API), `Kazi/`, `Rakhmanjan/`

---

## Architecture

```
311 Potholes ──┐
Traffic (ATR) ─┤─► kevin/cortex/ ─► SQLite DB ─► kevin/api/ ─► Frontend
AADT (NY DOT) ─┤   (XGBoost)        (GeoJSON)     (FastAPI)
Collisions ────┘
```

### Kevin's module (`kevin/`)

**`cortex/`** — ML pipeline (Python, XGBoost + joblib)
- `data.py` — fetches and joins 4 NYC Open Data datasets; caches as `.parquet` in `cortex/models/`
- `features.py` — engineers 11 features; `FEATURE_COLS` is the single source of truth for feature order
- `model.py` — `PotholeRiskModel`: two XGBoost models (regressor for risk 0–100, classifier for urgency tier 0–3); GridSearchCV tuning; joblib serialization
- `train.py` — CLI entry point for the full pipeline

**`api/`** — FastAPI backend
- `main.py` — all routes; lazy-loads the joblib model on first `/predict` call
- `database.py` — SQLite read/write; `upsert_potholes()` populates from scored DataFrame
- `schemas.py` — Pydantic models for all request/response shapes

**`ml/`** (root-level) — earlier prototype; superseded by `kevin/cortex/` but kept for reference. Uses XGBoost native `.json` instead of joblib.

### Data flow

1. `fetch_all()` in `cortex/data.py` fetches potholes (last 2 years), traffic volume, AADT, and collisions → joins them → returns enriched DataFrame
2. `PotholeRiskModel.fit(df)` engineers features → generates domain-logic labels → trains with GridSearchCV → saves `.joblib`
3. `upsert_potholes(scored_df)` writes all rows to SQLite (`cortex/models/potholes.db`)
4. FastAPI reads from SQLite for map/stats endpoints; runs live inference only on `POST /predict`

### NYC Open Data datasets

| ID | Dataset | Used for |
|----|---------|----------|
| `erm2-nwe9` | 311 Service Requests | Core pothole reports |
| `7ym2-wayt` | Automated Traffic Volume Counts | Street-level daily vehicle counts |
| `6amx-2pbv` | NY State AADT | Annual avg daily traffic (data.ny.gov) |
| `h9gi-nx95` | Motor Vehicle Collisions | Crash counts within 200 m of each pothole |

---

## Commands

### ML pipeline (run from repo root)

```bash
# Full pipeline — fetch data, tune, train, save models
python -m kevin.cortex.train

# Skip GridSearchCV (faster, ~10s vs ~2min)
python -m kevin.cortex.train --no-tune

# Re-fetch all datasets, bypass parquet cache
python -m kevin.cortex.train --no-cache

# Smaller fetch for quick iteration
python -m kevin.cortex.train --limit 2000 --no-tune
```

### API server

```bash
# Start dev server (from repo root)
PYTHONPATH=. uvicorn kevin.api.main:app --reload --port 8000

# Populate SQLite after training
python3 -c "
from kevin.cortex.data import fetch_all
from kevin.cortex.model import score_potholes
from kevin.api.database import init_db, upsert_potholes
init_db(); df = fetch_all(); upsert_potholes(score_potholes(df))
"

# Force data refresh via API (requires ADMIN_SECRET env var, default: potholeiq-dev)
curl -X POST "http://localhost:8000/admin/refresh?secret=potholeiq-dev"
```

### API endpoints

```
GET  /                         health check
GET  /potholes/geojson         GeoJSON FeatureCollection — params: status, borough, min_risk, urgency, limit
GET  /potholes/{unique_key}    single pothole
POST /predict                  score arbitrary JSON pothole data (no lat/lon required)
GET  /stats                    summary + per-borough breakdown
POST /admin/refresh            re-fetch + re-score + reload DB
```

---

## Key design decisions

**Labels are derived, not collected.** There is no ground-truth "this pothole caused an accident" label. `compute_risk_labels()` in `features.py` generates `risk_score` (0–100) from a weighted formula (age × traffic × severity × crash proximity). XGBoost learns to predict this from raw observable features — the value is generalization to new potholes.

**XGBoost handles NaN natively.** When a street name doesn't match the traffic dataset, `traffic_volume` is left as `NaN`. Do not impute with zeros — XGBoost's split-finding ignores NaN correctly.

**Caching layers.** Each dataset has its own `.parquet` cache in `cortex/models/`. The fully joined DataFrame is cached as `enriched_cache.parquet`. Delete these files to force a re-fetch. The SQLite DB (`potholes.db`) is the serving layer — separate from the training cache.

**Feature order is fixed.** `FEATURE_COLS` in `features.py` must match exactly what the saved models were trained on. Never reorder or add features without retraining.

**Borough centroid fallback in `/predict`.** When a POST request omits `latitude`/`longitude`, `main.py` substitutes the borough centroid so spatial features don't crash.

---

## Workflow rules (from existing claude.md)

- Enter plan mode for any task with 3+ steps or architectural decisions.
- Never mark a task complete without proving it works.
- For non-trivial changes: ask "is there a more elegant way?" before implementing.
- When given a bug: fix it autonomously — point at logs/errors and resolve.
