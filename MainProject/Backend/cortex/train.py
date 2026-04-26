"""
Full ML training pipeline.

Usage:
  python -m kevin.cortex.train            # full GridSearchCV pipeline
  python -m kevin.cortex.train --no-tune  # skip grid search (fast iteration)
  python -m kevin.cortex.train --no-cache # re-fetch all datasets
  python -m kevin.cortex.train --limit 5000
"""

import argparse
import time

from .data import fetch_all
from .features import FEATURE_COLS
from .model import PotholeRiskModel


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit",    type=int,  default=10_000)
    parser.add_argument("--no-tune",  action="store_true")
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()

    print("=" * 55)
    print("  PotholeIQ — ML Training Pipeline")
    print("=" * 55)

    print(f"\n[1/3] Fetching enriched NYC dataset (limit={args.limit}) …")
    t0 = time.time()
    df = fetch_all(pothole_limit=args.limit, use_cache=not args.no_cache)
    print(f"      {len(df):,} records in {time.time()-t0:.1f}s")
    print(f"      traffic_volume : {df['traffic_volume'].notna().mean()*100:.1f}% filled")
    print(f"      aadt           : {df['aadt'].notna().mean()*100:.1f}% filled")
    print(f"      nearby_crashes : mean={df['nearby_crashes'].mean():.1f}")
    print(f"      pavement flag  : {df['pavement_crash_nearby'].mean()*100:.1f}% of potholes")

    print(f"\n[2/3] Training XGBoost models (tune={not args.no_tune}) …")
    t1 = time.time()
    model = PotholeRiskModel()
    model.fit(df, tune=not args.no_tune, verbose=True)
    print(f"\n      Finished in {time.time()-t1:.1f}s")

    # ── Feature importances ─────────────────────────────────────────────────────
    print("\n  ── Feature Importances ──")
    for name, fitted_model in [("risk", model.risk_model), ("urgency", model.urgency_model)]:
        importances = fitted_model.feature_importances_
        paired = sorted(zip(FEATURE_COLS, importances), key=lambda x: -x[1])
        print(f"\n  {name}_model:")
        for feat, imp in paired:
            print(f"    {feat:25s} {imp:.4f}")

    print("\n[3/3] Saving models (joblib) …")
    model.save()
    print("\n✓ Pipeline complete — models ready at kevin/ml/models/\n")


if __name__ == "__main__":
    main()
