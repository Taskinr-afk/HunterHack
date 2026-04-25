"""
GET /api/potholes          list potholes with filters
GET /api/potholes/{id}     single pothole with ML predictions
"""

from fastapi import APIRouter, HTTPException, Query
from ..database import get_conn, POTHOLE_COLS
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
        f"SELECT {POTHOLE_COLS} FROM potholes WHERE {' AND '.join(conditions)} "
        f"ORDER BY risk_score DESC LIMIT ? OFFSET ?"
    )
    params += [limit, offset]

    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()

    return [_to_pothole_response(dict(r)) for r in rows]


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

    return PotholeDetailResponse(
        **_to_pothole_response(pothole),
        nearby_collision_count = pothole.get("nearby_crashes", 0),
        traffic_volume         = int(pothole.get("traffic_volume") or 0) or None,
        accident_risk          = predictions["accident_risk"],
        accident_risk_probability = predictions["accident_risk_probability"],
        predicted_repair_days  = predictions["predicted_repair_days"],
    )


def _to_pothole_response(r: dict) -> dict:
    """Map DB columns → PotholeResponse schema (only safe fields)."""
    return dict(
        id           = r.get("unique_key", ""),
        latitude     = r.get("latitude", 0.0),
        longitude    = r.get("longitude", 0.0),
        borough      = r.get("borough", ""),
        zip_code     = None,
        descriptor   = r.get("descriptor", ""),
        status       = r.get("status", ""),
        created_date = str(r.get("created_date", "")),
        closed_date  = str(r.get("closed_date", "")) if r.get("closed_date") else None,
        days_open    = int(r.get("age_days") or 0),
        impact_score = r.get("risk_score"),
    )