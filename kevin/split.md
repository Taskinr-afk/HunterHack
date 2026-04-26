# Taskin + Kevin Split Tasks
> Kevin's copy — updated with current completion status

## Ownership Split

### Taskin
- Owns all UI work under `Taskin/Front-end/` and `MainProject/Frontend/`
- Owns map/list browsing experience, motion, filters, mobile layout, and dashboard presentation
- Owns keeping the frontend tree merge-safe:
  - `public/`, `src/components/`, `src/hooks/`, `src/pages/`, `src/types/`, `src/utils/`
  - `src/App.tsx`, `src/main.tsx`, `src/index.css`
  - `.env.example`, `package.json`, `tailwind.config.ts`, `tsconfig.json`, `vite.config.ts`

### Kevin
- Owns FastAPI routes and real data contract
- Owns `kevin/app/`, `kevin/cortex/`, `kevin/data/`, `kevin/tests/`, `kevin/scripts/`
- Owns `kevin/Front-end/src/api/` — API layer files only

---

## Kevin Merge Checklist

### Backend endpoints live ✅
- [x] `GET /potholes/geojson` — GeoJSON FeatureCollection for the map
- [x] `GET /potholes/{unique_key}` — single pothole detail with ML predictions
- [x] `GET /stats` — summary stats (total open/closed, avg days, borough breakdown)
- [x] `GET /api/stats/summary` — borough breakdown with `avg_days_open`, `total_collisions`
- [x] `GET /api/stats/timeline` — weekly opened vs closed time series
- [x] `POST /predict` — batch ML scoring
- [x] `POST /alerts/send` — DOT alert (admin key required)
- [x] `POST /alerts/report` — public citizen report (no key needed — for map UI)
- [x] `POST /admin/refresh` — re-fetch NYC data + re-score all potholes

### Backend fields confirmed ✅
- [x] `latitude` / `longitude`
- [x] `borough`
- [x] `city` — always `"New York"` (composed)
- [x] `zip_code` — field present (null until zip data added)
- [x] `address` — composed as `"STREET, Borough, NY"`
- [x] `status` — `"Open"` | `"Closed"`
- [x] `days_open` — alias for `age_days` (int)
- [x] `risk_score` — float 0–100 from XGBoost
- [x] `impact_score` — alias for `risk_score`
- [x] `nearby_collision_count` — alias for `nearby_crashes` (count within 200m)
- [x] `traffic_volume` — real daily vehicle count from NYC DOT ATR data
- [x] `accident_risk` — `LOW` / `MEDIUM` / `HIGH` / `CRITICAL`
- [x] `accident_risk_probability` — float 0–1
- [x] `predicted_repair_days` — int
- [x] `repair_eta` — ISO date string (`"2026-04-18"`)
- [x] `created_date` / `closed_date`
- [x] `urgency_tier` — `0`=Low `1`=Medium `2`=High `3`=Critical
- [x] `urgency_label` — `"Low"` / `"Medium"` / `"High"` / `"Critical"`

### `/stats` response confirmed ✅
- [x] `total_open`, `total_closed`, `avg_days_open`
- [x] Borough breakdown with `open_count`, `closed_count`, `avg_days_open`, `total_collisions`
- [x] Weekly timeline — `GET /api/stats/timeline` returns `[{week, opened, closed}]`

### Mock → Real data swap ✅
- [x] `MapPage.tsx` — `mockPotholes` replaced with `useViewportPotholes` real API hook
- [x] `Dashboard.tsx` — `buildMockStatsResponse()` replaced with live `/api/stats/summary` + `/api/stats/timeline`
- [x] `src/api/client.ts` — base fetch wrapper reading `VITE_API_BASE_URL`
- [x] `src/api/potholes.ts` — `getPotholesGeoJSON()`, `getPotholeById()`, `predictPothole()`
- [x] `src/api/stats.ts` — `getStats()`
- [x] `src/api/alerts.ts` — `sendAlert()` → `POST /alerts/report` (public, no auth)

### Alert flow
- [x] `POST /alerts/report` public endpoint live — no API key needed from the UI
- [x] Alert stored in SQLite, history returned by `GET /alerts/history`
- [ ] `PotholeDetail.tsx` mock alert (900ms fake delay) still needs replacing with real `sendAlert()` call — **Taskin's task**

---

## Current State (as of 2026-04-26)

- Backend fully live — 3,936 real NYC potholes in SQLite, XGBoost risk scores, all endpoints passing
- `MainProject/Frontend/` — canonical frontend with real API calls wired (Kazi merged this)
- `Taskin/Front-end/` — original frontend, `MapPage` and `Dashboard` updated to real API
- One mock remaining: `PotholeDetail.tsx` alert button — Taskin needs to call `sendAlert(pothole.unique_key)`
- Deployment next: backend → Render, frontend → Vercel

---

## How to Run Both Servers

```bash
# Terminal 1 — Kevin's backend
PYTHONPATH=. uvicorn kevin.app.main:app --reload --port 8000

# Terminal 2 — Frontend (MainProject canonical)
cd MainProject/Frontend
npm run dev
# Opens at http://localhost:5173
```

`.env` in `MainProject/Frontend/`:
```
VITE_API_BASE_URL=http://localhost:8000
VITE_ADMIN_API_KEY=potholeiq-dev
```
