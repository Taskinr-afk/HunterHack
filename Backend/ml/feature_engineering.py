"""
Feature engineering for PotholeIQ ML models.

Reads from the canonical SQLite DB (unique_key, age_days, risk_score,
nearby_crashes, etc.) and produces a feature DataFrame for training.
"""

import pandas as pd
import numpy as np
from pathlib import Path

from app.database import get_conn

FEATURE_COLS = [
    "age_days", "borough_encoded", "traffic_volume",
    "nearby_crashes", "latitude", "longitude",
    "month", "day_of_week",
]

BOROUGH_MAP = {
    "MANHATTAN": 25000, "BROOKLYN": 15000, "QUEENS": 18000,
    "BRONX": 12000, "STATEN ISLAND": 8000, "UNSPECIFIED": 10000,
}

BOROUGH_ENCODE = {
    "MANHATTAN": 0, "BROOKLYN": 1, "QUEENS": 2,
    "BRONX": 3, "STATEN ISLAND": 4, "UNSPECIFIED": 5,
}

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"


def build_features() -> pd.DataFrame:
    """Build ML features from the canonical potholes DB.

    Returns a DataFrame with one row per pothole and columns for features,
    plus target columns: has_nearby_accident, days_to_close, risk_score.
    """
    with get_conn() as conn:
        df = pd.read_sql("SELECT * FROM potholes", conn)

    # Borough encoding
    df["borough_encoded"] = df["borough"].map(BOROUGH_ENCODE).fillna(-1).astype(int)

    # Traffic volume: use stored value or borough proxy
    df["traffic_volume"] = df["traffic_volume"].fillna(
        df["borough"].map(BOROUGH_MAP)
    )

    # Date features
    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["month"] = df["created_date"].dt.month.fillna(0).astype(int)
    df["day_of_week"] = df["created_date"].dt.dayofweek.fillna(0).astype(int)

    # Target: has_nearby_accident (binary: nearby_crashes > 0)
    df["has_nearby_accident"] = (df["nearby_crashes"] > 0).astype(int)

    # Target: days_to_close (only for Closed potholes)
    df["closed_date_dt"] = pd.to_datetime(df["closed_date"], errors="coerce")
    closed_mask = (df["status"] == "Closed") & df["closed_date_dt"].notna()
    df["days_to_close"] = np.nan
    df.loc[closed_mask, "days_to_close"] = (
        df.loc[closed_mask, "closed_date_dt"] - df.loc[closed_mask, "created_date"]
    ).dt.days

    # Ensure feature columns exist
    for col in FEATURE_COLS:
        if col not in df.columns:
            df[col] = 0

    # Save to CSV
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "features.csv"
    df.to_csv(output_path, index=False)
    print(f"Built features for {len(df)} potholes -> {output_path}")
    print(f"  has_nearby_accident distribution: {df['has_nearby_accident'].value_counts().to_dict()}")
    print(f"  days_to_close available: {df['days_to_close'].notna().sum()} / {len(df)}")

    return df


if __name__ == "__main__":
    build_features()