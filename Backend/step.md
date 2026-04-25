# Backend Development Progress Log

This file tracks the current step and progress for backend/API work in the Backend/ folder.

---

## Current Step

- Phase 8: Complete ✓ — all phases done, backend ready for frontend wiring

---

## Completed Steps

- Phase 0: Python Environment Setup
  - Python 3.13.7, pip, dependencies installed
- Phase 1: Schemas & Main App
  - Step 1.1: Pydantic schemas (Backend/app/schemas.py)
  - Step 1.2: FastAPI app entry point (Backend/app/main.py)
- Phase 2: Endpoint Implementation
  - Step 2.1: SQLite database layer (Backend/app/database.py)
- Phase 3: ML Model Logic
  - Step 3.1: XGBoost model loading + prediction (Backend/cortex/model.py)
- Phase 4: Alerts Endpoint
  - Step 4.1: Alerts router registered (Backend/app/alerts.py, main.py)
- Phase 5: End-to-End Integration Testing
  - Step 5.1: All endpoints and model predictions verified
- Phase 6: Frontend Integration & Deployment Prep
  - Step 6.1: CORS env config, .env.example, Dockerfile, clean stubs (Backend/app/main.py)
  - Step 6.2: Data export + 384-dim embedding pipeline (Backend/cortex/embed.py → Backend/data/)
  - Step 6.3: GeoJSON contract verified — FeatureCollection with [lng,lat] coords, risk_score,
              urgency_label, prob_* fields. Shape confirmed valid for Leaflet/Mapbox.
- Phase 7: Real Alert Service
  - Step 7.1: SMTP email + SQLite alert persistence (Backend/app/alerts.py)
    - POST /alerts/send  — manual alert for a pothole, stored in alerts table
    - POST /alerts/scan  — auto-scan open potholes above ALERT_RISK_THRESHOLD (default 75),
                           sends alert for any not yet alerted
    - GET  /alerts/history — returns alert history from SQLite
    - alerts table added to database.py with FK to potholes
    - SMTP configured via env vars (logs to console when not set)
- Phase 8: Full Integration Test
  - Step 8.1: All endpoints tested end-to-end
    - GET  /              → {"status": "PotholeIQ API is running"}
    - GET  /stats         → 3,936 potholes, 792 open, breakdown by borough
    - GET  /potholes/geojson → valid GeoJSON FeatureCollection with risk scores
    - POST /alerts/scan   → 3 potholes alerted, stored in DB
    - GET  /alerts/history → history returned from SQLite

---

## GeoJSON Contract for Frontend (Taskin)

```
GET /potholes/geojson?status=Open&min_risk=0&limit=5000

Response:
{
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "geometry": { "type": "Point", "coordinates": [longitude, latitude] },
    "properties": {
      "unique_key": "68538157",
      "status": "Open",
      "descriptor": "Pothole",
      "borough": "MANHATTAN",
      "street_name": "HARLEM RIVER DRIVE",
      "age_days": 23.1,
      "risk_score": 51.8,          ← 0–100
      "urgency_label": "Medium",   ← Low / Medium / High / Critical
      "urgency_tier": 1,           ← 0 / 1 / 2 / 3
      "fix_days_estimate": 14,
      "nearby_crashes": 10,
      "pavement_crash_nearby": 1,
      "prob_low": 0.0,
      "prob_medium": 0.585,
      "prob_high": 0.414,
      "prob_critical": 0.0,
      "created_date": "2026-04-02 15:04:57",
      "closed_date": null
    }
  }],
  "meta": { "count": 5000 }
}

Query params:
  status    Open | Closed
  borough   MANHATTAN | BROOKLYN | QUEENS | BRONX | STATEN ISLAND
  min_risk  float 0–100
  urgency   Low | Medium | High | Critical
  limit     max 10000
```
