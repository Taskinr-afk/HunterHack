"""
Feature engineering and label generation for pothole risk scoring.

Labels are derived from domain logic (age × traffic × severity × crashes) since
NYC Open Data doesn't include accident causation ground truth.
XGBoost learns to approximate this from raw observable features.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timezone

FEATURE_COLS = [
    "age_days",
    "latitude",
    "longitude",
    "borough_code",
    "traffic_volume",       # real vehicle counts from Automated Traffic dataset
    "is_highway",
    "descriptor_severity",
    "month_opened",
    "nearby_crashes",       # collision count within 200 m (NYPD crash data)
    "pavement_crash_nearby", # 1 if pavement-specific crash within 500 m
]

BOROUGH_TRAFFIC = {
    "MANHATTAN":    5,
    "BROOKLYN":     4,
    "QUEENS":       3,
    "BRONX":        2,
    "STATEN ISLAND": 1,
}

# Borough-level volume fallback (avg daily vehicles, rough estimate)
BOROUGH_VOL_FALLBACK = {
    "MANHATTAN":    8_000,
    "BROOKLYN":     5_500,
    "QUEENS":       4_500,
    "BRONX":        3_500,
    "STATEN ISLAND": 2_000,
}

DESCRIPTOR_SEVERITY = {
    "pothole - highway":           1.0,
    "pothole-highway":             1.0,
    "cave-in":                     0.95,
    "cave in":                     0.95,
    "highway pothole":             1.0,
    "pothole":                     0.70,
    "pothole - residential street": 0.55,
    "pothole - street":            0.60,
    "pothole - tunnel":            0.85,
}

URGENCY_LABELS   = ["Low", "Medium", "High", "Critical"]
FIX_DAYS_BY_TIER = {0: 30, 1: 14, 2: 7, 3: 3}

# 95th-percentile daily volume cap for normalisation (calibrated from traffic dataset)
_TRAFFIC_VOL_P95 = 15_000.0


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    df  = df.copy()

    # age
    created = (
        df["created_date"].dt.tz_localize("UTC", ambiguous="NaT", nonexistent="NaT")
        if df["created_date"].dt.tz is None
        else df["created_date"].dt.tz_convert("UTC")
    )
    df["age_days"] = (now - created).dt.total_seconds() / 86400
    df["age_days"] = df["age_days"].clip(lower=0).fillna(30)

    # borough encoding
    df["borough_code"] = (
        df["borough"]
        .map({b: i for i, b in enumerate(BOROUGH_TRAFFIC)})
        .fillna(len(BOROUGH_TRAFFIC))
        .astype(int)
    )

    # traffic_volume: use real data if present, else borough fallback
    if "traffic_volume" not in df.columns:
        df["traffic_volume"] = df["borough"].map(BOROUGH_VOL_FALLBACK).fillna(3_000)
    else:
        fallback = df["borough"].map(BOROUGH_VOL_FALLBACK).fillna(3_000)
        df["traffic_volume"] = df["traffic_volume"].fillna(fallback)

    # highway flag
    df["is_highway"] = (
        df["location_type"].str.lower()
        .str.contains("highway|expressway|bridge|tunnel", na=False)
        .astype(int)
    )

    # descriptor severity
    df["descriptor_severity"] = (
        df["descriptor"].str.lower()
        .map(DESCRIPTOR_SEVERITY)
        .fillna(0.5)
    )

    # seasonality
    df["month_opened"] = df["created_date"].dt.month.fillna(1).astype(int)

    # collision features — default 0 when enriched data isn't available
    for col in ("nearby_crashes", "pavement_crash_nearby"):
        if col not in df.columns:
            df[col] = 0
        df[col] = df[col].fillna(0).astype(int)

    return df


def compute_risk_labels(df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """
    Generate risk_score (0–100) and urgency_tier (0–3) labels for training.

    Formula weights:
      age          40 pts  (180-day saturation)
      traffic      25 pts  (real vehicle counts, 95th-pct normalised)
      severity     15 pts  (descriptor type)
      highway       8 pts  (bonus)
      crashes      12 pts  (nearby crash count, 10-crash saturation)
    """
    rng = np.random.default_rng(seed)

    age_score      = np.minimum(df["age_days"] / 180, 1.0) * 40
    traffic_norm   = np.minimum(df["traffic_volume"] / _TRAFFIC_VOL_P95, 1.0)
    traffic_score  = traffic_norm * 25
    severity_score = df["descriptor_severity"] * 15
    highway_bonus  = df["is_highway"] * 8
    crash_score    = np.minimum(df["nearby_crashes"] / 10, 1.0) * 12

    raw   = age_score + traffic_score + severity_score + highway_bonus + crash_score
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
