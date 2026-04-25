# backend/app/schemas.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional
import re

# --- Input validation (what frontend sends TO us) ---

class PotholeFilterParams(BaseModel):
    borough: Optional[str] = Field(None, pattern="^(Manhattan|Brooklyn|Queens|Bronx|Staten Island)$")
    status: Optional[str] = Field(None, pattern="^(open|closed)$")
    limit: int = Field(100, ge=1, le=1000)   # Must be between 1 and 1000
    offset: int = Field(0, ge=0)

class AlertRequest(BaseModel):
    pothole_id: str = Field(..., min_length=1, max_length=50)
    message: Optional[str] = Field(None, max_length=2000)

    @field_validator("pothole_id")
    def validate_pothole_id(cls, v):
        # Only letters, numbers, hyphens allowed — blocks SQL injection
        if not re.match(r"^[a-zA-Z0-9\-]+$", v):
            raise ValueError("Invalid pothole ID format")
        return v

# --- Output models (what we send BACK to frontend) ---
# Only expose safe fields — no personal info from 311 data

class PotholeResponse(BaseModel):
    id: str
    latitude: float
    longitude: float
    borough: str
    status: str
    created_date: str
    closed_date: Optional[str]
    days_open: int
    descriptor: str

class PotholeDetailResponse(PotholeResponse):
    impact_score: Optional[float]
    accident_risk: Optional[str]          # LOW / MEDIUM / HIGH
    predicted_repair_days: Optional[int]
    nearby_collision_count: int
    traffic_volume: Optional[int]