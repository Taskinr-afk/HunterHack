"""
PotholeIQ FastAPI backend — merged from Kevin's ML routes + Backend security layer.

Endpoints:
  GET  /                         health check
  GET  /potholes/geojson         GeoJSON FeatureCollection (map layer)
  GET  /potholes/{unique_key}    single pothole detail
  POST /predict                  score arbitrary pothole data via ML model
  GET  /stats                    summary stats by borough
  POST /admin/refresh            re-fetch NYC data + re-score (admin only)
  POST /alerts/send              send DOT alert (admin key required)
  GET  /alerts/history           alert history

Run:
  uvicorn Backend.app.main:app --reload --port 8000
"""

from __future__ import annotations

import os
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware

from .alerts import router as alerts_router
from .api.potholes import router as potholes_router
from .api.stats import router as stats_router
from .api.predictions import router as predictions_router
from .api.alerts_api import router as alerts_api_router
from .database import init_db, upsert_potholes, query_potholes, get_stats
from .schemas import (
    GeoJSONFeatureCollection,
    GeoJSONFeature,
    GeoJSONPoint,
    PotholeProperties,
    PotholePredictRequest,
    PotholePredictResponse,
    PotholePrediction,
    StatsResponse,
    BoroughStats,
)

load_dotenv()

# ── Rate limiter ───────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="PotholeIQ API",
    description="NYC Pothole Risk Intelligence — ML-powered scoring and alerts",
    version="1.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ───────────────────────────────────────────────────────────────────────
_cors_origins = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Security headers ───────────────────────────────────────────────────────────
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline' https://api.mapbox.com; "
            "img-src 'self' data: https://*.tile.openstreetmap.org https://api.mapbox.com; "
            "connect-src 'self' https://api.mapbox.com https://data.cityofnewyork.us"
        )
        return response

app.add_middleware(SecurityHeadersMiddleware)

if os.getenv("ENVIRONMENT") == "production":
    app.add_middleware(HTTPSRedirectMiddleware)

# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(alerts_router)       # /alerts/*
app.include_router(potholes_router)     # /api/potholes
app.include_router(stats_router)        # /api/stats/*
app.include_router(predictions_router)  # /api/predictions/*
app.include_router(alerts_api_router)   # /api/alerts/*


@app.on_event("startup")
def startup():
    init_db()


# ── Lazy model loader ──────────────────────────────────────────────────────────
_model = None

def _get_model():
    global _model
    if _model is None:
        from Backend.cortex.model import PotholeRiskModel
        _model = PotholeRiskModel.load()
    return _model


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {"status": "PotholeIQ API is running", "version": "1.0.0"}


# ── GeoJSON map layer ──────────────────────────────────────────────────────────

@app.get("/potholes/geojson", response_model=GeoJSONFeatureCollection)
@limiter.limit("60/minute")
def potholes_geojson(
    request: Request,
    status:   Optional[str] = Query(None,  description="Open | Closed"),
    borough:  Optional[str] = Query(None,  description="MANHATTAN, BROOKLYN …"),
    min_risk: float          = Query(0.0,  description="Minimum risk score 0–100"),
    urgency:  Optional[str] = Query(None,  description="Low | Medium | High | Critical"),
    limit:    int            = Query(5_000, le=10_000),
):
    rows = query_potholes(
        status=status, borough=borough,
        min_risk=min_risk, urgency=urgency, limit=limit,
    )
    if not rows:
        return GeoJSONFeatureCollection(features=[], meta={"count": 0})

    features = []
    for r in rows:
        if r.get("latitude") is None or r.get("longitude") is None:
            continue
        features.append(
            GeoJSONFeature(
                geometry=GeoJSONPoint(coordinates=[r["longitude"], r["latitude"]]),
                properties=PotholeProperties(
                    unique_key            = str(r.get("unique_key", "")),
                    status                = r.get("status", ""),
                    descriptor            = r.get("descriptor", ""),
                    borough               = r.get("borough", ""),
                    street_name           = r.get("street_name", ""),
                    age_days              = float(r.get("age_days") or 0),
                    risk_score            = float(r.get("risk_score") or 0),
                    urgency_label         = r.get("urgency_label", ""),
                    urgency_tier          = int(r.get("urgency_tier") or 0),
                    fix_days_estimate     = int(r.get("fix_days_estimate") or 30),
                    traffic_volume        = r.get("traffic_volume"),
                    aadt                  = r.get("aadt"),
                    nearby_crashes        = int(r.get("nearby_crashes") or 0),
                    pavement_crash_nearby = int(r.get("pavement_crash_nearby") or 0),
                    prob_low              = r.get("prob_low"),
                    prob_medium           = r.get("prob_medium"),
                    prob_high             = r.get("prob_high"),
                    prob_critical         = r.get("prob_critical"),
                    created_date          = r.get("created_date"),
                    closed_date           = r.get("closed_date"),
                ),
            )
        )

    return GeoJSONFeatureCollection(features=features, meta={"count": len(features)})


# ── Single pothole ─────────────────────────────────────────────────────────────

@app.get("/potholes/{unique_key}")
@limiter.limit("120/minute")
def get_pothole(unique_key: str, request: Request):
    from .database import get_conn
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM potholes WHERE unique_key = ?", (unique_key,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Pothole not found")
    return dict(row)


# ── ML predict ────────────────────────────────────────────────────────────────

@app.post("/predict", response_model=PotholePredictResponse)
@limiter.limit("30/minute")
def predict(req: PotholePredictRequest, request: Request):
    if not req.potholes:
        raise HTTPException(status_code=422, detail="potholes list is empty")

    try:
        model = _get_model()
        df    = pd.DataFrame(req.potholes)

        if "created_date" not in df.columns:
            from datetime import datetime, timezone
            df["created_date"] = datetime.now(timezone.utc).isoformat()
        df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")

        for col in ("descriptor", "borough", "location_type", "street_name"):
            if col not in df.columns:
                df[col] = ""

        _CENTROIDS = {
            "MANHATTAN": (40.7831, -73.9712), "BROOKLYN": (40.6782, -73.9442),
            "QUEENS":    (40.7282, -73.7949), "BRONX":    (40.8448, -73.8648),
            "STATEN ISLAND": (40.5795, -74.1502),
        }
        if "latitude" not in df.columns or df["latitude"].isna().all():
            df["latitude"]  = df["borough"].str.upper().map(
                lambda b: _CENTROIDS.get(b, (40.7128, -74.0060))[0]
            )
            df["longitude"] = df["borough"].str.upper().map(
                lambda b: _CENTROIDS.get(b, (40.7128, -74.0060))[1]
            )

        result = model.predict(df)
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Model not trained — run python -m Backend.cortex.train first",
        )

    predictions = [
        PotholePrediction(
            unique_key        = str(row.get("unique_key", i)),
            risk_score        = float(row["risk_score"]),
            urgency_label     = row["urgency_label"],
            urgency_tier      = int(row["urgency_tier"]),
            fix_days_estimate = int(row["fix_days_estimate"]),
            prob_low          = float(row.get("prob_low",      0)),
            prob_medium       = float(row.get("prob_medium",   0)),
            prob_high         = float(row.get("prob_high",     0)),
            prob_critical     = float(row.get("prob_critical", 0)),
        )
        for i, row in result.iterrows()
    ]
    return PotholePredictResponse(predictions=predictions)


# ── Stats ──────────────────────────────────────────────────────────────────────

@app.get("/stats")
@limiter.limit("60/minute")
def stats(request: Request):
    s = get_stats()
    return StatsResponse(
        total_potholes = s.get("total", 0),
        open_potholes  = s.get("open_count", 0),
        critical       = s.get("critical", 0),
        high           = s.get("high", 0),
        medium         = s.get("medium", 0),
        low            = s.get("low", 0),
        avg_risk_score = s.get("avg_risk_score", 0.0),
        by_borough     = [BoroughStats(**b) for b in s.get("by_borough", [])],
    )


# ── Admin: refresh ─────────────────────────────────────────────────────────────

@app.post("/admin/refresh")
def admin_refresh(secret: str = Query(...)):
    if secret != os.environ.get("ADMIN_SECRET", "potholeiq-dev"):
        raise HTTPException(status_code=403, detail="Invalid secret")

    from Backend.cortex.data import fetch_all
    from Backend.cortex.model import score_potholes

    df     = fetch_all(use_cache=False)
    scored = score_potholes(df)
    n      = upsert_potholes(scored)

    global _model
    _model = None

    return {"status": "ok", "rows_upserted": n}
