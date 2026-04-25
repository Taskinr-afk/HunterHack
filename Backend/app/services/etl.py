"""
ETL pipeline for PotholeIQ.

Fetches pothole and collision data from NYC Open Data, cleans it,
counts nearby crashes, and loads into the canonical potholes.db using
the security dev's database module (Backend.app.database).
"""

import pandas as pd
import numpy as np
import httpx
import os
from datetime import datetime, timezone

from app.database import get_conn, upsert_potholes

NYC_311_API = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
NYC_COLLISIONS_API = "https://data.cityofnewyork.us/resource/h9gi-nx95.json"

APP_TOKEN = os.getenv("NYC_OPENDATA_APP_TOKEN", "")


def fetch_potholes(limit: int = 50000, year_from: str = "2024-01-01") -> pd.DataFrame:
    """Fetch pothole complaints from NYC 311."""
    params = {
        "$where": f"descriptor='Pothole' AND created_date > '{year_from}T00:00:00'",
        "$limit": limit,
        "$order": "created_date DESC",
    }
    if APP_TOKEN:
        params["$$app_token"] = APP_TOKEN

    response = httpx.get(NYC_311_API, params=params, timeout=60)
    response.raise_for_status()
    data = response.json()

    df = pd.DataFrame(data)
    print(f"Fetched {len(df)} pothole records")
    return df


def fetch_collisions(limit: int = 50000, year_from: str = "2024-01-01") -> pd.DataFrame:
    """Fetch motor vehicle collision data."""
    params = {
        "$where": f"latitude IS NOT NULL AND crash_date > '{year_from}'",
        "$limit": limit,
        "$order": "crash_date DESC",
    }
    if APP_TOKEN:
        params["$$app_token"] = APP_TOKEN

    response = httpx.get(NYC_COLLISIONS_API, params=params, timeout=60)
    response.raise_for_status()
    data = response.json()

    df = pd.DataFrame(data)
    print(f"Fetched {len(df)} collision records")
    return df


def clean_potholes(df: pd.DataFrame) -> pd.DataFrame:
    """Clean pothole data and map to the canonical schema."""
    df = df.dropna(subset=["latitude", "longitude"]).copy()

    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    df = df[
        (df["latitude"].between(40.4, 41.0)) &
        (df["longitude"].between(-74.3, -73.7))
    ]

    # Uppercase borough, capitalize status to match canonical schema
    df["borough"] = df.get("borough", pd.Series(dtype=str)).fillna("UNKNOWN").str.upper()
    df["status"] = df["status"].str.strip().str.capitalize()  # "Open" / "Closed"

    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["closed_date"] = pd.to_datetime(df.get("closed_date"), errors="coerce")

    now = pd.Timestamp.now(tz="UTC")
    df["age_days"] = (df["closed_date"].fillna(now) - df["created_date"]).dt.days
    df["age_days"] = df["age_days"].fillna(0).astype(float)

    # Map to canonical column names
    df["unique_key"] = df.get("unique_key", pd.Series(dtype=str)).astype(str)
    df["street_name"] = df.get("street_name", df.get("intersection_street_1", pd.Series(dtype=str))).fillna("")
    df["descriptor"] = df.get("descriptor", pd.Series(dtype=str)).fillna("")

    # Defaults for ML-scored columns (filled later by cortex or impact.py)
    df["traffic_volume"] = None
    df["aadt"] = None
    df["nearby_crashes"] = 0
    df["pavement_crash_nearby"] = 0
    df["risk_score"] = None
    df["urgency_tier"] = None
    df["urgency_label"] = None
    df["fix_days_estimate"] = None
    df["prob_low"] = None
    df["prob_medium"] = None
    df["prob_high"] = None
    df["prob_critical"] = None

    return df


def clean_collisions(df: pd.DataFrame) -> pd.DataFrame:
    """Clean collision data for geospatial counting."""
    df = df.dropna(subset=["latitude", "longitude"]).copy()

    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    df = df[
        (df["latitude"].between(40.4, 41.0)) &
        (df["longitude"].between(-74.3, -73.7))
    ]

    return df


def count_nearby_crashes(potholes_df: pd.DataFrame, collisions_df: pd.DataFrame, radius_km: float = 0.200) -> pd.Series:
    """Count collisions within radius_km of each pothole using vectorized haversine.

    Default radius: 200m to match the cortex/data.py approach.
    """
    if collisions_df.empty:
        return pd.Series(0, index=potholes_df.index)

    p_lats = np.radians(potholes_df["latitude"].values)
    p_lons = np.radians(potholes_df["longitude"].values)
    c_lats = np.radians(collisions_df["latitude"].values)
    c_lons = np.radians(collisions_df["longitude"].values)

    chunk_size = 5000
    counts = np.zeros(len(potholes_df), dtype=int)

    for start in range(0, len(collisions_df), chunk_size):
        end = min(start + chunk_size, len(collisions_df))
        c_lat_chunk = c_lats[start:end]
        c_lon_chunk = c_lons[start:end]

        dlat = c_lat_chunk[np.newaxis, :] - p_lats[:, np.newaxis]
        dlon = c_lon_chunk[np.newaxis, :] - p_lons[:, np.newaxis]
        a = np.sin(dlat / 2) ** 2 + np.cos(p_lats[:, np.newaxis]) * np.cos(c_lat_chunk[np.newaxis, :]) * np.sin(dlon / 2) ** 2
        dist = 6371 * 2 * np.arcsin(np.sqrt(a))

        counts += (dist <= radius_km).sum(axis=1)

    return pd.Series(counts, index=potholes_df.index)


def run_etl():
    """Full ETL pipeline: fetch, clean, count crashes, load into DB."""
    print("Starting ETL pipeline...")

    print("\n1. Fetching pothole data...")
    potholes_df = fetch_potholes(limit=50000, year_from="2024-01-01")

    print("\n2. Fetching collision data...")
    collisions_df = fetch_collisions(limit=50000, year_from="2024-01-01")

    print("\n3. Cleaning pothole data...")
    potholes_df = clean_potholes(potholes_df)

    print("\n4. Cleaning collision data...")
    collisions_df = clean_collisions(collisions_df)

    print("\n5. Counting nearby crashes for each pothole...")
    potholes_df["nearby_crashes"] = count_nearby_crashes(potholes_df, collisions_df, radius_km=0.200)
    print(f"   Potholes with crashes nearby: {(potholes_df['nearby_crashes'] > 0).sum()}")

    print("\n6. Loading potholes into database...")
    n = upsert_potholes(potholes_df)
    print(f"   Upserted {n} potholes")

    print("\nETL pipeline complete!")


if __name__ == "__main__":
    run_etl()