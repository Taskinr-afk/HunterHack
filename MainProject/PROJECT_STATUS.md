# PotholeIQ — Project Status & How to Run

**Last updated:** 2026-04-26  
**Repo:** https://github.com/Taskinr-afk/HunterHack  
**Hackathon:** HunterHack 2026, Hunter College

---

## Quick Start

### 1. Backend
```bash
cd MainProject/Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=.. uvicorn Backend.app.main:app --reload --port 8000
```
The backend auto-seeds 500 demo potholes on first run (empty DB).

### 2. Frontend
```bash
cd MainProject/Frontend
npm install
npm run dev
```
Opens at http://localhost:5173

### 3. One-command preflight (checks + starts both)
```bash
bash MainProject/scripts/preflight.sh
```
See `MainProject/scripts/preflight.sh --help` for options.

### 4. Run tests
```bash
cd MainProject/Backend
source .venv/bin/activate
PYTHONPATH=../.. pytest tests/ -v
```
Expected: 36/37 pass. The 1 failure (`test_real_model_loads`) requires trained XGBoost models.

### 5. Train ML models (optional, for /predict endpoint)
```bash
PYTHONPATH=.. python -m Backend.cortex.train
```

---

## Architecture

```
React + TypeScript + Vite (Frontend)
  ├── Leaflet map with CARTO dark tiles
  ├── TanStack React Query (server state)
  ├── Framer Motion (animations)
  └── Recharts (dashboard charts)
       │
       ▼  Vite proxy → localhost:8000
FastAPI Backend (Python)
  ├── 16 REST endpoints
  ├── SQLite database (auto-seeded)
  ├── XGBoost ML models (heuristic fallback when untrained)
  └── CORS + security headers
       │
       ▼
4 NYC Open Data sources
  (311 Potholes, Traffic Volume, AADT, Motor Vehicle Collisions)
```

---

## API Endpoints (all verified, 30/30 tests pass)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| GET | `/potholes/geojson` | GeoJSON map layer (with filters) |
| GET | `/potholes/{unique_key}` | Single pothole (legacy) |
| GET | `/api/potholes` | List potholes (with viewport bbox) |
| GET | `/api/potholes/{id}` | Pothole detail + ML predictions |
| POST | `/predict` | Score arbitrary pothole data |
| GET | `/stats` | Summary stats by borough |
| GET | `/api/stats/summary` | Stats summary (open/closed/avg_age_days) |
| GET | `/api/stats/timeline` | Weekly opened vs closed |
| POST | `/admin/refresh` | Re-fetch NYC data + re-score |
| POST | `/alerts/send` | Send DOT alert (requires x-api-key) |
| GET | `/alerts/history` | Alert history |
| POST | `/alerts/scan` | Scan for high-risk unalerted potholes |
| GET | `/docs` | OpenAPI docs |

---

## Canonical Field Names

The project uses these canonical field names everywhere. Do NOT create aliases:

| Canonical | ❌ Never use |
|-----------|-------------|
| `unique_key` | id, pothole_id (in pothole context) |
| `age_days` | days_open |
| `risk_score` | impact_score |
| `nearby_crashes` | nearby_collision_count |
| `avg_age_days` | avg_days_open (in stats context) |

---

## Database Schema

```sql
CREATE TABLE potholes (
    unique_key TEXT PRIMARY KEY,
    latitude REAL NOT NULL, longitude REAL NOT NULL,
    borough TEXT, street_name TEXT, zip_code TEXT,
    descriptor TEXT, status TEXT,
    created_date TEXT, closed_date TEXT, location_type TEXT,
    age_days REAL DEFAULT 0, risk_score REAL DEFAULT 0,
    urgency_label TEXT DEFAULT 'Low', urgency_tier INTEGER DEFAULT 0,
    fix_days_estimate INTEGER DEFAULT 30,
    traffic_volume REAL, aadt REAL,
    nearby_crashes INTEGER DEFAULT 0,
    pavement_crash_nearby INTEGER DEFAULT 0,
    prob_low REAL, prob_medium REAL, prob_high REAL, prob_critical REAL,
    scored_at TEXT
);
```

---

## GeoJSON Contract

Backend returns coordinates in `feature.geometry.coordinates` as `[lng, lat]`  
(per GeoJSON spec). Frontend reads from `geometry.coordinates`, NOT from properties.

---

## Environment Variables

See `MainProject/Backend/.env.example`:
- `ADMIN_API_KEY` — default: `potholeiq-dev`
- `ALLOWED_ORIGINS` — default: `http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173`
- `DATABASE_URL` — default: `sqlite:///./cortex/models/potholes.db`
- `ENVIRONMENT` — set to `production` for HTTPS redirect

---

## Test Results (as of 2026-04-26)

```
36/37 passed
  test_api.py:    30/30 PASSED ✓
  test_ml.py:      6/7 PASSED ✓
  test_real_model_loads: FAILED (expected — needs trained XGBoost models)
```

All 30 API tests pass including:
- Canonical schema fields verified
- No internal fields leaked (zip_code, location_type, etc.)
- Stats endpoint uses avg_age_days
- GeoJSON returns proper [lng, lat] coordinates
- Alerts require valid admin key

---

## Bugs Fixed (full list)

1. **Map markers invisible** — Frontend read lat/lng from `properties` instead of `geometry.coordinates`. Fixed.
2. **Dashboard NaN** — `avg_age_days` vs `avg_days_open` mismatch. Standardized to `avg_age_days`.
3. **Empty database** — Added auto-seed on startup in `app/seed.py`.
4. **No mock fallback** — MapPage and Dashboard now fall back to mock data with `DataSourceBanner`.
5. **scored_at column** — Removed from `POTHOLE_COLS` (not in CREATE TABLE).
6. **Dead alias fields** — Removed `city`, `zip_code`, `address`, `days_open`, `impact_score`, `nearby_collision_count` from `_map()` and `PotholeResponse`.
7. **PotholeDetail missing lat/lng** — `PotholeDetail` now includes `latitude`/`longitude`; MapPage merges detail with GeoJSON pothole.
8. **accident_risk_probability** — Standardized: both GeoJSON and detail paths use backend-computed value.
9. **repair_eta** — Added to `PotholeDetail` type, `getPotholeById` mapper, and displayed in PotholeDetail component.
10. **CORS defaults** — Expanded to include `localhost:3000` and `127.0.0.1:5173`.
11. **CSP headers** — Added `*.cartocdn.com` for img-src, font-src, connect-src.
12. **load_dotenv ordering** — Moved before all local imports so env vars are available at import time.
13. **Auth key timing** — `ADMIN_API_KEY` now read at call time, not module level. Default: `potholeiq-dev`.
14. **Predict endpoint fallback** — Returns heuristic predictions when XGBoost models aren't available.
15. **seed.py commit** — Added `conn.commit()` after `executemany()`.
16. **Admin refresh UI** — Dashboard has a "Refresh data" button with `useMutation` and query invalidation.