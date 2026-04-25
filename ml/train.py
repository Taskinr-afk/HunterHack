"""
Training script — run once to build and save the XGBoost models.

Usage:
  python -m ml.train              # fetches live NYC data (10 000 rows)
  python -m ml.train --limit 5000 # smaller fetch for quick testing
  python -m ml.train --no-cache   # bypass local parquet cache
"""

import argparse
import sys
import time

from .data import fetch_potholes
from .model import PotholeRiskModel


def main() -> None:
    parser = argparse.ArgumentParser(description="Train PotholeIQ XGBoost models")
    parser.add_argument("--limit", type=int, default=10_000)
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()

    print(f"[1/3] Fetching NYC 311 pothole data (limit={args.limit}) …")
    t0 = time.time()
    df = fetch_potholes(limit=args.limit, use_cache=not args.no_cache)
    print(f"      {len(df):,} records loaded  ({time.time()-t0:.1f}s)")

    print("[2/3] Training XGBoost models …")
    t1 = time.time()
    model = PotholeRiskModel()
    model.fit(df, verbose=True)
    print(f"      Training done  ({time.time()-t1:.1f}s)")

    print("[3/3] Saving models …")
    model.save()
    print("Done — models are ready at ml/models/")


if __name__ == "__main__":
    main()
