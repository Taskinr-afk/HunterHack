# Rakhmanjan — Backend Security

Security layer for the PotholeIQ backend (Phases 0–2 complete).

## Completed Phases

### Phase 0: Secrets Management
- `.gitignore` — prevents `.env`, `*.db`, `*.pkl`, `*.joblib` from being committed
- `.env.example` — safe template with fake values (never commit real `.env`)

### Phase 1: Backend API Security
- CORS configured (only allowed origins from `ALLOWED_ORIGINS` env var)
- Rate limiting via `slowapi` (60/min GeoJSON, 120/min single pothole, 30/min predict)
- Input validation with Pydantic models (`PotholeFilterParams`, `AlertRequest`)
- Parameterized SQL queries everywhere (`?` placeholders, no string concatenation)
- Admin API key auth on `/alerts/send` and `/admin/refresh`

### Phase 2: Data Security
- All `SELECT *` replaced with explicit column lists (`POTHOLE_COLS`, `ALERT_COLS`)
- Response schemas only expose safe fields (no personal info)
- `etl.py` validates external data before storage (coordinate bounds, text sanitization, status normalization)
- `database.py` rewritten: added `upsert_potholes()`, `query_potholes()`, `get_stats()`, `get_conn()` alias, fixed `insert_alert()` and `get_high_risk_unalerted()` signatures

### Phase 3: Frontend Security (paused — waiting for frontend code)
- Security headers already set in `main.py` (CSP, X-Frame-Options, X-XSS-Protection, etc.)
- Steps 3.1–3.2 require frontend code to apply

## Key Files

| File | Purpose |
|------|---------|
| `app/main.py` | FastAPI app, CORS, rate limiter, security headers, routes |
| `app/auth.py` | Admin API key verification |
| `app/database.py` | SQLite with parameterized queries, explicit column selection |
| `app/schemas.py` | Pydantic models for input validation and safe responses |
| `app/etl.py` | External data validation before DB storage |
| `app/alerts.py` | Alert endpoints with admin auth |
| `app/api/*.py` | Route handlers (all use explicit columns) |

## Run

```bash
PYTHONPATH=. uvicorn Backend.app.main:app --reload --port 8000
```