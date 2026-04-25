"""Pydantic request/response models for the PotholeIQ API."""

from typing import Any, Optional
from pydantic import BaseModel, Field


# ── GeoJSON ────────────────────────────────────────────────────────────────────

class GeoJSONPoint(BaseModel):
    type: str = "Point"
    coordinates: list[float]  # [longitude, latitude]


class PotholeProperties(BaseModel):
    unique_key:             str
    status:                 str
    descriptor:             str
    borough:                str
    street_name:            str
    age_days:               float
    risk_score:             float
    urgency_label:          str
    urgency_tier:           int
    fix_days_estimate:      int
    traffic_volume:         Optional[float] = None
    aadt:                   Optional[float] = None
    nearby_crashes:         int = 0
    pavement_crash_nearby:  int = 0
    prob_low:               Optional[float] = None
    prob_medium:            Optional[float] = None
    prob_high:              Optional[float] = None
    prob_critical:          Optional[float] = None
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


# ── Prediction endpoint ────────────────────────────────────────────────────────

class PotholePredictRequest(BaseModel):
    potholes: list[dict[str, Any]] = Field(
        description="List of pothole dicts matching 311 Service Request schema"
    )


class PotholePrediction(BaseModel):
    unique_key:          Optional[str]   = None
    risk_score:          float
    urgency_label:       str
    urgency_tier:        int
    fix_days_estimate:   int
    prob_low:            float
    prob_medium:         float
    prob_high:           float
    prob_critical:       float


class PotholePredictResponse(BaseModel):
    predictions: list[PotholePrediction]
    model_version: str = "1.0"


# ── Stats endpoint ─────────────────────────────────────────────────────────────

class BoroughStats(BaseModel):
    borough:          str
    total:            int
    open_count:       int
    critical_count:   int
    high_count:       int
    avg_risk_score:   float
    avg_age_days:     float


class StatsResponse(BaseModel):
    total_potholes:   int
    open_potholes:    int
    critical:         int
    high:             int
    medium:           int
    low:              int
    avg_risk_score:   float
    by_borough:       list[BoroughStats]
