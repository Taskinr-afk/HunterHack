"""
Seed realistic pothole data across all 5 NYC boroughs.
Uses the same heuristic formula as features.py so all fields show real values.

Run: python -m Backend.app.seed_reports
"""

import os
import sys
import random
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from Backend.app.database import init_db, upsert_potholes, insert_report

BOROUGHS = ["MANHATTAN", "BROOKLYN", "QUEENS", "BRONX", "STATEN ISLAND"]

BOROUGH_BOUNDS = {
    "MANHATTAN":     ((40.700, 40.880), (-74.020, -73.910)),
    "BROOKLYN":      ((40.570, 40.740), (-74.040, -73.830)),
    "QUEENS":        ((40.540, 40.800), (-73.960, -73.700)),
    "BRONX":         ((40.785, 40.920), (-73.930, -73.760)),
    "STATEN ISLAND": ((40.490, 40.650), (-74.250, -74.080)),
}

BOROUGH_TRAFFIC = {
    "MANHATTAN": (8_000, 22_000),
    "BROOKLYN":  (4_000, 14_000),
    "QUEENS":    (3_500, 12_000),
    "BRONX":     (3_000, 10_000),
    "STATEN ISLAND": (1_500, 6_000),
}

BOROUGH_CRASHES = {
    "MANHATTAN": (40, 300),
    "BROOKLYN":  (20, 200),
    "QUEENS":    (15, 180),
    "BRONX":     (10, 150),
    "STATEN ISLAND": (5, 80),
}

STREET_NAMES = {
    "MANHATTAN": ["Broadway", "5th Avenue", "Madison Avenue", "Park Avenue",
                  "Amsterdam Avenue", "1st Avenue", "Houston Street", "Canal Street",
                  "Lexington Avenue", "2nd Avenue", "West 125th Street"],
    "BROOKLYN":  ["Flatbush Avenue", "Atlantic Avenue", "4th Avenue", "Court Street",
                  "Ocean Parkway", "Kings Highway", "Fulton Street", "Nostrand Avenue",
                  "Eastern Parkway", "Bedford Avenue"],
    "QUEENS":    ["Queens Boulevard", "Northern Boulevard", "Roosevelt Avenue",
                  "Woodhaven Boulevard", "Jamaica Avenue", "Astoria Boulevard",
                  "31st Avenue", "Steinway Street", "Hillside Avenue"],
    "BRONX":     ["Grand Concourse", "Fordham Road", "Pelham Parkway",
                  "Boston Road", "Webster Avenue", "Jerome Avenue",
                  "Southern Boulevard", "Tremont Avenue", "White Plains Road"],
    "STATEN ISLAND": ["Victory Boulevard", "Hylan Boulevard", "Richmond Road",
                       "Forest Avenue", "Stapleton Road", "Bay Street",
                       "Arthur Kill Road", "Clove Road", "Richmond Terrace"],
}

DESCRIPTORS = [
    "Large pothole in the right lane",
    "Deep pothole near crosswalk",
    "Multiple potholes in a cluster",
    "Pothole causing tire damage",
    "Pothole filled with standing water",
    "Pothole near bus stop",
    "Cave-in forming around pothole",
    "Pothole on highway on-ramp",
    "Pothole at intersection",
    "Recurring pothole, previously patched",
    "Pothole - Highway",
    "Pothole - Residential Street",
]

DESCRIPTOR_SEVERITY = {
    "Pothole - Highway": 1.0,
    "Pothole on highway on-ramp": 0.95,
    "Cave-in forming around pothole": 0.90,
    "Deep pothole near crosswalk": 0.80,
    "Large pothole in the right lane": 0.75,
    "Pothole at intersection": 0.70,
    "Multiple potholes in a cluster": 0.65,
    "Pothole causing tire damage": 0.65,
    "Pothole near bus stop": 0.60,
    "Pothole - Residential Street": 0.55,
    "Recurring pothole, previously patched": 0.55,
    "Pothole filled with standing water": 0.50,
}

URGENCY_LABELS = ["Low", "Medium", "High", "Critical"]
FIX_DAYS = {0: 30, 1: 14, 2: 7, 3: 3}

rng = np.random.default_rng(42)


def _heuristic_score(age_days, traffic_vol, crashes, descriptor, is_highway=0):
    age_score     = min(age_days / 180, 1.0) * 40
    traffic_score = min(traffic_vol / 15_000, 1.0) * 15
    crash_score   = min(crashes / 10, 1.0) * 12
    sev           = DESCRIPTOR_SEVERITY.get(descriptor, 0.6)
    sev_score     = sev * 15
    hw_bonus      = is_highway * 8
    noise         = float(rng.normal(0, 2.5))
    return float(np.clip(age_score + traffic_score + crash_score + sev_score + hw_bonus + noise, 0, 100))


def _urgency_tier(score):
    if score >= 75: return 3
    if score >= 50: return 2
    if score >= 25: return 1
    return 0


def _proba(tier):
    bases = [[0.70, 0.20, 0.07, 0.03],
             [0.20, 0.55, 0.18, 0.07],
             [0.05, 0.18, 0.55, 0.22],
             [0.02, 0.08, 0.25, 0.65]]
    p = bases[tier]
    noise = rng.dirichlet([1] * 4) * 0.05
    out = np.array(p) + noise
    out = out / out.sum()
    return [round(float(x), 3) for x in out]


def seed_reports(n_per_borough: int = 20) -> int:
    init_db()
    rows = []
    now = datetime.now(timezone.utc)

    for borough in BOROUGHS:
        (lat_lo, lat_hi), (lon_lo, lon_hi) = BOROUGH_BOUNDS[borough]
        tv_lo, tv_hi = BOROUGH_TRAFFIC[borough]
        cr_lo, cr_hi = BOROUGH_CRASHES[borough]

        for i in range(n_per_borough):
            lat        = round(random.uniform(lat_lo, lat_hi), 6)
            lon        = round(random.uniform(lon_lo, lon_hi), 6)
            street     = random.choice(STREET_NAMES[borough])
            descriptor = random.choice(DESCRIPTORS)
            age_days   = random.randint(1, 365)
            traffic    = random.randint(tv_lo, tv_hi)
            crashes    = random.randint(cr_lo, cr_hi)
            is_hw      = 1 if "highway" in descriptor.lower() or "Highway" in descriptor else 0
            created    = now - timedelta(days=age_days)
            unique_key = f"NYC-{borough[:3]}-{i:04d}-{abs(hash(street+descriptor+borough)) % 99999:05d}"

            risk  = _heuristic_score(age_days, traffic, crashes, descriptor, is_hw)
            tier  = _urgency_tier(risk)
            probs = _proba(tier)

            rows.append({
                "unique_key":           unique_key,
                "latitude":             lat,
                "longitude":            lon,
                "borough":              borough,
                "street_name":          street,
                "descriptor":           descriptor,
                "status":               "Open",
                "created_date":         created.isoformat(),
                "closed_date":          None,
                "age_days":             float(age_days),
                "traffic_volume":       float(traffic),
                "aadt":                 float(traffic * 365),
                "nearby_crashes":       crashes,
                "pavement_crash_nearby": 1 if crashes > 50 else 0,
                "risk_score":           round(risk, 1),
                "urgency_tier":         tier,
                "urgency_label":        URGENCY_LABELS[tier],
                "fix_days_estimate":    FIX_DAYS[tier],
                "prob_low":             probs[0],
                "prob_medium":          probs[1],
                "prob_high":            probs[2],
                "prob_critical":        probs[3],
            })

            insert_report(
                latitude=lat, longitude=lon, borough=borough,
                street_name=street, descriptor=descriptor,
                reporter_name="Anonymous", reporter_email="",
                image_url="", pothole_key=unique_key,
            )

    df = pd.DataFrame(rows)
    n = upsert_potholes(df)
    print(f"Seeded {n} potholes across {len(BOROUGHS)} boroughs")
    print(f"  risk range:   {df['risk_score'].min():.1f} – {df['risk_score'].max():.1f}")
    print(f"  urgency dist: {df['urgency_label'].value_counts().to_dict()}")
    print(f"  traffic range:{int(df['traffic_volume'].min())} – {int(df['traffic_volume'].max())} veh/day")
    return n


if __name__ == "__main__":
    seed_reports()
