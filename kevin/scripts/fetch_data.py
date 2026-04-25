"""
Download and cache raw NYC Open Data CSVs to Backend/data/raw/.
Run: python Backend/scripts/fetch_data.py
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import requests
import pandas as pd
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

DATASETS = [
    {
        "name":   "311 Pothole Complaints",
        "url":    "https://data.cityofnewyork.us/resource/erm2-nwe9.json",
        "params": {
            "$where": "upper(descriptor) LIKE '%POTHOLE%' AND created_date > '2024-01-01T00:00:00'",
            "$limit": 50000,
            "$order": "created_date DESC",
        },
        "file":   "potholes.csv",
    },
    {
        "name":   "Motor Vehicle Collisions",
        "url":    "https://data.cityofnewyork.us/resource/h9gi-nx95.json",
        "params": {
            "$where": "latitude IS NOT NULL AND crash_date > '2024-01-01'",
            "$limit": 50000,
            "$order": "crash_date DESC",
        },
        "file":   "collisions.csv",
    },
    {
        "name":   "Automated Traffic Volume",
        "url":    "https://data.cityofnewyork.us/resource/7ym2-wayt.json",
        "params": {"$limit": 50000, "$order": "yr DESC"},
        "file":   "traffic.csv",
    },
    {
        "name":   "NY State AADT",
        "url":    "https://data.ny.gov/resource/6amx-2pbv.json",
        "params": {
            "$where": "county IN ('Bronx','Kings','New York','Queens','Richmond')",
            "$limit": 50000,
        },
        "file":   "aadt.csv",
    },
]


def fetch_and_save(name: str, url: str, params: dict, filename: str) -> int:
    print(f"  Fetching {name}...")
    resp = requests.get(url, params=params, timeout=120)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json())
    path = RAW_DIR / filename
    df.to_csv(path, index=False)
    print(f"    ✓ {len(df):,} rows → {path}")
    return len(df)


if __name__ == "__main__":
    print("=" * 50)
    print("  PotholeIQ — Raw Data Fetch")
    print("=" * 50)
    total = 0
    for ds in DATASETS:
        total += fetch_and_save(ds["name"], ds["url"], ds["params"], ds["file"])
    print(f"\nDone — {total:,} total rows saved to Backend/data/raw/")
