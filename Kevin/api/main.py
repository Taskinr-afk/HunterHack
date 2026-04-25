"""
PotholeIQ FastAPI backend.

Endpoints:
  GET  /                         health check
  GET  /potholes/geojson         GeoJSON FeatureCollection (map layer)
  GET  /potholes/{unique_key}    single pothole detail
  POST /predict                  score arbitrary pothole data via ML model
  GET  /stats                    summary stats by borough
  POST /admin/refresh            re-fetch NYC data + re-score (admin only)

Run:
  uvicorn kevin.api.main:app --reload --port 8000
"""

from __future__ import annotations

import os
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware

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

# lazy imports so the API can start even before models are trained
_model = None

def _get_model():
    global _model
    if _model is None:
        from kevin.cortex.model import PotholeRiskModel
        _model = PotholeRiskModel.load()
    return _model


# ── App setup ──────────────────────────────────────────────────────────────────

app = FastAPI(
    title="PotholeIQ API",
    description="NYC Pothole Risk Intelligence — ML-powered scoring and alerts",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # frontend dev server
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/")
def health():
    return {"status": "ok", "service": "PotholeIQ API v1.0"}


# ── GeoJSON map layer ──────────────────────────────────────────────────────────

@app.get("/potholes/geojson", response_model=GeoJSONFeatureCollection)
def potholes_geojson(
    status:   Optional[str]   = Query(None,  description="Open | Closed"),
    borough:  Optional[str]   = Query(None,  description="MANHATTAN, BROOKLYN …"),
    min_risk: float            = Query(0.0,  description="Minimum risk score 0–100"),
    urgency:  Optional[str]   = Query(None,  description="Low | Medium | High | Critical"),
    limit:    int              = Query(5_000, le=10_000),
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
                geometry=GeoJSONPoint(
                    coordinates=[r["longitude"], r["latitude"]]
                ),
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

    return GeoJSONFeatureCollection(
        features=features,
        meta={"count": len(features)},
    )


# ── Single pothole ─────────────────────────────────────────────────────────────

@app.get("/potholes/{unique_key}")
def get_pothole(unique_key: str):
    rows = query_potholes(limit=1)
    # targeted lookup
    from .database import get_conn
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM potholes WHERE unique_key = ?", (unique_key,)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Pothole not found")
    return dict(row)


# ── ML predict endpoint ────────────────────────────────────────────────────────

@app.post("/predict", response_model=PotholePredictResponse)
def predict(req: PotholePredictRequest):
    if not req.potholes:
        raise HTTPException(status_code=422, detail="potholes list is empty")

    try:
        model  = _get_model()
        df     = pd.DataFrame(req.potholes)

        # created_date is required for age_days; default to now if missing
        if "created_date" not in df.columns:
            from datetime import datetime, timezone
            df["created_date"] = datetime.now(timezone.utc).isoformat()
        df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")

        for col in ("descriptor", "borough", "location_type", "street_name"):
            if col not in df.columns:
                df[col] = ""
        # lat/lon required by features; use borough centroid fallback
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
            detail="Model not trained yet — run python -m kevin.cortex.train first",
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

@app.get("/stats", response_model=StatsResponse)
def stats():
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


# ── Admin: refresh data ────────────────────────────────────────────────────────

@app.post("/admin/refresh")
def admin_refresh(secret: str = Query(...)):
    """Re-fetch NYC datasets, re-score all potholes, reload DB."""
    if secret != os.environ.get("ADMIN_SECRET", "potholeiq-dev"):
        raise HTTPException(status_code=403, detail="Invalid secret")

    from kevin.cortex.data import fetch_all
    from kevin.cortex.model import score_potholes

    df      = fetch_all(use_cache=False)
    scored  = score_potholes(df)
    n       = upsert_potholes(scored)

    # invalidate cached model so next predict reloads from disk
    global _model
    _model = None

    return {"status": "ok", "rows_upserted": n}
