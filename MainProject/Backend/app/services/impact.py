"""
Impact scoring for PotholeIQ.

Computes a composite risk_score (0–100) and urgency_tier/label for
every open pothole, using crash proximity, age, and traffic volume.

The canonical schema stores risk_score, urgency_tier, urgency_label,
prob_*, and fix_days_estimate directly on the potholes table. This
module updates those columns in place.
"""

from app.database import get_conn

# Borough-level traffic proxy (vehicles/day) — used when traffic_volume
# is missing from the pothole record.
BOROUGH_TRAFFIC = {
    "MANHATTAN": 25000,
    "BROOKLYN": 15000,
    "QUEENS": 18000,
    "BRONX": 12000,
    "STATEN ISLAND": 8000,
}


def compute_impact_scores():
    """Compute and persist risk_score, urgency, and probability columns.

    Composite formula (matches cortex/features.py logic):
      raw_risk = 0.40 * crash_factor
               + 0.30 * age_factor
               + 0.30 * traffic_factor

    Each factor is normalised to 0–1 before weighting:
      crash_factor   = min(nearby_crashes / 15, 1.0)
      age_factor     = min(age_days / 90, 1.0)
      traffic_factor = min(traffic_volume / 25000, 1.0)

    risk_score is then scaled to 0–100 and urgency_tier assigned:
      0 = Low, 1 = Medium, 2 = High, 3 = Critical
    """
    with get_conn() as conn:
        potholes = conn.execute("""
            SELECT unique_key, age_days, borough, nearby_crashes,
                   traffic_volume, risk_score
            FROM potholes WHERE status = 'Open'
        """).fetchall()

    print(f"Computing impact scores for {len(potholes)} open potholes...")

    with get_conn() as conn:
        for pothole in potholes:
            p = dict(pothole)
            age_days = p.get("age_days") or 0
            borough = (p.get("borough") or "MANHATTAN").upper()
            nearby_crashes = p.get("nearby_crashes") or 0
            traffic_volume = p.get("traffic_volume")

            # Use stored traffic volume if available, else borough proxy
            traffic = traffic_volume if traffic_volume else BOROUGH_TRAFFIC.get(borough, 15000)

            # Normalised factors (each 0–1)
            crash_factor = min(nearby_crashes / 15.0, 1.0)
            age_factor = min(float(age_days) / 90.0, 1.0)
            traffic_factor = min(float(traffic) / 25000.0, 1.0)

            # Weighted composite → 0–100
            raw_risk = 0.40 * crash_factor + 0.30 * age_factor + 0.30 * traffic_factor
            risk_score = round(raw_risk * 100, 1)

            # Urgency tier and label
            if risk_score > 75:
                urgency_tier, urgency_label = 3, "Critical"
            elif risk_score > 50:
                urgency_tier, urgency_label = 2, "High"
            elif risk_score > 25:
                urgency_tier, urgency_label = 1, "Medium"
            else:
                urgency_tier, urgency_label = 0, "Low"

            # Probability breakdowns (simple ratio from risk_score)
            prob_low = round(max(0, 1 - raw_risk), 3)
            prob_medium = round(min(raw_risk * 0.5, 0.5), 3)
            prob_high = round(min(raw_risk * 0.3, 0.4), 3)
            prob_critical = round(min(raw_risk * 0.2, 0.3), 3)

            # Estimated fix days (borough-based baseline + age modifier)
            base_days = 7 if borough == "MANHATTAN" else 14
            fix_days = max(1, base_days + int(age_days // 10))

            conn.execute(
                """UPDATE potholes SET
                    risk_score = ?,
                    urgency_tier = ?,
                    urgency_label = ?,
                    fix_days_estimate = ?,
                    prob_low = ?,
                    prob_medium = ?,
                    prob_high = ?,
                    prob_critical = ?,
                    traffic_volume = ?
                WHERE unique_key = ?""",
                (
                    risk_score, urgency_tier, urgency_label, fix_days,
                    prob_low, prob_medium, prob_high, prob_critical,
                    int(traffic) if traffic_volume is None else traffic_volume,
                    p["unique_key"],
                ),
            )

    print(f"Impact scores updated for {len(potholes)} potholes")


if __name__ == "__main__":
    compute_impact_scores()