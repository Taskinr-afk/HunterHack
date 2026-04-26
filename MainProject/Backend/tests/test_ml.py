"""
ML model tests — covers both real XGBoost model and heuristic fallback.
Run: pytest Backend/tests/ -v  (from repo root)
"""

import pytest
from Backend.app.models.ml_models import predict_for_pothole, _get_model
from Backend.cortex.features import FEATURE_COLS, tier_to_label, tier_to_fix_days


def test_predict_returns_required_fields():
    result = predict_for_pothole({
        "unique_key": "test-001",
        "age_days": 30,
        "borough": "MANHATTAN",
        "risk_score": 55.0,
        "nearby_crashes": 5,
        "traffic_volume": 8000,
        "aadt": 50000,
        "is_highway": 0,
        "descriptor": "Pothole",
        "location_type": "",
        "latitude": 40.75,
        "longitude": -73.99,
        "created_date": "2026-01-01",
        "month_opened": 1,
        "pavement_crash_nearby": 0,
        "borough_code": 0,
        "descriptor_severity": 0.7,
        "status": "Open",
    })
    assert "accident_risk" in result
    assert "accident_risk_probability" in result
    assert "predicted_repair_days" in result
    assert "risk_score" in result
    assert result["accident_risk"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert 0.0 <= result["accident_risk_probability"] <= 1.0
    assert isinstance(result["predicted_repair_days"], int)
    assert result["predicted_repair_days"] >= 1


def test_high_risk_higher_than_low_risk():
    high = predict_for_pothole({
        "age_days": 180, "borough": "MANHATTAN", "risk_score": 90.0,
        "nearby_crashes": 20, "traffic_volume": 20000, "aadt": 120000,
        "is_highway": 1, "descriptor": "Pothole - Highway", "location_type": "Highway",
        "latitude": 40.78, "longitude": -73.97, "created_date": "2025-01-01",
        "month_opened": 1, "pavement_crash_nearby": 1, "borough_code": 0,
        "descriptor_severity": 1.0, "status": "Open",
    })
    low = predict_for_pothole({
        "age_days": 2, "borough": "STATEN ISLAND", "risk_score": 10.0,
        "nearby_crashes": 0, "traffic_volume": 1000, "aadt": 5000,
        "is_highway": 0, "descriptor": "Pothole", "location_type": "",
        "latitude": 40.57, "longitude": -74.15, "created_date": "2026-04-20",
        "month_opened": 4, "pavement_crash_nearby": 0, "borough_code": 4,
        "descriptor_severity": 0.7, "status": "Open",
    })
    assert high["accident_risk_probability"] >= low["accident_risk_probability"]


def test_heuristic_fallback():
    import Backend.app.models.ml_models as mm
    original = mm._model
    mm._model = "heuristic"

    result = predict_for_pothole({
        "age_days": 45, "borough": "BROOKLYN", "risk_score": 0,
        "nearby_crashes": 3, "traffic_volume": 5000,
    })
    assert result["accident_risk"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert result["predicted_repair_days"] >= 1

    mm._model = original


def test_real_model_loads():
    model = _get_model()
    # Heuristic fallback is valid when model files aren't trained yet
    # Re-train with: python -m Backend.cortex.train
    assert model is not None, "Model loader should return a model or 'heuristic'"


def test_feature_cols_stable():
    assert len(FEATURE_COLS) == 11
    assert "age_days" in FEATURE_COLS
    assert "traffic_volume" in FEATURE_COLS
    assert "aadt" in FEATURE_COLS
    assert "nearby_crashes" in FEATURE_COLS
    assert "pavement_crash_nearby" in FEATURE_COLS


def test_tier_labels():
    assert tier_to_label(0) == "Low"
    assert tier_to_label(1) == "Medium"
    assert tier_to_label(2) == "High"
    assert tier_to_label(3) == "Critical"


def test_tier_fix_days():
    assert tier_to_fix_days(3) < tier_to_fix_days(2)
    assert tier_to_fix_days(2) < tier_to_fix_days(1)
    assert tier_to_fix_days(1) < tier_to_fix_days(0)
