"""
Fetch pothole complaint data from NYC Open Data (311 Service Requests).
Dataset: https://data.cityofnewyork.us/resource/erm2-nwe9.json
"""

import requests
import pandas as pd
from pathlib import Path

NYC_311_URL = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
CACHE_PATH = Path(__file__).parent / "models" / "pothole_cache.parquet"

FIELDS = (
    "unique_key,created_date,closed_date,status,"
    "complaint_type,descriptor,borough,"
    "latitude,longitude,location_type"
)


def fetch_potholes(limit: int = 10_000, use_cache: bool = True) -> pd.DataFrame:
    if use_cache and CACHE_PATH.exists():
        return pd.read_parquet(CACHE_PATH)

    params = {
        "$limit": limit,
        "$select": FIELDS,
        "$where": "upper(descriptor) LIKE '%POTHOLE%'",
        "$order": "created_date DESC",
        "$$app_token": "",  # optional: add Socrata app token for higher rate limits
    }

    resp = requests.get(NYC_311_URL, params=params, timeout=30)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())

    if df.empty:
        raise ValueError("NYC Open Data returned no results — check API availability")

    df = _clean(df)
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(CACHE_PATH, index=False)
    return df


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["closed_date"] = pd.to_datetime(df["closed_date"], errors="coerce")
    df["latitude"] = pd.to_numeric(df.get("latitude"), errors="coerce")
    df["longitude"] = pd.to_numeric(df.get("longitude"), errors="coerce")

    # drop rows missing core location or date
    df = df.dropna(subset=["created_date", "latitude", "longitude"])
    df = df[df["latitude"].between(40.4, 40.95)]
    df = df[df["longitude"].between(-74.3, -73.6)]

    df["borough"] = df.get("borough", pd.Series("UNKNOWN", index=df.index)).str.upper().fillna("UNKNOWN")
    df["descriptor"] = df.get("descriptor", pd.Series("", index=df.index)).str.strip().fillna("")
    df["status"] = df.get("status", pd.Series("Open", index=df.index)).fillna("Open")
    df["location_type"] = df.get("location_type", pd.Series("", index=df.index)).fillna("")

    return df.reset_index(drop=True)
