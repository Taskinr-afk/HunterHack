"""
Sanity-check the raw CSVs in Backend/data/raw/.
Run after fetch_data.py: python Backend/scripts/explore_data.py
"""

import pandas as pd
from pathlib import Path

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"


def explore(filename: str, key_cols: list[str]) -> None:
    path = RAW_DIR / filename
    if not path.exists():
        print(f"  ✗ {filename} not found — run fetch_data.py first\n")
        return

    df = pd.read_csv(path)
    print(f"  {filename}: {len(df):,} rows × {df.shape[1]} cols")
    for col in key_cols:
        if col in df.columns:
            vc = df[col].value_counts().head(5)
            print(f"    {col}: {dict(vc)}")
        else:
            print(f"    {col}: ✗ MISSING")
    null_pct = df.isnull().mean().sort_values(ascending=False).head(5)
    print(f"    Top null %: {dict(null_pct.round(2))}")
    print()


if __name__ == "__main__":
    print("=" * 55)
    print("  PotholeIQ — Data Exploration")
    print("=" * 55)
    print()

    explore("potholes.csv",   ["borough", "status", "descriptor", "latitude", "longitude"])
    explore("collisions.csv", ["borough", "contributing_factor_vehicle_1", "latitude"])
    explore("traffic.csv",    ["boro", "street", "vol"])
    explore("aadt.csv",       ["county", "road_name", "count"])
