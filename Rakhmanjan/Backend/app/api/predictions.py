"""
GET /api/predictions/{pothole_id}   ML risk + repair prediction for one pothole
"""

from fastapi import APIRouter, HTTPException
from ..database import get_conn, POTHOLE_COLS
from ..models.ml_models import predict_for_pothole

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.get("/{pothole_id}")
def get_prediction(pothole_id: str):
    with get_conn() as conn:
        row = conn.execute(
            f"SELECT {POTHOLE_COLS} FROM potholes WHERE unique_key = ?",
            (pothole_id,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Pothole not found")

    return predict_for_pothole(dict(row))