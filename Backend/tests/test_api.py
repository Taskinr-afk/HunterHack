"""
API endpoint tests — adapted to Backend/app/ structure and our actual DB schema.
Run: pytest Backend/tests/ -v  (from repo root)
"""

import pytest
from fastapi.testclient import TestClient
from Backend.app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "PotholeIQ API is running"
    assert "version" in data


def test_get_potholes_returns_list():
    response = client.get("/api/potholes?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5


def test_get_potholes_fields_present():
    response = client.get("/api/potholes?limit=1")
    assert response.status_code == 200
    data = response.json()
    if data:
        p = data[0]
        assert "id" in p
        assert "latitude" in p
        assert "longitude" in p
        assert "borough" in p
        assert "status" in p
        assert "days_open" in p
        assert "impact_score" in p


def test_get_potholes_borough_filter():
    response = client.get("/api/potholes?borough=MANHATTAN&limit=5")
    assert response.status_code == 200
    data = response.json()
    for p in data:
        assert p["borough"].upper() == "MANHATTAN"


def test_get_potholes_status_filter():
    response = client.get("/api/potholes?status=Open&limit=5")
    assert response.status_code == 200
    data = response.json()
    for p in data:
        assert p["status"] == "Open"


def test_get_pothole_detail():
    # get an ID first
    ids = client.get("/api/potholes?limit=1").json()
    if not ids:
        pytest.skip("No potholes in DB")
    pothole_id = ids[0]["id"]

    response = client.get(f"/api/potholes/{pothole_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == pothole_id
    assert "accident_risk" in data
    assert data["accident_risk"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert "accident_risk_probability" in data
    assert "predicted_repair_days" in data
    assert "nearby_collision_count" in data


def test_get_pothole_not_found():
    response = client.get("/api/potholes/DOES-NOT-EXIST-99999")
    assert response.status_code == 404


def test_geojson_endpoint():
    response = client.get("/potholes/geojson?limit=5")
    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "FeatureCollection"
    assert "features" in data
    assert "meta" in data
    if data["features"]:
        f = data["features"][0]
        assert f["type"] == "Feature"
        assert f["geometry"]["type"] == "Point"
        assert len(f["geometry"]["coordinates"]) == 2
        assert "risk_score" in f["properties"]
        assert "urgency_label" in f["properties"]


def test_stats_summary():
    response = client.get("/api/stats/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_open" in data
    assert "total_closed" in data
    assert "avg_days_open" in data
    assert "by_borough" in data
    assert isinstance(data["by_borough"], dict)
    for borough, stats in data["by_borough"].items():
        assert "open_count" in stats
        assert "closed_count" in stats
        assert "avg_days_open" in stats
        assert "total_collisions" in stats


def test_stats_timeline():
    response = client.get("/api/stats/timeline")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        w = data[0]
        assert "week" in w
        assert "opened" in w
        assert "closed" in w


def test_stats_endpoint():
    response = client.get("/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_potholes" in data
    assert "open_potholes" in data
    assert "by_borough" in data


def test_alert_history():
    response = client.get("/api/alerts/history?limit=10")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_alert_send_unauthorized():
    response = client.post(
        "/api/alerts/send",
        json={"pothole_id": "12345"},
        headers={"x-api-key": "wrong-key"},
    )
    assert response.status_code == 401


def test_alert_send_missing_key():
    response = client.post("/api/alerts/send", json={"pothole_id": "12345"})
    assert response.status_code == 422


def test_docs_available():
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_has_all_routes():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    required = [
        "/api/potholes",
        "/api/stats/summary",
        "/api/stats/timeline",
        "/api/predictions/{pothole_id}",
        "/api/alerts/send",
        "/api/alerts/history",
        "/potholes/geojson",
        "/stats",
    ]
    for route in required:
        assert route in paths, f"Missing route: {route}"
