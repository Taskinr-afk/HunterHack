"""
NYC Open Data pipeline for PotholeIQ.

Datasets used:
  311 Service Requests   erm2-nwe9  pothole reports, age, status, lat/lon
  Automated Traffic      7ym2-wayt  real vehicle counts per street segment
  Motor Vehicle Crashes  h9gi-nx95  collision counts + pavement-specific crashes
"""

from __future__ import annotations

import re
import numpy as np
import pandas as pd
import requests
from pathlib import Path
from sklearn.neighbors import BallTree

MODEL_DIR = Path(__file__).parent / "models"

# ── API endpoints ──────────────────────────────────────────────────────────────
NYC_311_URL      = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
TRAFFIC_URL      = "https://data.cityofnewyork.us/resource/7ym2-wayt.json"
COLLISION_URL    = "https://data.cityofnewyork.us/resource/h9gi-nx95.json"

# ── Cache paths ────────────────────────────────────────────────────────────────
POTHOLE_CACHE   = MODEL_DIR / "pothole_cache.parquet"
TRAFFIC_CACHE   = MODEL_DIR / "traffic_cache.parquet"
COLLISION_CACHE = MODEL_DIR / "collision_cache.parquet"
ENRICHED_CACHE  = MODEL_DIR / "enriched_cache.parquet"

# ── Collision search radii ─────────────────────────────────────────────────────
CRASH_RADIUS_M          = 200   # any crash within 200 m → nearby_crashes count
PAVEMENT_CRASH_RADIUS_M = 500   # pavement-specific crash within 500 m → flag

PAVEMENT_FACTORS = {"Pavement Slippery", "Pavement Defective"}


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════

def fetch_all(pothole_limit: int = 10_000, use_cache: bool = True) -> pd.DataFrame:
    """
    Return enriched DataFrame with columns from all three datasets.
    Added columns: traffic_volume, nearby_crashes, pavement_crash_nearby.
    """
    if use_cache and ENRICHED_CACHE.exists():
        return pd.read_parquet(ENRICHED_CACHE)

    print("  Fetching 311 pothole reports …")
    potholes = _fetch_potholes(pothole_limit)

    print("  Fetching traffic volume counts …")
    traffic = _fetch_traffic()

    print("  Fetching motor vehicle collisions …")
    collisions = _fetch_collisions()

    print("  Joining datasets …")
    df = _join_traffic(potholes, traffic)
    df = _join_collisions(df, collisions)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(ENRICHED_CACHE, index=False)
    return df


def fetch_potholes(limit: int = 10_000, use_cache: bool = True) -> pd.DataFrame:
    """Backwards-compatible single-dataset fetch (used by train.py)."""
    if use_cache and POTHOLE_CACHE.exists():
        return pd.read_parquet(POTHOLE_CACHE)
    return _fetch_potholes(limit)


# ══════════════════════════════════════════════════════════════════════════════
# Dataset fetchers
# ══════════════════════════════════════════════════════════════════════════════

def _fetch_potholes(limit: int = 10_000) -> pd.DataFrame:
    params = {
        "$limit": limit,
        "$select": (
            "unique_key,created_date,closed_date,status,"
            "complaint_type,descriptor,borough,street_name,"
            "latitude,longitude,location_type"
        ),
        "$where": "upper(descriptor) LIKE '%POTHOLE%'",
        "$order": "created_date DESC",
    }
    df = _get(NYC_311_URL, params)
    df = _clean_potholes(df)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(POTHOLE_CACHE, index=False)
    return df


def _fetch_traffic(limit: int = 100_000) -> pd.DataFrame:
    """
    Fetch automated traffic counts and aggregate to avg daily volume
    per (street_key, boro_key) for street-name joining.
    """
    if TRAFFIC_CACHE.exists():
        return pd.read_parquet(TRAFFIC_CACHE)

    params = {
        "$limit": limit,
        "$select": "segmentid,street,boro,vol,yr,m,d",
        "$order": "yr DESC",
    }
    raw = _get(TRAFFIC_URL, params)
    if raw.empty:
        return raw

    raw["vol"] = pd.to_numeric(raw["vol"], errors="coerce").fillna(0)
    raw["date"] = (
        raw["yr"].astype(str) + "-" +
        raw["m"].astype(str).str.zfill(2) + "-" +
        raw["d"].astype(str).str.zfill(2)
    )

    # daily totals per segment, then average across all days observed
    daily = (
        raw.groupby(["segmentid", "street", "boro", "date"])["vol"]
        .sum()
        .reset_index()
    )
    seg_avg = (
        daily.groupby(["segmentid", "street", "boro"])["vol"]
        .mean()
        .reset_index()
        .rename(columns={"vol": "daily_avg_vol"})
    )
    seg_avg["street_key"] = seg_avg["street"].apply(_norm_street)
    seg_avg["boro_key"]   = seg_avg["boro"].str.upper().str.strip()

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    seg_avg.to_parquet(TRAFFIC_CACHE, index=False)
    return seg_avg


def _fetch_collisions(limit: int = 50_000) -> pd.DataFrame:
    """
    Fetch NYPD motor vehicle collisions with lat/lon and pavement flag.
    """
    if COLLISION_CACHE.exists():
        return pd.read_parquet(COLLISION_CACHE)

    params = {
        "$limit": limit,
        "$select": (
            "collision_id,crash_date,borough,latitude,longitude,"
            "contributing_factor_vehicle_1,contributing_factor_vehicle_2,"
            "number_of_persons_injured,number_of_persons_killed"
        ),
        "$where": "latitude IS NOT NULL AND longitude IS NOT NULL",
        "$order": "crash_date DESC",
    }
    df = _get(COLLISION_URL, params)
    if df.empty:
        return df

    df["latitude"]  = pd.to_numeric(df["latitude"],  errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df = df.dropna(subset=["latitude", "longitude"])
    df = df[df["latitude"].between(40.4, 40.95)]
    df = df[df["longitude"].between(-74.3, -73.6)]

    # flag pavement-related crashes
    for col in ["contributing_factor_vehicle_1", "contributing_factor_vehicle_2"]:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("")

    df["is_pavement_crash"] = (
        df["contributing_factor_vehicle_1"].isin(PAVEMENT_FACTORS) |
        df["contributing_factor_vehicle_2"].isin(PAVEMENT_FACTORS)
    ).astype(int)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(COLLISION_CACHE, index=False)
    return df


# ══════════════════════════════════════════════════════════════════════════════
# Join helpers
# ══════════════════════════════════════════════════════════════════════════════

def _join_traffic(potholes: pd.DataFrame, traffic: pd.DataFrame) -> pd.DataFrame:
    """
    Add traffic_volume column by matching street_name + borough.
    Rows with no match get NaN (XGBoost handles missing values natively).
    Falls back to borough median when a street isn't in the traffic dataset.
    """
    df = potholes.copy()

    if traffic.empty:
        df["traffic_volume"] = np.nan
        return df

    # Build lookup: (street_key, boro_key) → max daily_avg_vol across segments
    lookup = (
        traffic.groupby(["street_key", "boro_key"])["daily_avg_vol"]
        .max()
        .to_dict()
    )

    # Borough-level medians as fallback
    boro_median = (
        traffic.groupby("boro_key")["daily_avg_vol"]
        .median()
        .to_dict()
    )

    street_key = df.get("street_name", pd.Series("", index=df.index)).apply(_norm_street)
    boro_key   = df["borough"].str.upper().str.strip()

    def _lookup(sk, bk):
        v = lookup.get((sk, bk))
        if v is not None:
            return v
        return boro_median.get(bk, np.nan)

    df["traffic_volume"] = [
        _lookup(sk, bk) for sk, bk in zip(street_key, boro_key)
    ]
    return df


def _join_collisions(potholes: pd.DataFrame, collisions: pd.DataFrame) -> pd.DataFrame:
    """
    For each pothole, count collisions within CRASH_RADIUS_M metres and flag
    any pavement-specific crash within PAVEMENT_CRASH_RADIUS_M metres.
    Uses sklearn BallTree (haversine) for vectorised radius search.
    """
    df = potholes.copy()

    if collisions.empty or len(collisions) < 10:
        df["nearby_crashes"]       = 0
        df["pavement_crash_nearby"] = 0
        return df

    collision_coords  = np.radians(collisions[["latitude", "longitude"]].values)
    pavement_mask     = collisions["is_pavement_crash"].values.astype(bool)
    pavement_coords   = collision_coords[pavement_mask]

    pothole_coords = np.radians(df[["latitude", "longitude"]].values)

    tree     = BallTree(collision_coords, metric="haversine")
    p_tree   = BallTree(pavement_coords,  metric="haversine") if pavement_mask.any() else None

    R = 6_371_000  # Earth radius metres
    df["nearby_crashes"] = tree.query_radius(
        pothole_coords, r=CRASH_RADIUS_M / R, count_only=True
    )

    if p_tree is not None:
        df["pavement_crash_nearby"] = (
            p_tree.query_radius(
                pothole_coords, r=PAVEMENT_CRASH_RADIUS_M / R, count_only=True
            ) > 0
        ).astype(int)
    else:
        df["pavement_crash_nearby"] = 0

    return df


# ══════════════════════════════════════════════════════════════════════════════
# Utilities
# ══════════════════════════════════════════════════════════════════════════════

def _get(url: str, params: dict) -> pd.DataFrame:
    resp = requests.get(url, params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)


def _clean_potholes(df: pd.DataFrame) -> pd.DataFrame:
    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["closed_date"]  = pd.to_datetime(df["closed_date"],  errors="coerce")
    df["latitude"]     = pd.to_numeric(df.get("latitude"),  errors="coerce")
    df["longitude"]    = pd.to_numeric(df.get("longitude"), errors="coerce")

    df = df.dropna(subset=["created_date", "latitude", "longitude"])
    df = df[df["latitude"].between(40.4, 40.95)]
    df = df[df["longitude"].between(-74.3, -73.6)]

    for col, default in [
        ("borough",       "UNKNOWN"),
        ("descriptor",    ""),
        ("status",        "Open"),
        ("location_type", ""),
        ("street_name",   ""),
    ]:
        df[col] = df.get(col, pd.Series(default, index=df.index)).str.strip().fillna(default)

    df["borough"] = df["borough"].str.upper()
    return df.reset_index(drop=True)


_ABBREV = re.compile(
    r"\b(st(reet)?|ave(nue)?|blvd|boulevard|rd|road|dr|drive|"
    r"ln|lane|pl|place|pkwy|parkway|hwy|highway|ct|court|ter(race)?)\b",
    re.IGNORECASE,
)

def _norm_street(name: str) -> str:
    """Normalise a street name for fuzzy matching across datasets."""
    if not isinstance(name, str):
        return ""
    s = name.upper().strip()
    s = _ABBREV.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s
