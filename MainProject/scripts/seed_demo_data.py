"""
Seed the SQLite DB with synthetic demo data for presentations.
Use this if the live NYC API is unavailable during the demo.
Run: python Backend/scripts/seed_demo_data.py
"""

import os
import sys
import random
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from Backend.app.database import init_db, get_conn

BOROUGHS = ["MANHATTAN", "BROOKLYN", "QUEENS", "BRONX", "STATEN ISLAND"]
DESCRIPTORS = ["Pothole", "Pothole - Highway", "Pothole - Tunnel", "Cave-In"]
URGENCY = ["Low", "Medium", "High", "Critical"]

LAT_RANGES = {
    "MANHATTAN":    (40.700, 40.880),
    "BROOKLYN":     (40.570, 40.740),
    "QUEENS":       (40.540, 40.800),
    "BRONX":        (40.785, 40.920),
    "STATEN ISLAND":(40.490, 40.650),
}
LON_RANGES = {
    "MANHATTAN":    (-74.020, -73.910),
    "BROOKLYN":     (-74.040, -73.830),
    "QUEENS":       (-73.960, -73.700),
    "BRONX":        (-73.930, -73.760),
    "STATEN ISLAND":(-74.250, -74.080),
}
TRAFFIC = {
    "MANHATTAN": 15000, "BROOKLYN": 8000,
    "QUEENS": 6000, "BRONX": 5000, "STATEN ISLAND": 3000,
}


def seed(n: int = 500) -> None:
    init_db()

    with get_conn() as conn:
        conn.execute("DELETE FROM alerts")
        conn.execute("DELETE FROM potholes")

        rows = []
        for i in range(n):
            borough    = random.choice(BOROUGHS)
            lat        = round(random.uniform(*LAT_RANGES[borough]), 6)
            lon        = round(random.uniform(*LON_RANGES[borough]), 6)
            age        = random.randint(1, 120)
            status     = "Open" if random.random() > 0.4 else "Closed"
            created    = datetime.datetime.now() - datetime.timedelta(days=age)
            closed     = None
            if status == "Closed":
                closed = (created + datetime.timedelta(days=random.randint(1, age))).isoformat()

            risk       = round(random.uniform(5, 95), 1)
            tier       = 0 if risk < 25 else (1 if risk < 50 else (2 if risk < 75 else 3))
            label      = URGENCY[tier]
            fix_days   = [30, 14, 7, 3][tier]
            crashes    = random.randint(0, 20)

            rows.append((
                f"DEMO-{i:05d}", str(created), closed, status,
                random.choice(DESCRIPTORS), borough, "DEMO STREET",
                lat, lon, float(age),
                float(TRAFFIC[borough] + random.randint(-2000, 2000)),
                float(TRAFFIC[borough] * 365),
                crashes, 1 if crashes > 5 else 0,
                risk, tier, label, fix_days,
                0.3, 0.4, 0.2, 0.1,
            ))

        conn.executemany("""
            INSERT OR REPLACE INTO potholes (
                unique_key, created_date, closed_date, status, descriptor, borough,
                street_name, latitude, longitude, age_days, traffic_volume, aadt,
                nearby_crashes, pavement_crash_nearby, risk_score, urgency_tier,
                urgency_label, fix_days_estimate, prob_low, prob_medium, prob_high, prob_critical
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, rows)

    print(f"✓ Seeded {n} demo potholes into SQLite")
    print("  Run: PYTHONPATH=. uvicorn Backend.app.main:app --reload --port 8000")


if __name__ == "__main__":
    seed()
