"""
Training script — run once to build and save the XGBoost models.

Usage:
  python -m ml.train              # fetches all three NYC datasets (enriched)
  python -m ml.train --limit 5000 # smaller pothole fetch for quick testing
  python -m ml.train --no-cache   # bypass all local parquet caches
"""

import argparse
import time

from .data import fetch_all
from .model import PotholeRiskModel


def main() -> None:
    parser = argparse.ArgumentParser(description="Train PotholeIQ XGBoost models")
    parser.add_argument("--limit",    type=int, default=10_000)
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()

    print(f"[1/3] Fetching enriched NYC dataset (pothole limit={args.limit}) …")
    t0 = time.time()
    df = fetch_all(pothole_limit=args.limit, use_cache=not args.no_cache)
    print(f"      {len(df):,} records  |  "
          f"traffic_volume filled: {df['traffic_volume'].notna().sum():,}  |  "
          f"nearby_crashes mean: {df['nearby_crashes'].mean():.2f}  "
          f"({time.time()-t0:.1f}s)")

    print("[2/3] Training XGBoost models …")
    t1 = time.time()
    model = PotholeRiskModel()
    model.fit(df, verbose=True)
    print(f"      Training done  ({time.time()-t1:.1f}s)")

    print("[3/3] Saving models …")
    model.save()
    print("Done — models ready at ml/models/")


if __name__ == "__main__":
    main()
