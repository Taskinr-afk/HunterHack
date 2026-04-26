# Kevin — Frontend Integration Progress Log

This file tracks Kevin's work on wiring the backend API into Taskin's frontend.
Kevin owns `src/api/` only — all UI/component files belong to Taskin.

---

## Current Step

- **Phase 9: Live Frontend Hookup**
- Step 9.1: Confirm Taskin wires real API calls — replace `mockPotholes` and
  `buildMockStatsResponse()` in `MapPage.tsx` and `Dashboard.tsx` with the
  query hooks from `src/api/potholes.ts` and `src/api/stats.ts`

---

## Upcoming Steps

- **Step 9.2:** End-to-end smoke test — both servers running, map dots load
  from real NYC data, clicking a dot shows live ML predictions
- **Step 9.3:** Alert flow — "Alert DOT" button in `PotholeDetail.tsx` hits
  `POST /alerts/report` (public endpoint, no API key needed)
- **Step 9.4:** Viewport filter — confirm `useViewportPotholes.ts` passes
  `lat_min`, `lat_max`, `lng_min`, `lng_max` to `getPotholesGeoJSON()` so
  the map only fetches dots in the current viewport
- **Step 9.5:** Deploy — backend on Render, frontend on Vercel, update
  `VITE_API_BASE_URL` to the live Render URL

---

## Completed Steps

### Phase 1 — Backend API (Kevin owns)
- [x] FastAPI app with all routes (`Backend/app/main.py`)
- [x] SQLite database layer with potholes + alerts tables (`Backend/app/database.py`)
- [x] XGBoost ML pipeline — risk score + urgency tier (`Backend/cortex/`)
- [x] `/potholes/geojson` — GeoJSON FeatureCollection for map layer
- [x] `/api/potholes` + `/api/potholes/{id}` — list + detail with ML predictions
- [x] `/api/stats/summary` + `/api/stats/timeline` — borough stats + weekly chart
- [x] `/api/predictions/{id}` — accident risk + repair ETA
- [x] `/alerts/send`, `/alerts/scan`, `/alerts/report` — alert endpoints
- [x] `/admin/refresh` — re-fetch NYC data + re-score
- [x] Rate limiting (slowapi), security headers, CORS from env var
- [x] 23/23 tests passing (`Backend/tests/`)

### Phase 2 — Data
- [x] 4 NYC Open Data datasets joined (311 potholes, traffic, AADT, collisions)
- [x] 3,936 real NYC potholes in SQLite with risk scores
- [x] `Backend/data/potholes_raw.csv` — 856 KB raw data
- [x] `Backend/data/potholes_embeddings.csv` — 18 MB, 384-dim MiniLM embeddings

### Phase 3 — Frontend API Layer (Kevin owns)
- [x] `src/api/client.ts` — base fetch wrapper reading `VITE_API_BASE_URL`
- [x] `src/api/potholes.ts` — `getPotholesGeoJSON()`, `getPotholeById()`, `predictPothole()`
- [x] `src/api/stats.ts` — `getStats()`
- [x] `src/api/alerts.ts` — `sendAlert()` → `POST /alerts/report` (no auth needed)
- [x] `index.ts` — TypeScript types matching all backend response shapes

### Phase 4 — Integration Fixes
- [x] Added `days_open` alias (frontend expected this, backend had `age_days`)
- [x] Added `nearby_collision_count` alias (frontend alias for `nearby_crashes`)
- [x] Added `address` field — composed as `"STREET, Borough, NY"`
- [x] Added `city` field — always `"New York"` for NYC data
- [x] Added `repair_eta` — ISO date computed from `fix_days_estimate`
- [x] Added `impact_score` alias for `risk_score`
- [x] Fixed stats `avg_days_open` field name to match frontend `BoroughStats` type
- [x] Added viewport bbox filter (`lat_min/max`, `lng_min/max`) to `/api/potholes`
- [x] `POST /alerts/report` — public endpoint, no API key, for frontend use

---

## How to Run (Both Servers)

```bash
# Terminal 1 — Kevin's backend (from repo root)
PYTHONPATH=. uvicorn Backend.app.main:app --reload --port 8000

# Terminal 2 — Taskin's frontend
cd Taskin/Front-end
npm install
npm run dev
# Opens at http://localhost:5173
```

`.env` needed in `Taskin/Front-end/`:
```
VITE_API_BASE_URL=http://localhost:8000
```

---

## Field Reference (Backend → Frontend)

| Backend field | Frontend type field | Notes |
|---|---|---|
| `unique_key` | `unique_key` | pothole ID |
| `age_days` | `age_days` + `days_open` | both returned |
| `risk_score` | `risk_score` + `impact_score` | both returned |
| `nearby_crashes` | `nearby_crashes` + `nearby_collision_count` | both returned |
| `street_name` + `borough` | `address` | composed |
| — | `city` | always "New York" |
| `fix_days_estimate` | `repair_eta` | computed ISO date |
| `urgency_tier` | `urgency_tier` | 0=Low 1=Med 2=High 3=Critical |
