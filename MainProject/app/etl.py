"""Validate and sanitize pothole data from external sources before storage."""

from __future__ import annotations

import pandas as pd

# NYC bounding box
LAT_MIN, LAT_MAX = 40.4, 41.0
LON_MIN, LON_MAX = -74.3, -73.7

VALID_STATUSES = {"open", "closed"}
VALID_BOROUGHS = {"MANHATTAN", "BROOKLYN", "QUEENS", "BRONX", "STATEN ISLAND"}


def validate_pothole_data(df: pd.DataFrame) -> pd.DataFrame:
    """Sanitize and validate incoming pothole data.

    - Drops rows missing required coordinates
    - Clips coordinates to NYC bounds
    - Strips whitespace from text fields
    - Validates status and borough values
    """
    if df.empty:
        return df

    original = len(df)

    # Drop rows without coordinates
    df = df.dropna(subset=["latitude", "longitude"])

    # Clip coordinates to NYC bounding box
    df["latitude"]  = df["latitude"].clip(LAT_MIN, LAT_MAX)
    df["longitude"] = df["longitude"].clip(LON_MIN, LON_MAX)

    # Strip whitespace from text fields
    for col in ("borough", "status", "descriptor", "street_name"):
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    df["borough"] = df["borough"].str.upper()

    # Validate status — normalize to expected values
    if "status" in df.columns:
        df.loc[:, "status"] = df["status"].str.lower().str.strip()
        df = df[df["status"].isin(VALID_STATUSES) | df["status"].isna()]

    # Validate borough — mark unknown boroughs
    if "borough" in df.columns:
        unknown = ~df["borough"].isin(VALID_BOROUGHS) & df["borough"].notna()
        df.loc[unknown, "borough"] = "UNKNOWN"

    cleaned = len(df)
    if cleaned < original:
        print(f"  [etl] Validated pothole data: {original} -> {cleaned} rows "
              f"({original - cleaned} dropped)")

    return df.reset_index(drop=True)