# Kevin — Frontend API Layer

This folder contains **only Kevin's portion** of the frontend integration.

**Do NOT edit UI files here — those are Taskin's in `Taskin/Front-end/`.**

## Kevin's files

| File | What it does |
|------|-------------|
| `src/api/client.ts` | Base fetch wrapper — reads `VITE_API_BASE_URL` from env |
| `src/api/potholes.ts` | `getPotholesGeoJSON()`, `getPotholeById()`, `predictPothole()` |
| `src/api/stats.ts` | `getStats()` |
| `src/api/alerts.ts` | `sendAlert()` → `POST /alerts/report` (no auth), `adminRefresh()` |
| `index.ts` | TypeScript types matching Kevin's backend response shapes |

## Backend endpoints these call

```
GET  /potholes/geojson        GeoJSON FeatureCollection for the map
GET  /potholes/{unique_key}   Single pothole with ML predictions
POST /predict                 Batch ML scoring
GET  /stats                   Summary + borough breakdown
POST /alerts/report           Public alert (no API key needed)
POST /admin/refresh           Re-fetch + re-score all data
```

## Env var needed

```
VITE_API_BASE_URL=http://localhost:8000
```
