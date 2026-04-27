"""Pydantic request/response models for the PotholeIQ API."""

import re
from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator


# ── GeoJSON ──────────────────────────────────────────────────────────────────────

class GeoJSONPoint(BaseModel):
    type: str = "Point"
    coordinates: list[float]  # [longitude, latitude]


class PotholeProperties(BaseModel):
    unique_key:             str
    status:                 str
    descriptor:             Optional[str] = None
    borough:                Optional[str] = None
    street_name:            Optional[str] = None
    age_days:               float
    risk_score:             float
    urgency_label:          Optional[str] = None
    urgency_tier:           int
    fix_days_estimate:      int
    traffic_volume:         Optional[float] = None
    aadt:                   Optional[float] = None
    nearby_crashes:         int = 0
    pavement_crash_nearby:  int = 0
    prob_low:               Optional[float] = None
    prob_medium:            Optional[float] = None
    prob_high:               Optional[float] = None
    prob_critical:          Optional[float] = None
    accident_risk_probability: Optional[float] = None
    accident_probability:    Optional[float] = None
    created_date:           Optional[str]   = None
    closed_date:            Optional[str]   = None


class GeoJSONFeature(BaseModel):
    type:       str = "Feature"
    geometry:   GeoJSONPoint
    properties: PotholeProperties


class GeoJSONFeatureCollection(BaseModel):
    type:     str = "FeatureCollection"
    features: list[GeoJSONFeature]
    meta:     dict[str, Any] = {}


# ── Input validation (frontend → API) ────────────────────────────────────────────

class PotholeFilterParams(BaseModel):
    borough: Optional[str] = Field(None, pattern="^(Manhattan|Brooklyn|Queens|Bronx|Staten Island)$")
    status:  Optional[str] = Field(None, pattern="^(open|closed)$")
    limit:   int            = Field(100, ge=1, le=1000)
    offset:  int            = Field(0, ge=0)


class AlertRequest(BaseModel):
    pothole_id: str            = Field(..., min_length=1, max_length=50)
    message:    Optional[str] = Field(None, max_length=2000)

    @field_validator("pothole_id")
    @classmethod
    def validate_pothole_id(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9\-]+$", v):
            raise ValueError("Invalid pothole ID format")
        return v


class PotholePredictRequest(BaseModel):
    potholes: list[dict[str, Any]] = Field(
        description="List of pothole dicts matching 311 Service Request schema"
    )


# ── Output models (API → frontend) ──────────────────────────────────────────────
# Only safe fields — no personal info like complainant names or phone numbers.

class PotholeResponse(BaseModel):
    unique_key:             str
    latitude:               float
    longitude:              float
    borough:                Optional[str]   = None
    street_name:            Optional[str]   = None
    descriptor:             Optional[str]   = None
    status:                 str
    created_date:           Optional[str]   = None
    closed_date:            Optional[str]   = None
    age_days:               float
    risk_score:             Optional[float] = None
    urgency_label:          Optional[str]   = None
    urgency_tier:           Optional[int]   = None
    nearby_crashes:         int             = 0
    traffic_volume:         Optional[float] = None


class PotholeDetailResponse(PotholeResponse):
    accident_risk:              Optional[str]   = None
    accident_risk_probability:  Optional[float] = None
    accident_probability:       Optional[float] = None
    predicted_repair_days:      Optional[int]   = None
    repair_eta:                 Optional[str]   = None   # ISO date of estimated fix
    fix_days_estimate:          Optional[int]   = None
    prob_low:                   Optional[float] = None
    prob_medium:                Optional[float] = None
    prob_high:                  Optional[float] = None
    prob_critical:              Optional[float] = None


class PotholePrediction(BaseModel):
    unique_key:          Optional[str] = None
    risk_score:          float
    urgency_label:       str
    urgency_tier:        int
    fix_days_estimate:   int
    prob_low:            float
    prob_medium:         float
    prob_high:           float
    prob_critical:       float
    accident_probability: Optional[float] = None


class PotholePredictResponse(BaseModel):
    predictions:   list[PotholePrediction]
    model_version: str = "1.0"


# ── Stats ────────────────────────────────────────────────────────────────────────

class BoroughStats(BaseModel):
    borough:        str
    total:          int
    open_count:     int
    critical_count: int
    high_count:     int
    avg_risk_score: float
    avg_age_days:   float


class StatsResponse(BaseModel):
    total_potholes: int
    open_potholes:  int
    critical:       int
    high:           int
    medium:         int
    low:            int
    avg_risk_score: float
    by_borough:     list[BoroughStats]


class StatsBoroughEntry(BaseModel):
    open_count:       int
    closed_count:     int
    avg_age_days:     float
    total_collisions: int


class StatsSummary(BaseModel):
    total_open:    int
    total_closed:  int
    avg_days_open: float
    by_borough:    dict[str, StatsBoroughEntry]


class TimelinePoint(BaseModel):
    week:   str
    opened: int
    closed: int


# ── Alerts ───────────────────────────────────────────────────────────────────────

class AlertResponse(BaseModel):
    id:         int
    pothole_id: str
    sent_date:  str
    status:     str
    message:    str


# ── Citizen Reports ───────────────────────────────────────────────────────────

class ReportCreateRequest(BaseModel):
    latitude:       float           = Field(..., ge=40.4, le=41.0, description="Latitude within NYC bounds")
    longitude:      float           = Field(..., ge=-74.3, le=-73.7, description="Longitude within NYC bounds")
    borough:        Optional[str]   = Field(None, max_length=50)
    street_name:    Optional[str]   = Field(None, max_length=200)
    descriptor:     Optional[str]   = Field(None, max_length=1000)
    reporter_name:  Optional[str]   = Field(None, max_length=100)
    reporter_email: Optional[str]   = Field(None, max_length=200)
    image_url:      Optional[str]   = Field(None, max_length=500)

    @field_validator("borough")
    @classmethod
    def validate_borough(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        normalized = v.strip().upper()
        valid = {"MANHATTAN", "BROOKLYN", "QUEENS", "BRONX", "STATEN ISLAND"}
        if normalized not in valid:
            raise ValueError(f"Invalid borough: {v}. Must be one of: {', '.join(sorted(valid))}")
        return normalized


class ReportResponse(BaseModel):
    id:             int
    latitude:       float
    longitude:      float
    borough:        Optional[str]    = None
    street_name:    Optional[str]   = None
    descriptor:     Optional[str]   = None
    reporter_name:  Optional[str]   = None
    reporter_email: Optional[str]   = None
    image_url:      Optional[str]   = None
    status:         str             = "unverified"
    pothole_key:    Optional[str]   = None
    created_at:     str
    verified_at:    Optional[str]   = None


class ReportListResponse(BaseModel):
    reports: list[ReportResponse]
    count:   int
