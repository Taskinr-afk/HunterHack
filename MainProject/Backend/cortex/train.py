"""
Full ML training pipeline — supports quick and deep training modes.

Usage:
  python -m Backend.cortex.train                  # deep: RandomizedSearchCV (~2-3 hr)
  python -m Backend.cortex.train --quick           # quick: GridSearchCV (~2 min)
  python -m Backend.cortex.train --no-tune         # defaults, no search (~30 sec)
  python -m Backend.cortex.train --no-cache        # re-fetch all datasets
  python -m Backend.cortex.train --limit 50000     # custom data limit
  python -m Backend.cortex.train --n-iter 200      # RandomizedSearchCV iterations
  python -m Backend.cortex.train --cv 5            # cross-validation folds
"""

import argparse
import time

from .data import fetch_all
from .features import FEATURE_COLS, ACCIDENT_FEATURE_COLS
from .model import PotholeRiskModel


def main() -> None:
    parser = argparse.ArgumentParser(description="PotholeIQ ML Training Pipeline")
    parser.add_argument("--limit",    type=int,  default=50_000,
                        help="Max pothole records to fetch (default: 50000)")
    parser.add_argument("--quick",    action="store_true",
                        help="Quick GridSearchCV (~2 min) instead of deep training")
    parser.add_argument("--no-tune",  action="store_true",
                        help="Skip hyperparameter search entirely (~30 sec)")
    parser.add_argument("--no-cache", action="store_true",
                        help="Re-fetch all datasets from NYC Open Data APIs")
    parser.add_argument("--n-iter",   type=int,  default=500,
                        help="RandomizedSearchCV iterations for deep training (default: 500)")
    parser.add_argument("--cv",        type=int,  default=5,
                        help="Cross-validation folds (default: 5)")
    args = parser.parse_args()

    # Default: deep training (2-3 hours). --quick for fast iteration.
    deep = not args.quick and not args.no_tune

    print("=" * 60)
    print("  PotholeIQ — ML Training Pipeline")
    print("=" * 60)
    mode = "DEEP (RandomizedSearchCV)" if deep else (
           "QUICK (GridSearchCV)" if args.quick else
           "DEFAULTS (no tuning)")
    print(f"\n  Mode: {mode}")
    if deep:
        print(f"  n_iter: {args.n_iter}  |  cv: {args.cv}")
    print(f"  Data limit: {args.limit:,} records")
    print(f"  Cache: {'OFF (re-fetch)' if args.no_cache else 'ON'}")
    print()

    print(f"[1/3] Fetching enriched NYC dataset (limit={args.limit}) …")
    t0 = time.time()
    df = fetch_all(pothole_limit=args.limit, use_cache=not args.no_cache)
    print(f"      {len(df):,} records fetched in {time.time()-t0:.1f}s")
    print(f"      Columns: {list(df.columns)}")
    print(f"      Feature coverage:")
    for col in FEATURE_COLS + ACCIDENT_FEATURE_COLS:
        if col in df.columns:
            pct = df[col].notna().mean() * 100
            print(f"        {col:25s} {pct:5.1f}% filled")
    if "nearby_crashes" in df.columns:
        print(f"        {'nearby_crashes mean':25s} {df['nearby_crashes'].mean():.1f}")
    if "pavement_crash_nearby" in df.columns:
        pct = df["pavement_crash_nearby"].mean() * 100
        print(f"        {'pavement_crash_nearby':25s} {pct:.1f}% of potholes")
    if "has_accident" in df.columns:
        # won't be here yet, will be computed during build_features
        pass

    print(f"\n[2/3] Training 3 XGBoost models (tune={not args.no_tune}, deep={deep}) …")
    t1 = time.time()
    model = PotholeRiskModel()
    model.fit(
        df,
        tune=not args.no_tune,
        deep=deep,
        n_iter=args.n_iter,
        cv=args.cv,
        verbose=True,
    )
    train_time = time.time() - t1
    print(f"\n      Finished training in {train_time:.1f}s ({train_time/60:.1f} min)")

    print("\n[3/3] Saving models (joblib) …")
    model.save()
    print(f"\n{'='*60}")
    print(f"  Pipeline complete — {len(df):,} records, {train_time/60:.1f} min")
    print(f"  Models saved to cortex/models/")
    print(f"  risk_model.joblib     — risk score regressor")
    print(f"  urgency_model.joblib  — urgency tier classifier")
    print(f"  accident_model.joblib  — accident probability classifier")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()