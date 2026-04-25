"""
POST /api/alerts/send     send DOT alert for a pothole (admin key)
GET  /api/alerts/history  alert history
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from ..auth import verify_admin_key
from ..database import get_conn, insert_alert, get_alert_history
from ..schemas import AlertRequest, AlertResponse
from ..services.alert_service import generate_alert_message, send_alert_email

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.post("/send", response_model=AlertResponse)
async def send_alert(
    alert:      AlertRequest,
    authorized: bool = Depends(verify_admin_key),
):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM potholes WHERE unique_key = ?", (alert.pothole_id,)
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Pothole not found")

    pothole = dict(row)
    message = generate_alert_message(pothole, alert.message)
    sent    = send_alert_email(pothole, message)

    alert_id = insert_alert(
        pothole_id  = alert.pothole_id,
        urgency     = pothole.get("urgency_label", ""),
        risk_score  = pothole.get("risk_score", 0),
        borough     = pothole.get("borough", ""),
        street_name = pothole.get("street_name", ""),
        message     = message,
        delivered   = sent,
    )

    return AlertResponse(
        id         = alert_id,
        pothole_id = alert.pothole_id,
        sent_date  = datetime.now(timezone.utc).isoformat(),
        status     = "sent" if sent else "logged",
        message    = message,
    )


@router.get("/history", response_model=list[AlertResponse])
def alert_history(limit: int = 50):
    rows = get_alert_history(limit=limit)
    return [
        AlertResponse(
            id         = r["id"],
            pothole_id = r["pothole_id"],
            sent_date  = r.get("sent_at", ""),
            status     = "sent" if r.get("delivered") else "logged",
            message    = r.get("message", ""),
        )
        for r in rows
    ]