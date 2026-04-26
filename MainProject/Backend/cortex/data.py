"""
NYC Open Data pipeline for PotholeIQ — Kevin's ML module.

Datasets:
  311 Service Requests   erm2-nwe9      pothole reports (last 5 years)
  Automated Traffic      7ym2-wayt      real vehicle counts per street segment
  Motor Vehicle Crashes  h9gi-nx95      collision proximity features
  NY State AADT          6amx-2pbv      annual avg daily traffic by road segment

Limits can be overridden via fetch_all(pothole_limit=N, use_cache=False).
CLI: python -m cortex.data [--limit N] [--no-cache]
"""

from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
import requests
from pathlib import Path
from sklearn.neighbors import BallTree

MODEL_DIR = Path(__file__).parent / "models"

# ── Endpoints ──────────────────────────────────────────────────────────────────
NYC_311_URL   = "https://data.cityofnewyork.us/resource/erm2-nwe9.json"
TRAFFIC_URL   = "https://data.cityofnewyork.us/resource/7ym2-wayt.json"
COLLISION_URL = "https://data.cityofnewyork.us/resource/h9gi-nx95.json"
AADT_URL      = "https://data.ny.gov/resource/6amx-2pbv.json"

# ── Cache paths ────────────────────────────────────────────────────────────────
POTHOLE_CACHE   = MODEL_DIR / "pothole_cache.parquet"
TRAFFIC_CACHE   = MODEL_DIR / "traffic_cache.parquet"
COLLISION_CACHE = MODEL_DIR / "collision_cache.parquet"
AADT_CACHE      = MODEL_DIR / "aadt_cache.parquet"
ENRICHED_CACHE  = MODEL_DIR / "enriched_cache.parquet"

# ── Collision radii ────────────────────────────────────────────────────────────
CRASH_RADIUS_M          = 500
PAVEMENT_CRASH_RADIUS_M = 1000
PAVEMENT_FACTORS        = {"Pavement Slippery", "Pavement Defective"}

# NYC county → borough name mapping for AADT data
AADT_COUNTY_TO_BOROUGH = {
    "Bronx":    "BRONX",
    "Kings":    "BROOKLYN",
    "New York": "MANHATTAN",
    "Queens":   "QUEENS",
    "Richmond": "STATEN ISLAND",
}


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════

def fetch_all(pothole_limit: int = 50_000, use_cache: bool = True) -> pd.DataFrame:
    """
    Return enriched DataFrame joining all four NYC datasets.
    Filters 311 data to last 5 years for deep ML training.
    Added columns: traffic_volume, aadt, nearby_crashes, pavement_crash_nearby.
    Set use_cache=False to force re-fetch even with cached parquet files.
    """
    if use_cache and ENRICHED_CACHE.exists():
        return pd.read_parquet(ENRICHED_CACHE)

    print("  [data] Fetching 311 pothole reports (last 5 years) …")
    potholes = _fetch_potholes(pothole_limit)

    print("  [data] Fetching automated traffic volume counts …")
    traffic = _fetch_traffic(use_cache=use_cache)

    print("  [data] Fetching NY State AADT by road segment …")
    aadt = _fetch_aadt(use_cache=use_cache)

    print("  [data] Fetching motor vehicle collisions …")
    collisions = _fetch_collisions(use_cache=use_cache)

    print("  [data] Joining datasets …")
    df = _join_traffic(potholes, traffic)
    df = _join_aadt(df, aadt)
    df = _join_collisions(df, collisions)

    _print_data_quality(df)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(ENRICHED_CACHE, index=False)
    return df


def fetch_potholes(limit: int = 50_000, use_cache: bool = True) -> pd.DataFrame:
    if use_cache and POTHOLE_CACHE.exists():
        return pd.read_parquet(POTHOLE_CACHE)
    return _fetch_potholes(limit)


# ══════════════════════════════════════════════════════════════════════════════
# Fetchers
# ══════════════════════════════════════════════════════════════════════════════

def _fetch_potholes(limit: int = 50_000) -> pd.DataFrame:
    five_years_ago = (datetime.now(timezone.utc) - timedelta(days=1825)).strftime(
        "%Y-%m-%dT00:00:00"
    )
    params = {
        "$limit":  limit,
        "$select": (
            "unique_key,created_date,closed_date,status,"
            "complaint_type,descriptor,borough,street_name,"
            "latitude,longitude,location_type"
        ),
        "$where":  (
            f"upper(descriptor) LIKE '%POTHOLE%' "
            f"AND created_date >= '{five_years_ago}'"
        ),
        "$order":  "created_date DESC",
    }
    df = _get(NYC_311_URL, params)
    df = _clean_potholes(df)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(POTHOLE_CACHE, index=False)
    return df


def _fetch_traffic(limit: int = 200_000, use_cache: bool = True) -> pd.DataFrame:
    if use_cache and TRAFFIC_CACHE.exists():
        return pd.read_parquet(TRAFFIC_CACHE)

    params = {
        "$limit":  limit,
        "$select": "segmentid,street,boro,vol,yr,m,d",
        "$order":  "yr DESC",
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
    daily = (
        raw.groupby(["segmentid", "street", "boro", "date"])["vol"]
        .sum().reset_index()
    )
    seg_avg = (
        daily.groupby(["segmentid", "street", "boro"])["vol"]
        .mean().reset_index()
        .rename(columns={"vol": "daily_avg_vol"})
    )
    seg_avg["street_key"] = seg_avg["street"].apply(_norm_street)
    seg_avg["boro_key"]   = seg_avg["boro"].str.upper().str.strip()

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    seg_avg.to_parquet(TRAFFIC_CACHE, index=False)
    return seg_avg


def _fetch_aadt(limit: int = 100_000, use_cache: bool = True) -> pd.DataFrame:
    """
    NY State Annual Average Daily Traffic (AADT) filtered to NYC counties.
    Dataset: data.ny.gov/resource/6amx-2pbv.json
    """
    if use_cache and AADT_CACHE.exists():
        return pd.read_parquet(AADT_CACHE)

    nyc_counties = "('Bronx','Kings','New York','Queens','Richmond')"
    params = {
        "$limit":  limit,
        "$select": "station_id,county,municipality,road_name,aadt_year,count",
        "$where":  f"county IN {nyc_counties}",
        "$order":  "aadt_year DESC",
    }
    raw = _get(AADT_URL, params)
    if raw.empty:
        return raw

    raw["count"] = pd.to_numeric(raw["count"], errors="coerce").fillna(0)
    raw["aadt_year"] = pd.to_numeric(raw["aadt_year"], errors="coerce")

    # Keep only the most recent year per station
    raw = raw.sort_values("aadt_year", ascending=False)
    raw = raw.drop_duplicates(subset=["station_id"])

    raw["borough"]    = raw["county"].map(AADT_COUNTY_TO_BOROUGH).fillna("UNKNOWN")
    raw["street_key"] = raw["road_name"].apply(_norm_street)
    raw["boro_key"]   = raw["borough"].str.upper().str.strip()

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    raw.to_parquet(AADT_CACHE, index=False)
    return raw


def _fetch_collisions(limit: int = 100_000, use_cache: bool = True) -> pd.DataFrame:
    if use_cache and COLLISION_CACHE.exists():
        return pd.read_parquet(COLLISION_CACHE)

    five_years_ago = (datetime.now(timezone.utc) - timedelta(days=1825)).strftime(
        "%Y-%m-%dT00:00:00"
    )
    params = {
        "$limit":  limit,
        "$select": (
            "collision_id,crash_date,borough,latitude,longitude,"
            "contributing_factor_vehicle_1,contributing_factor_vehicle_2,"
            "number_of_persons_injured,number_of_persons_killed"
        ),
        "$where":  (
            f"latitude IS NOT NULL AND longitude IS NOT NULL "
            f"AND crash_date >= '{five_years_ago}'"
        ),
        "$order":  "crash_date DESC",
    }
    df = _get(COLLISION_URL, params)
    if df.empty:
        return df

    df["latitude"]  = pd.to_numeric(df["latitude"],  errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df = df.dropna(subset=["latitude", "longitude"])
    df = df[df["latitude"].between(40.4, 40.95)]
    df = df[df["longitude"].between(-74.3, -73.6)]

    for col in ["contributing_factor_vehicle_1", "contributing_factor_vehicle_2"]:
        df[col] = df.get(col, pd.Series("", index=df.index)).fillna("")

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
    df = potholes.copy()
    if traffic.empty:
        df["traffic_volume"] = np.nan
        return df

    lookup = (
        traffic.groupby(["street_key", "boro_key"])["daily_avg_vol"]
        .max().to_dict()
    )
    boro_median = traffic.groupby("boro_key")["daily_avg_vol"].median().to_dict()

    sk = df.get("street_name", pd.Series("", index=df.index)).apply(_norm_street)
    bk = df["borough"].str.upper().str.strip()

    df["traffic_volume"] = [
        lookup.get((s, b), boro_median.get(b, np.nan))
        for s, b in zip(sk, bk)
    ]
    return df


def _join_aadt(potholes: pd.DataFrame, aadt: pd.DataFrame) -> pd.DataFrame:
    """
    Merge AADT (annual avg daily traffic) by road name + borough.
    Provides a stable annual count vs. the snapshot-based traffic_volume.
    Falls back to borough median AADT when street not matched.
    """
    df = potholes.copy()
    if aadt.empty:
        df["aadt"] = np.nan
        return df

    lookup = (
        aadt.groupby(["street_key", "boro_key"])["count"]
        .max().to_dict()
    )
    boro_median = aadt.groupby("boro_key")["count"].median().to_dict()

    sk = df.get("street_name", pd.Series("", index=df.index)).apply(_norm_street)
    bk = df["borough"].str.upper().str.strip()

    df["aadt"] = [
        lookup.get((s, b), boro_median.get(b, np.nan))
        for s, b in zip(sk, bk)
    ]
    return df


def _join_collisions(potholes: pd.DataFrame, collisions: pd.DataFrame) -> pd.DataFrame:
    df = potholes.copy()
    if collisions.empty or len(collisions) < 10:
        df["nearby_crashes"]        = 0
        df["pavement_crash_nearby"] = 0
        return df

    c_coords = np.radians(collisions[["latitude", "longitude"]].values)
    pav_mask  = collisions["is_pavement_crash"].values.astype(bool)
    p_coords  = c_coords[pav_mask]

    pot_coords = np.radians(df[["latitude", "longitude"]].values)
    R = 6_371_000

    tree  = BallTree(c_coords, metric="haversine")
    df["nearby_crashes"] = tree.query_radius(
        pot_coords, r=CRASH_RADIUS_M / R, count_only=True
    )

    if pav_mask.any():
        p_tree = BallTree(p_coords, metric="haversine")
        df["pavement_crash_nearby"] = (
            p_tree.query_radius(pot_coords, r=PAVEMENT_CRASH_RADIUS_M / R, count_only=True) > 0
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
    return pd.DataFrame(data) if data else pd.DataFrame()


def _clean_potholes(df: pd.DataFrame) -> pd.DataFrame:
    df["created_date"] = pd.to_datetime(df["created_date"], errors="coerce")
    df["closed_date"]  = pd.to_datetime(df["closed_date"],  errors="coerce")
    df["latitude"]     = pd.to_numeric(df.get("latitude"),  errors="coerce")
    df["longitude"]    = pd.to_numeric(df.get("longitude"), errors="coerce")

    df = df.dropna(subset=["created_date", "latitude", "longitude"])
    df = df[df["latitude"].between(40.4, 40.95)]
    df = df[df["longitude"].between(-74.3, -73.6)]

    for col, default in [
        ("borough", "UNKNOWN"), ("descriptor", ""), ("status", "Open"),
        ("location_type", ""),  ("street_name", ""),
    ]:
        col_data = df[col] if col in df.columns else pd.Series(default, index=df.index)
        df[col] = col_data.astype(str).str.strip().fillna(default)

    df["borough"] = df["borough"].str.upper()
    return df.reset_index(drop=True)


_ABBREV = re.compile(
    r"\b(st(reet)?|ave(nue)?|blvd|boulevard|rd|road|dr|drive|"
    r"ln|lane|pl|place|pkwy|parkway|hwy|highway|ct|court|ter(race)?)\b",
    re.IGNORECASE,
)

def _norm_street(name: str) -> str:
    if not isinstance(name, str):
        return ""
    s = _ABBREV.sub("", name.upper().strip())
    return re.sub(r"\s+", " ", s).strip()


# ══════════════════════════════════════════════════════════════════════════════
# Data quality reporting
# ══════════════════════════════════════════════════════════════════════════════

def _print_data_quality(df: pd.DataFrame) -> None:
    n = len(df)
    if n == 0:
        print("  [data] WARNING: enriched dataset is empty")
        return
    traffic_pct = (df["traffic_volume"].notna().mean() * 100) if "traffic_volume" in df.columns else 0
    aadt_pct = (df["aadt"].notna().mean() * 100) if "aadt" in df.columns else 0
    mean_crashes = df["nearby_crashes"].mean() if "nearby_crashes" in df.columns else 0
    pavement_pct = (df["pavement_crash_nearby"].mean() * 100) if "pavement_crash_nearby" in df.columns else 0
    print(f"  [data] Quality report — {n:,} records")
    print(f"           traffic_volume filled: {traffic_pct:.1f}%")
    print(f"           aadt filled:           {aadt_pct:.1f}%")
    print(f"           mean nearby_crashes:   {mean_crashes:.2f}")
    print(f"           pavement_crash_nearby: {pavement_pct:.1f}%")


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fetch and enrich NYC pothole data")
    parser.add_argument("--limit", type=int, default=50_000, help="Max 311 pothole records to fetch")
    parser.add_argument("--no-cache", action="store_true", help="Force re-fetch, ignore cached parquet files")
    args = parser.parse_args()
    df = fetch_all(pothole_limit=args.limit, use_cache=not args.no_cache)
    print(f"Done — {len(df):,} enriched records ready")
