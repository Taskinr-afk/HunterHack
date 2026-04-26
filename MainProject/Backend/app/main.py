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
from contextlib import asynccontextmanager
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
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
from .api.reports import router as reports_router
from .database import init_db, upsert_potholes, query_potholes, get_stats, get_conn, POTHOLE_COLS
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

# ── Rate limiter ───────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # Auto-seed if the potholes table is empty
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM potholes").fetchone()[0]
    if count == 0:
        from . import seed
        seed.seed_demo_data()
    yield


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="PotholeIQ API",
    description="NYC Pothole Risk Intelligence — ML-powered scoring and alerts",
    version="1.0.0",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ───────────────────────────────────────────────────────────────────────
_cors_origins = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173").split(",")
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
            "img-src 'self' data: https://*.tile.openstreetmap.org https://api.mapbox.com https://*.cartocdn.com; "
            "font-src 'self' https://api.mapbox.com https://*.cartocdn.com; "
            "connect-src 'self' https://api.mapbox.com https://data.cityofnewyork.us https://*.cartocdn.com"
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
app.include_router(reports_router)     # /api/reports


# ── Lazy model loader ──────────────────────────────────────────────────────────
_model = None


def _load_pothole_risk_model():
    try:
        from Backend.cortex.model import PotholeRiskModel
    except ImportError:
        from cortex.model import PotholeRiskModel

    return PotholeRiskModel


def _load_refresh_pipeline():
    try:
        from Backend.cortex.data import fetch_all
        from Backend.cortex.model import score_potholes
    except ImportError:
        from cortex.data import fetch_all
        from cortex.model import score_potholes

    return fetch_all, score_potholes


def _get_model():
    global _model
    if _model is None:
        try:
            _model = _load_pothole_risk_model().load()
        except Exception:
            _model = "heuristic"
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
                    accident_risk_probability = (
                        round(float(r["prob_high"]) + float(r["prob_critical"]), 3)
                        if r.get("prob_high") is not None and r.get("prob_critical") is not None
                        else None
                    ),
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
    with get_conn() as conn:
        row = conn.execute(
            f"SELECT {POTHOLE_COLS} FROM potholes WHERE unique_key = ?", (unique_key,)
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

    model = _get_model()

    if model == "heuristic":
        predictions = []
        for p in req.potholes:
            days_open    = float(p.get("age_days") or 0)
            risk_score   = float(p.get("risk_score") or 0)
            borough      = (p.get("borough") or "MANHATTAN").upper()
            crashes      = int(p.get("nearby_crashes") or 0)

            if risk_score > 0:
                prob = min(risk_score / 100, 0.99)
            else:
                prob = min(days_open * 0.003 + crashes * 0.02, 0.95)

            if prob > 0.75 or risk_score > 75:
                label, tier = "Critical", 3
            elif prob > 0.50 or risk_score > 50:
                label, tier = "High", 2
            elif prob > 0.25 or risk_score > 25:
                label, tier = "Medium", 1
            else:
                label, tier = "Low", 0

            base_days = 7 if borough == "MANHATTAN" else 14
            fix_days  = max(1, base_days + int(days_open // 10))

            predictions.append(PotholePrediction(
                unique_key        = str(p.get("unique_key", "")),
                risk_score        = round(risk_score, 1),
                urgency_label     = label,
                urgency_tier      = tier,
                fix_days_estimate = fix_days,
                prob_low          = round(max(1 - prob, 0), 3),
                prob_medium       = round(min(prob * 0.5, 0.5), 3),
                prob_high         = round(min(prob * 0.4, 0.4), 3),
                prob_critical     = round(min(prob * 0.3, 0.3), 3),
            ))
        return PotholePredictResponse(predictions=predictions)

    try:
        df = pd.DataFrame(req.potholes)

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
    except Exception:
        # If real model fails, use heuristic predictions
        from .models.ml_models import predict_for_pothole
        predictions = []
        for i, p in enumerate(req.potholes):
            pred = predict_for_pothole(dict(p))
            predictions.append(PotholePrediction(
                unique_key        = str(p.get("unique_key", i)),
                risk_score        = pred.get("risk_score", 50.0),
                urgency_label     = pred.get("accident_risk", "LOW"),
                urgency_tier      = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}.get(pred.get("accident_risk", "LOW"), 0),
                fix_days_estimate = pred.get("predicted_repair_days", 14),
                prob_low          = 0.3,
                prob_medium       = 0.4,
                prob_high         = 0.2,
                prob_critical    = 0.1,
            ))
        return PotholePredictResponse(predictions=predictions)

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

    import requests as _requests

    try:
        from .etl import validate_pothole_data
        fetch_all, score_potholes = _load_refresh_pipeline()

        df     = fetch_all(use_cache=False)
        df     = validate_pothole_data(df)
        scored = score_potholes(df)
        n      = upsert_potholes(scored)

        global _model
        _model = None

        return {"status": "ok", "rows_upserted": n}

    except _requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="NYC Open Data API timed out — try again in a minute")
    except _requests.exceptions.ConnectionError:
        raise HTTPException(status_code=502, detail="Cannot reach NYC Open Data APIs — check your internet connection")
    except _requests.exceptions.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"NYC Open Data API error: {e.response.status_code}")
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="ML model not trained — run python -m Backend.cortex.train first")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Data validation error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refresh failed: {str(e)}")
