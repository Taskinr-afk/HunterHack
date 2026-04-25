"""
Geospatial utility for PotholeIQ.

The canonical schema stores crash proximity as denormalized columns on
the potholes table (nearby_crashes, pavement_crash_nearby) rather than
a junction table. The ETL pipeline (etl.py) computes these counts at
ingest time.

This module provides a standalone re-count function for refreshing
crash proximity data after adding new collision data.
"""

import numpy as np
from app.database import get_conn


def recount_nearby_crashes(radius_km: float = 0.200):
    """Re-count nearby crashes for all potholes from the collisions dataset.

    Fetches fresh collision data from the NYC API and updates the
    nearby_crashes column on every pothole. This is a heavy operation.

    Default radius: 200m to match the cortex/data.py approach.
    """
    import httpx
    import pandas as pd

    print("Fetching collision data for re-count...")
    response = httpx.get(
        "https://data.cityofnewyork.us/resource/h9gi-nx95.json",
        params={"$where": "latitude IS NOT NULL AND crash_date > '2024-01-01'", "$limit": 50000},
        timeout=60,
    )
    response.raise_for_status()
    collisions_df = pd.DataFrame(response.json())

    collisions_df["latitude"] = pd.to_numeric(collisions_df["latitude"], errors="coerce")
    collisions_df["longitude"] = pd.to_numeric(collisions_df["longitude"], errors="coerce")
    collisions_df = collisions_df.dropna(subset=["latitude", "longitude"])
    collisions_df = collisions_df[
        (collisions_df["latitude"].between(40.4, 41.0)) &
        (collisions_df["longitude"].between(-74.3, -73.7))
    ]

    with get_conn() as conn:
        potholes = conn.execute("SELECT unique_key, latitude, longitude FROM potholes").fetchall()

    print(f"Re-counting crashes for {len(potholes)} potholes against {len(collisions_df)} collisions...")

    p_lats = np.radians(np.array([float(r["latitude"]) for r in potholes]))
    p_lons = np.radians(np.array([float(r["longitude"]) for r in potholes]))
    c_lats = np.radians(collisions_df["latitude"].values)
    c_lons = np.radians(collisions_df["longitude"].values)

    chunk_size = 5000
    counts = np.zeros(len(potholes), dtype=int)

    for start in range(0, len(collisions_df), chunk_size):
        end = min(start + chunk_size, len(collisions_df))
        c_lat_chunk = c_lats[start:end]
        c_lon_chunk = c_lons[start:end]

        dlat = c_lat_chunk[np.newaxis, :] - p_lats[:, np.newaxis]
        dlon = c_lon_chunk[np.newaxis, :] - p_lons[:, np.newaxis]
        a = np.sin(dlat / 2) ** 2 + np.cos(p_lats[:, np.newaxis]) * np.cos(c_lat_chunk[np.newaxis, :]) * np.sin(dlon / 2) ** 2
        dist = 6371 * 2 * np.arcsin(np.sqrt(a))
        counts += (dist <= radius_km).sum(axis=1)

    with get_conn() as conn:
        for i, pothole in enumerate(potholes):
            conn.execute(
                "UPDATE potholes SET nearby_crashes = ? WHERE unique_key = ?",
                (int(counts[i]), pothole["unique_key"]),
            )

    print(f"Updated nearby_crashes for {len(potholes)} potholes")
    print(f"Potholes with crashes nearby: {(counts > 0).sum()}")


if __name__ == "__main__":
    recount_nearby_crashes()