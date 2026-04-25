"""
GET /api/potholes          list potholes with filters (including viewport bbox)
GET /api/potholes/{id}     single pothole with ML predictions
"""

from __future__ import annotations

import math
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from ..database import get_conn, POTHOLE_COLS
from ..models.ml_models import predict_for_pothole
from ..schemas import PotholeResponse, PotholeDetailResponse

router = APIRouter(prefix="/api/potholes", tags=["potholes"])


@router.get("", response_model=list[PotholeResponse])
def list_potholes(
    borough:  Optional[str] = Query(None),
    status:   Optional[str] = Query(None),
    limit:    int            = Query(100, ge=1, le=1000),
    offset:   int            = Query(0,   ge=0),
    lat_min:  Optional[float] = Query(None),
    lat_max:  Optional[float] = Query(None),
    lng_min:  Optional[float] = Query(None),
    lng_max:  Optional[float] = Query(None),
):
    conditions, params = ["1=1"], []

    if borough:
        conditions.append("UPPER(borough) = UPPER(?)")
        params.append(borough)
    if status:
        conditions.append("LOWER(status) = LOWER(?)")
        params.append(status)
    if lat_min is not None:
        conditions.append("latitude >= ?");  params.append(lat_min)
    if lat_max is not None:
        conditions.append("latitude <= ?");  params.append(lat_max)
    if lng_min is not None:
        conditions.append("longitude >= ?"); params.append(lng_min)
    if lng_max is not None:
        conditions.append("longitude <= ?"); params.append(lng_max)

    sql = (
        f"SELECT {POTHOLE_COLS} FROM potholes WHERE {' AND '.join(conditions)} "
        f"ORDER BY risk_score DESC LIMIT ? OFFSET ?"
    )
    params += [limit, offset]

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [PotholeResponse(**_map(dict(r))) for r in rows]


@router.get("/{pothole_id}", response_model=PotholeDetailResponse)
def get_pothole_detail(pothole_id: str):
    with get_conn() as conn:
        row = conn.execute(
            f"SELECT {POTHOLE_COLS} FROM potholes WHERE unique_key = ?",
            (pothole_id,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Pothole not found")

    pothole     = dict(row)
    predictions = predict_for_pothole(pothole)
    base        = _map(pothole)

    return PotholeDetailResponse(
        **base,
        accident_risk             = predictions["accident_risk"],
        accident_risk_probability = predictions.get("accident_risk_probability"),
        predicted_repair_days     = predictions.get("predicted_repair_days"),
        repair_eta                = _repair_eta(pothole),
        fix_days_estimate         = pothole.get("fix_days_estimate"),
        prob_low                  = pothole.get("prob_low"),
        prob_medium               = pothole.get("prob_medium"),
        prob_high                 = pothole.get("prob_high"),
        prob_critical             = pothole.get("prob_critical"),
    )


# ── Field mapping ──────────────────────────────────────────────────────────────

def _map(r: dict) -> dict:
    """Map DB columns → PotholeResponse fields, including frontend aliases."""
    age = float(r.get("age_days") or 0)
    return dict(
        unique_key              = r.get("unique_key", ""),
        latitude                = r.get("latitude", 0.0),
        longitude               = r.get("longitude", 0.0),
        borough                 = r.get("borough"),
        city                    = "New York",           # all potholes are NYC
        zip_code                = r.get("zip_code"),
        address                 = _address(r),
        street_name             = r.get("street_name"),
        descriptor              = r.get("descriptor"),
        status                  = r.get("status", ""),
        created_date            = str(r["created_date"]) if r.get("created_date") else None,
        closed_date             = str(r["closed_date"])  if r.get("closed_date")  else None,
        age_days                = age,
        days_open               = int(age),             # frontend alias
        risk_score              = r.get("risk_score"),
        impact_score            = r.get("risk_score"),  # frontend alias
        urgency_label           = r.get("urgency_label"),
        urgency_tier            = r.get("urgency_tier"),
        nearby_crashes          = r.get("nearby_crashes", 0),
        nearby_collision_count  = r.get("nearby_crashes", 0),  # frontend alias
        traffic_volume          = r.get("traffic_volume"),
    )


def _address(r: dict) -> str | None:
    street = r.get("street_name", "")
    borough = r.get("borough", "")
    if street and borough:
        return f"{street}, {borough.title()}, NY"
    if street:
        return street
    return None


def _repair_eta(r: dict) -> str | None:
    fix_days = r.get("fix_days_estimate")
    created  = r.get("created_date")
    if not fix_days or not created:
        return None
    try:
        base = datetime.fromisoformat(str(created).replace(" ", "T"))
        eta  = base + timedelta(days=int(fix_days))
        return eta.strftime("%Y-%m-%d")
    except Exception:
        return None
