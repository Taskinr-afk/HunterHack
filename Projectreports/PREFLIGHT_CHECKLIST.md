# PotholeIQ — Hackathon Pre-Flight Checklist

**Complete before demo. Check each box as you verify it.**

---

## Backend (Kevin — Person B)

### Environment
- [x] Python 3.13.7 installed (`python3 --version`)
- [x] All dependencies installed (`pip install -r Backend/requirements.txt`)
- [x] `.env` file exists — copy from `Backend/.env.example`

### Server
- [x] `PYTHONPATH=. uvicorn Backend.app.main:app --reload --port 8000` starts clean
- [x] `GET http://localhost:8000/` returns `{"status": "PotholeIQ API is running"}`
- [x] `GET http://localhost:8000/docs` opens Swagger UI with 16 endpoints

### Data
- [x] SQLite DB populated — `GET /api/potholes?limit=5` returns real NYC data
- [x] `GET /api/stats/summary` shows 3,936 potholes, 792 open, all 5 boroughs
- [x] NYC Open Data API accessible: `curl "https://data.cityofnewyork.us/resource/erm2-nwe9.json?$limit=1"`

### ML Models
- [x] `Backend/cortex/models/risk_model.joblib` exists
- [x] `Backend/cortex/models/urgency_model.joblib` exists
- [x] `GET /api/predictions/68538157` returns `accident_risk`, `predicted_repair_days`

### Tests
- [x] `PYTHONPATH=. pytest Backend/tests/ -v` → 23/23 passing

### Alerts
- [x] `POST /api/alerts/send` with `x-api-key` header creates an alert
- [x] `GET /api/alerts/history` returns history

### Demo Fallback
- [x] `python Backend/scripts/seed_demo_data.py` runs without errors (backup if NYC API is down)

---

## Deployment (Render)

- [ ] Pushed latest `main` to GitHub
- [ ] Render Web Service created at render.com
  - Root Directory: `Backend`
  - Build Command: `pip install -r requirements.txt`
  - Start Command: `uvicorn Backend.app.main:app --host 0.0.0.0 --port $PORT`
- [ ] Env vars set in Render dashboard (from `Backend/.env.example`)
- [ ] `https://your-backend.onrender.com/` returns health check JSON
- [ ] `https://your-backend.onrender.com/api/potholes?limit=5` returns data
- [ ] Update `ALLOWED_ORIGINS` in Render to match Vercel frontend URL

---

## Integration with Frontend (Taskin — Person A)

- [ ] Taskin's frontend `.env` has `VITE_API_BASE_URL=http://localhost:8000`
- [ ] Map loads pothole dots from `GET /potholes/geojson`
- [ ] Clicking a dot calls `GET /api/potholes/{id}` and shows ML predictions
- [ ] "Alert DOT" button calls `POST /api/alerts/send`
- [ ] Dashboard calls `GET /api/stats/summary` and `GET /api/stats/timeline`

---

## Common Quick Fixes

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError` | Run from repo root with `PYTHONPATH=.` |
| `Address already in use` | `kill $(lsof -t -i:8000)` |
| Empty pothole data | Re-populate: `python3 -c "from Backend.cortex.data import fetch_all; from Backend.cortex.model import score_potholes; from Backend.app.database import init_db,upsert_potholes; init_db(); upsert_potholes(score_potholes(fetch_all()))"` |
| CORS error in browser | Update `ALLOWED_ORIGINS` in `.env` to match frontend URL |
| Models not found | `PYTHONPATH=. python -m Backend.cortex.train --no-tune` |
| NYC API down | `python Backend/scripts/seed_demo_data.py` |

---

## 5-Min Demo Run Order

1. `PYTHONPATH=. uvicorn Backend.app.main:app --port 8000`
2. Open frontend → verify map dots load
3. Click a red dot → verify ML predictions in panel
4. Switch to Dashboard → verify stats
5. Click "Alert DOT" → verify alert is created
6. `GET /api/alerts/history` → show alert was logged

See full script: `Projectreports/DEMO_SCRIPT.md`
