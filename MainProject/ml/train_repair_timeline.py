"""
Train XGBoost regressor to predict repair timeline for a pothole.

Uses only closed potholes (where we know days_to_close).
Excludes age_days/days_open from features since for closed potholes
days_to_close approximates days_open (trivial prediction).
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import xgboost as xgb
import joblib
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent

# Features for repair timeline (no days_open/age_days to avoid trivial prediction)
FEATURE_COLS = [
    "borough_encoded", "traffic_volume",
    "nearby_crashes", "latitude", "longitude",
    "month", "day_of_week",
]


def train_repair_timeline_model():
    """Train XGBoost regressor for repair timeline prediction."""
    print("Training Repair Timeline Model...")

    features_path = Path(__file__).resolve().parent.parent / "data" / "processed" / "features.csv"
    if not features_path.exists():
        print("features.csv not found. Run feature_engineering.py first.")
        return None

    df = pd.read_csv(features_path)

    closed = df[df["days_to_close"].notna()].copy()
    if len(closed) < 50:
        print(f"Warning: Only {len(closed)} closed potholes. Using heuristic fallback.")
        model_path = MODEL_DIR / "model_repair_timeline.pkl"
        joblib.dump(None, model_path)
        print(f"Saved dummy model to {model_path}")
        return None

    closed["days_to_close"] = closed["days_to_close"].astype(float)

    X = closed[FEATURE_COLS].fillna(0)
    y = closed["days_to_close"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = xgb.XGBRegressor(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))

    baseline_mae = mean_absolute_error(y_test, [y_train.mean()] * len(y_test))
    improvement = ((baseline_mae - mae) / baseline_mae) * 100

    print(f"\nMean Absolute Error: {mae:.1f} days")
    print(f"Root Mean Squared Error: {rmse:.1f} days")
    print(f"Baseline MAE (mean): {baseline_mae:.1f} days")
    print(f"Improvement over baseline: {improvement:.1f}%")

    importance = pd.Series(model.feature_importances_, index=FEATURE_COLS)
    print("\nFeature Importance:")
    print(importance.sort_values(ascending=False))

    model_path = MODEL_DIR / "model_repair_timeline.pkl"
    joblib.dump(model, model_path)
    print(f"\nModel saved to {model_path}")

    return model


if __name__ == "__main__":
    train_repair_timeline_model()