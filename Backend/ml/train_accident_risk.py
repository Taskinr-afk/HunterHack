"""
Train XGBoost classifier to predict accident risk near a pothole.

Uses features from the canonical DB schema. Targets has_nearby_accident
(binary: nearby_crashes > 0).

Feature leakage note: nearby_crashes is excluded from the classifier
since it directly encodes the target.
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import xgboost as xgb
import joblib
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent

# Features for accident risk prediction (no leakage)
FEATURE_COLS = [
    "age_days", "borough_encoded", "traffic_volume",
    "latitude", "longitude", "month", "day_of_week",
]


def train_accident_risk_model():
    """Train XGBoost classifier for accident risk prediction."""
    print("Training Accident Risk Model...")

    features_path = Path(__file__).resolve().parent.parent / "data" / "processed" / "features.csv"
    if not features_path.exists():
        print("features.csv not found. Run feature_engineering.py first.")
        return None

    df = pd.read_csv(features_path)
    print(f"Loaded {len(df)} rows from features.csv")

    X = df[FEATURE_COLS].fillna(0)
    y = df["has_nearby_accident"]

    if y.nunique() < 2:
        print("ERROR: Only one class in target. Cannot train classifier.")
        return None

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
        eval_metric="logloss",
        use_label_encoder=False,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    try:
        auc = roc_auc_score(y_test, y_prob)
        print(f"ROC-AUC: {auc:.3f}")
    except ValueError:
        print("ROC-AUC: Could not compute")

    importance = pd.Series(model.feature_importances_, index=FEATURE_COLS)
    print("\nFeature Importance:")
    print(importance.sort_values(ascending=False))

    model_path = MODEL_DIR / "model_accident_risk.pkl"
    joblib.dump(model, model_path)
    print(f"\nModel saved to {model_path}")

    return model


if __name__ == "__main__":
    train_accident_risk_model()