"""
GET /api/potholes          list potholes with filters
GET /api/potholes/{id}     single pothole with ML predictions
"""

from fastapi import APIRouter, HTTPException, Query
from ..database import get_conn
from ..models.ml_models import predict_for_pothole
from ..schemas import PotholeResponse, PotholeDetailResponse

router = APIRouter(prefix="/api/potholes", tags=["potholes"])


@router.get("", response_model=list[PotholeResponse])
def list_potholes(
    borough: str | None = Query(None),
    status:  str | None = Query(None),
    limit:   int        = Query(100, ge=1, le=1000),
    offset:  int        = Query(0,   ge=0),
):
    conditions = ["1=1"]
    params: list = []

    if borough:
        conditions.append("UPPER(borough) = UPPER(?)")
        params.append(borough)
    if status:
        conditions.append("LOWER(status) = LOWER(?)")
        params.append(status)

    sql = (
        f"SELECT * FROM potholes WHERE {' AND '.join(conditions)} "
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
            "SELECT * FROM potholes WHERE unique_key = ?", (pothole_id,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Pothole not found")

    pothole     = dict(row)
    predictions = predict_for_pothole(pothole)

    base = _map(pothole)
    return PotholeDetailResponse(
        **base,
        accident_risk              = predictions["accident_risk"],
        accident_risk_probability  = predictions.get("accident_risk_probability"),
        predicted_repair_days     = predictions.get("predicted_repair_days"),
        fix_days_estimate         = pothole.get("fix_days_estimate"),
        prob_low                  = pothole.get("prob_low"),
        prob_medium               = pothole.get("prob_medium"),
        prob_high                 = pothole.get("prob_high"),
        prob_critical             = pothole.get("prob_critical"),
    )


def _map(r: dict) -> dict:
    """Map DB row dict to PotholeResponse field names."""
    return dict(
        unique_key     = r.get("unique_key", ""),
        latitude       = r.get("latitude", 0.0),
        longitude      = r.get("longitude", 0.0),
        borough        = r.get("borough"),
        street_name    = r.get("street_name"),
        descriptor     = r.get("descriptor"),
        status         = r.get("status", ""),
        created_date   = str(r.get("created_date", "")) if r.get("created_date") else None,
        closed_date    = str(r.get("closed_date", "")) if r.get("closed_date") else None,
        age_days       = float(r.get("age_days") or 0),
        risk_score     = r.get("risk_score"),
        urgency_label  = r.get("urgency_label"),
        urgency_tier   = r.get("urgency_tier"),
        nearby_crashes = r.get("nearby_crashes", 0),
        traffic_volume = r.get("traffic_volume"),
    )