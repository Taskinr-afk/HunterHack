"""
Alerts endpoint for PotholeIQ API.
- POST /alerts/send: Send an alert about a high-risk pothole
- GET  /alerts/history: Get alert history
"""

from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional
import os
import datetime

router = APIRouter(prefix="/alerts", tags=["alerts"])

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "change-me-in-production")

async def verify_admin_key(x_api_key: str = Header(...)):
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

@router.post("/send")
async def send_alert(pothole_id: str, message: Optional[str] = None, authorized: bool = Depends(verify_admin_key)):
    # For demo: just log the alert
    now = datetime.datetime.now().isoformat()
    print(f"[ALERT] {now} | pothole_id={pothole_id} | message={message}")
    # In production, insert into DB and/or send email
    return {"status": "sent", "pothole_id": pothole_id, "sent_date": now, "message": message or ""}

@router.get("/history")
def get_alert_history():
    # For demo: return empty list
    return []
