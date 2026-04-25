"""
Feature engineering and label generation for pothole risk scoring.

Labels are derived from domain logic (age × traffic × severity) since
NYC Open Data doesn't include accident causation ground truth.
XGBoost then learns to approximate this from raw observable features,
which lets it generalize to potholes the formula hasn't seen.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timezone

FEATURE_COLS = [
    "age_days",
    "latitude",
    "longitude",
    "borough_code",
    "traffic_weight",
    "is_highway",
    "descriptor_severity",
    "month_opened",
]

BOROUGH_TRAFFIC = {
    "MANHATTAN": 5,
    "BROOKLYN": 4,
    "QUEENS": 3,
    "BRONX": 2,
    "STATEN ISLAND": 1,
}

DESCRIPTOR_SEVERITY = {
    "pothole - highway": 1.0,
    "pothole-highway": 1.0,
    "cave-in": 0.95,
    "cave in": 0.95,
    "highway pothole": 1.0,
    "pothole": 0.70,
    "pothole - residential street": 0.55,
    "pothole - street": 0.60,
}

URGENCY_LABELS = ["Low", "Medium", "High", "Critical"]

# Estimated days to fix by urgency tier (for the backend tooltip)
FIX_DAYS_BY_TIER = {0: 30, 1: 14, 2: 7, 3: 3}


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    df = df.copy()

    created = df["created_date"].dt.tz_localize("UTC", ambiguous="NaT", nonexistent="NaT") \
        if df["created_date"].dt.tz is None else df["created_date"].dt.tz_convert("UTC")

    df["age_days"] = (now - created).dt.total_seconds() / 86400
    df["age_days"] = df["age_days"].clip(lower=0).fillna(30)

    df["borough_code"] = df["borough"].map(
        {b: i for i, b in enumerate(BOROUGH_TRAFFIC)}
    ).fillna(len(BOROUGH_TRAFFIC)).astype(int)

    df["traffic_weight"] = df["borough"].map(BOROUGH_TRAFFIC).fillna(2.5)

    df["is_highway"] = df["location_type"].str.lower().str.contains(
        "highway|expressway|bridge|tunnel", na=False
    ).astype(int)

    desc_lower = df["descriptor"].str.lower()
    df["descriptor_severity"] = desc_lower.map(DESCRIPTOR_SEVERITY).fillna(0.5)

    df["month_opened"] = df["created_date"].dt.month.fillna(1).astype(int)

    return df


def compute_risk_labels(df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """
    Generate risk_score (0–100) and urgency_tier (0–3) labels for training.

    Formula encodes three real-world factors:
      - Age:         older open potholes → higher danger
      - Traffic:     busier borough → more cars at risk
      - Severity:    highway/cave-in → higher impact
    Small Gaussian noise ensures the model can't just memorize the formula.
    """
    rng = np.random.default_rng(seed)

    age_score = np.minimum(df["age_days"] / 180, 1.0) * 40
    traffic_score = (df["traffic_weight"] / 5) * 30
    severity_score = df["descriptor_severity"] * 20
    highway_bonus = df["is_highway"] * 10

    raw = age_score + traffic_score + severity_score + highway_bonus
    noise = rng.normal(0, 2.5, size=len(df))

    df = df.copy()
    df["risk_score"] = np.clip(raw + noise, 0, 100).round(1)
    df["urgency_tier"] = pd.cut(
        df["risk_score"],
        bins=[-1, 25, 50, 75, 101],
        labels=[0, 1, 2, 3],
    ).astype(int)

    return df


def tier_to_label(tier: int) -> str:
    return URGENCY_LABELS[int(tier)]


def tier_to_fix_days(tier: int) -> int:
    return FIX_DAYS_BY_TIER[int(tier)]
