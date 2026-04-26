"""
API endpoint tests — canonical schema (unique_key, age_days, risk_score, nearby_crashes).
Run:  PYTHONPATH=MainProject pytest MainProject/Backend/tests/test_api.py -v
"""

import pytest
from fastapi.testclient import TestClient

from Backend.app.main import app
from Backend.app.database import init_db, get_conn

client = TestClient(app)


# ── Seed test data once ──────────────────────────────────────────────────────

@pytest.fixture(scope="module", autouse=True)
def _seed():
    init_db()
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM potholes").fetchone()[0]
        if count == 0:
            samples = [
                (
                    "TEST-001", 40.7580, -73.9855, "MANHATTAN", "BROADWAY",
                    "Pothole", "Open", "2026-01-15", None, "Street",
                    100, 72.5, "High", 2, 21,
                    25000.0, 80000.0, 5, 1,
                    0.15, 0.25, 0.45, 0.15,
                ),
                (
                    "TEST-002", 40.6782, -73.9442, "BROOKLYN", "ATLANTIC AVE",
                    "Pothole", "Open", "2026-02-10", None, "Street",
                    45, 35.0, "Medium", 1, 14,
                    18000.0, 55000.0, 2, 0,
                    0.30, 0.40, 0.20, 0.10,
                ),
                (
                    "TEST-003", 40.7282, -73.7949, "QUEENS", "QUEENS BLVD",
                    "Pothole - Highway", "Closed", "2025-11-01", "2026-01-15", "Highway",
                    75, 88.0, "Critical", 3, 7,
                    30000.0, 120000.0, 12, 1,
                    0.05, 0.10, 0.30, 0.55,
                ),
                (
                    "TEST-004", 40.8448, -73.8648, "BRONX", "GRAND CONCOURSE",
                    "Pothole", "Open", "2026-03-01", None, "Street",
                    55, 60.0, "High", 2, 18,
                    22000.0, 65000.0, 4, 0,
                    0.20, 0.30, 0.35, 0.15,
                ),
                (
                    "TEST-005", 40.5795, -74.1502, "STATEN ISLAND", "VICTORY BLVD",
                    "Pothole", "Open", "2026-04-01", None, "Street",
                    24, 20.0, "Low", 0, 30,
                    5000.0, 20000.0, 0, 0,
                    0.50, 0.30, 0.15, 0.05,
                ),
            ]
            cols = (
                "unique_key, latitude, longitude, borough, street_name, "
                "descriptor, status, created_date, closed_date, location_type, "
                "age_days, risk_score, urgency_label, urgency_tier, fix_days_estimate, "
                "traffic_volume, aadt, nearby_crashes, pavement_crash_nearby, "
                "prob_low, prob_medium, prob_high, prob_critical"
            )
            placeholders = ", ".join(["?"] * 23)
            for s in samples:
                conn.execute(
                    f"INSERT INTO potholes ({cols}) VALUES ({placeholders})", s
                )
            conn.commit()


# ── Health ───────────────────────────────────────────────────────────────────

def test_root_endpoint():
    r = client.get("/")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "PotholeIQ API is running"
    assert "version" in data


def test_docs_available():
    assert client.get("/docs").status_code == 200


# ── GET /api/potholes ──────────────────────────────────────────────────────

def test_list_potholes_returns_list():
    r = client.get("/api/potholes?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) <= 5


def test_list_potholes_canonical_fields():
    r = client.get("/api/potholes?limit=1")
    assert r.status_code == 200
    data = r.json()
    if not data:
        pytest.skip("No potholes in DB")
    p = data[0]
    # canonical schema fields
    assert "unique_key" in p
    assert "age_days" in p
    assert "risk_score" in p
    assert "nearby_crashes" in p
    assert "urgency_label" in p
    # old schema fields must NOT appear
    assert "id" not in p or p.get("id") == p.get("unique_key")
    assert "days_open" not in p
    assert "impact_score" not in p
    assert "nearby_collision_count" not in p


def test_list_potholes_borough_filter():
    # SQL uses UPPER(borough) = UPPER(?) so any case works
    r = client.get("/api/potholes?borough=manhattan&limit=5")
    assert r.status_code == 200
    for p in r.json():
        assert p["borough"].upper() == "MANHATTAN"


def test_list_potholes_status_filter():
    # SQL uses LOWER(status) = LOWER(?) so any case works
    r = client.get("/api/potholes?status=open&limit=5")
    assert r.status_code == 200
    for p in r.json():
        assert p["status"].lower() == "open"


def test_list_potholes_risk_ordering():
    r = client.get("/api/potholes?limit=10")
    data = r.json()
    if len(data) < 2:
        pytest.skip("Need >=2 potholes to test ordering")
    scores = [p["risk_score"] for p in data if p.get("risk_score") is not None]
    assert scores == sorted(scores, reverse=True)


# ── GET /api/potholes/{unique_key} ─────────────────────────────────────────

def test_get_pothole_detail():
    ids = client.get("/api/potholes?limit=1").json()
    if not ids:
        pytest.skip("No potholes in DB")
    key = ids[0]["unique_key"]

    r = client.get(f"/api/potholes/{key}")
    assert r.status_code == 200
    p = r.json()
    assert p["unique_key"] == key
    # canonical detail fields
    assert "accident_risk" in p
    assert p["accident_risk"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert "accident_risk_probability" in p
    assert "predicted_repair_days" in p
    assert "nearby_crashes" in p
    assert "prob_low" in p
    assert "prob_medium" in p
    assert "prob_high" in p
    assert "prob_critical" in p


def test_get_pothole_not_found():
    assert client.get("/api/potholes/DOES-NOT-EXIST-99999").status_code == 404


# ── GET /potholes/geojson ──────────────────────────────────────────────────

def test_geojson_endpoint():
    r = client.get("/potholes/geojson?limit=5")
    assert r.status_code == 200
    data = r.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert "meta" in data
    if data["features"]:
        f = data["features"][0]
        assert f["type"] == "Feature"
        assert f["geometry"]["type"] == "Point"
        assert len(f["geometry"]["coordinates"]) == 2
        props = f["properties"]
        assert "risk_score" in props
        assert "urgency_label" in props
        assert "unique_key" in props
        assert "age_days" in props


def test_geojson_borough_filter():
    r = client.get("/potholes/geojson?borough=MANHATTAN&limit=5")
    assert r.status_code == 200
    for f in r.json()["features"]:
        assert f["properties"]["borough"].upper() == "MANHATTAN"


def test_geojson_urgency_filter():
    r = client.get("/potholes/geojson?urgency=Critical&limit=5")
    assert r.status_code == 200
    for f in r.json()["features"]:
        assert f["properties"]["urgency_label"].lower() == "critical"


def test_geojson_min_risk_filter():
    r = client.get("/potholes/geojson?min_risk=50&limit=5")
    assert r.status_code == 200
    for f in r.json()["features"]:
        assert f["properties"]["risk_score"] >= 50


# ── GET /potholes/{unique_key} (main.py route) ────────────────────────────

def test_get_pothole_by_key():
    ids = client.get("/api/potholes?limit=1").json()
    if not ids:
        pytest.skip("No potholes in DB")
    key = ids[0]["unique_key"]

    r = client.get(f"/potholes/{key}")
    assert r.status_code == 200
    assert r.json()["unique_key"] == key


def test_get_pothole_by_key_not_found():
    assert client.get("/potholes/DOES-NOT-EXIST-99999").status_code == 404


# ── GET /stats ──────────────────────────────────────────────────────────────

def test_stats_endpoint():
    r = client.get("/stats")
    assert r.status_code == 200
    data = r.json()
    assert "total_potholes" in data
    assert "open_potholes" in data
    assert "by_borough" in data
    assert isinstance(data["by_borough"], list)
    if data["by_borough"]:
        b = data["by_borough"][0]
        assert "borough" in b
        assert "open_count" in b
        assert "avg_risk_score" in b
        assert "avg_age_days" in b


# ── GET /api/stats/summary ──────────────────────────────────────────────────

def test_stats_summary():
    r = client.get("/api/stats/summary")
    assert r.status_code == 200
    data = r.json()
    assert "total_open" in data
    assert "total_closed" in data
    assert "avg_age_days" in data
    assert "by_borough" in data
    assert isinstance(data["by_borough"], dict)
    for name, stats in data["by_borough"].items():
        assert "open_count" in stats
        assert "closed_count" in stats
        assert "avg_age_days" in stats
        assert "total_collisions" in stats


# ── GET /api/stats/timeline ─────────────────────────────────────────────────

def test_stats_timeline():
    r = client.get("/api/stats/timeline")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    if data:
        w = data[0]
        assert "week" in w
        assert "opened" in w
        assert "closed" in w


# ── GET /api/predictions/{pothole_id} ───────────────────────────────────────

def test_predictions_endpoint():
    ids = client.get("/api/potholes?limit=1").json()
    if not ids:
        pytest.skip("No potholes in DB")
    key = ids[0]["unique_key"]

    r = client.get(f"/api/predictions/{key}")
    assert r.status_code == 200
    pred = r.json()
    assert "accident_risk" in pred
    assert pred["accident_risk"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


def test_predictions_not_found():
    assert client.get("/api/predictions/DOES-NOT-EXIST").status_code == 404


# ── POST /predict ───────────────────────────────────────────────────────────

def test_predict_endpoint():
    payload = {
        "potholes": [{
            "unique_key": "PREDICT-001",
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
        }]
    }
    r = client.post("/predict", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "predictions" in data
    pred = data["predictions"][0]
    assert "risk_score" in pred
    assert "urgency_label" in pred
    assert "urgency_tier" in pred
    assert "fix_days_estimate" in pred


def test_predict_empty_list():
    r = client.post("/predict", json={"potholes": []})
    assert r.status_code == 422


# ── Alerts ───────────────────────────────────────────────────────────────────

def test_alerts_history():
    r = client.get("/api/alerts/history?limit=10")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_alerts_send_requires_api_key():
    r = client.post(
        "/api/alerts/send",
        json={"pothole_id": "TEST-001", "message": "test"},
    )
    # Missing x-api-key header → 422 (FastAPI validation)
    assert r.status_code == 422


def test_alerts_send_wrong_key():
    r = client.post(
        "/api/alerts/send",
        json={"pothole_id": "TEST-001"},
        headers={"x-api-key": "wrong-key"},
    )
    assert r.status_code == 401


def test_alerts_send_valid_key():
    import os
    key = os.environ.get("ADMIN_API_KEY", "change-me")
    r = client.post(
        "/api/alerts/send",
        json={"pothole_id": "TEST-001"},
        headers={"x-api-key": key},
    )
    # Either 200 (success) or 404 (pothole not in DB) is acceptable
    assert r.status_code in (200, 404)
    if r.status_code == 200:
        data = r.json()
        assert "status" in data
        assert data["status"] in ("sent", "logged")


# ── /alerts/* (alerts.py routes) ────────────────────────────────────────────

def test_alerts_history_legacy():
    r = client.get("/alerts/history?limit=5")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_alerts_scan_requires_admin():
    r = client.post("/alerts/scan")
    # Requires query param `secret` for admin — should fail auth
    assert r.status_code in (401, 403, 422)


# ── POTHOLE_COLS security ──────────────────────────────────────────────────

def test_pothole_response_no_internal_fields():
    """Ensure API responses never leak internal DB columns like zip_code."""
    r = client.get("/api/potholes?limit=1")
    if not r.json():
        pytest.skip("No potholes in DB")
    p = r.json()[0]
    # These should NOT appear in API responses
    assert "zip_code" not in p
    assert "location_type" not in p
    assert "pavement_crash_nearby" not in p
    # These MUST appear (canonical schema)
    assert "unique_key" in p
    assert "age_days" in p
    assert "risk_score" in p


# ── OpenAPI routes check ───────────────────────────────────────────────────

def test_openapi_has_all_routes():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    expected = [
        "/",
        "/potholes/geojson",
        "/potholes/{unique_key}",
        "/predict",
        "/stats",
        "/admin/refresh",
        "/api/potholes",
        "/api/potholes/{pothole_id}",
        "/api/stats/summary",
        "/api/stats/timeline",
        "/api/predictions/{pothole_id}",
        "/api/alerts/send",
        "/api/alerts/history",
        "/alerts/send",
        "/alerts/scan",
        "/alerts/history",
    ]
    for route in expected:
        assert route in paths, f"Missing route: {route}"