"""
Citizen pothole report endpoints.

POST /api/reports   — submit a new pothole report (public, no auth)
GET  /api/reports   — list unverified reports
"""

from __future__ import annotations

import random
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Query

from ..database import (
    insert_report,
    insert_unverified_pothole,
    get_unverified_reports,
    infer_borough,
)
from ..schemas import ReportCreateRequest, ReportResponse, ReportListResponse
from ..services.report_email import send_report_notification

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.post("", response_model=ReportResponse, status_code=201)
async def create_report(req: ReportCreateRequest):
    borough = req.borough or infer_borough(req.latitude, req.longitude)
    unique_key = f"RPT-{int(time.time())}-{random.randint(1000, 9999)}"

    insert_unverified_pothole(
        unique_key=unique_key,
        latitude=req.latitude,
        longitude=req.longitude,
        borough=borough,
        street_name=req.street_name or "",
        descriptor=req.descriptor or "",
    )

    report_id = insert_report(
        latitude=req.latitude,
        longitude=req.longitude,
        borough=borough,
        street_name=req.street_name or "",
        descriptor=req.descriptor or "",
        reporter_name=req.reporter_name or "",
        reporter_email=req.reporter_email or "",
        image_url=req.image_url or "",
        pothole_key=unique_key,
    )

    send_report_notification({
        "report_id": report_id,
        "pothole_key": unique_key,
        "latitude": req.latitude,
        "longitude": req.longitude,
        "borough": borough,
        "street_name": req.street_name,
        "descriptor": req.descriptor,
        "reporter_name": req.reporter_name,
        "reporter_email": req.reporter_email,
        "image_url": req.image_url,
    })

    return ReportResponse(
        id=report_id,
        latitude=req.latitude,
        longitude=req.longitude,
        borough=borough,
        street_name=req.street_name,
        descriptor=req.descriptor,
        reporter_name=req.reporter_name,
        reporter_email=req.reporter_email,
        image_url=req.image_url,
        status="unverified",
        pothole_key=unique_key,
        created_at=datetime.now(timezone.utc).isoformat(),
        verified_at=None,
    )


@router.get("", response_model=ReportListResponse)
def list_unverified_reports(limit: int = Query(200, ge=1, le=1000)):
    rows = get_unverified_reports(limit=limit)
    reports = [
        ReportResponse(
            id=r["id"],
            latitude=r["latitude"],
            longitude=r["longitude"],
            borough=r["borough"],
            street_name=r["street_name"],
            descriptor=r["descriptor"],
            reporter_name=r["reporter_name"],
            reporter_email=r["reporter_email"],
            image_url=r["image_url"],
            status=r["status"],
            pothole_key=r["pothole_key"],
            created_at=r["created_at"],
            verified_at=r["verified_at"],
        )
        for r in rows
    ]
    return ReportListResponse(reports=reports, count=len(reports))