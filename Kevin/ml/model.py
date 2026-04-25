"""
PotholeRiskModel — XGBoost-only risk scoring engine.

Exposes two models:
  risk_model    XGBRegressor  → risk_score (float 0–100)
  urgency_model XGBClassifier → urgency_tier (0=Low … 3=Critical)

Public API:
  model = PotholeRiskModel()
  model.fit(df)                   # train on a labeled DataFrame
  results = model.predict(df)     # score new potholes, returns enriched DataFrame
  model.save() / .load()          # persist to ml/models/
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, accuracy_score

from .features import (
    FEATURE_COLS,
    build_features,
    compute_risk_labels,
    tier_to_label,
    tier_to_fix_days,
)

MODEL_DIR = Path(__file__).parent / "models"
RISK_MODEL_PATH = MODEL_DIR / "risk_model.json"
URGENCY_MODEL_PATH = MODEL_DIR / "urgency_model.json"

XGB_SHARED = dict(
    n_estimators=400,
    learning_rate=0.05,
    max_depth=5,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1,
    verbosity=0,
)


class PotholeRiskModel:
    def __init__(self) -> None:
        self.risk_model = xgb.XGBRegressor(
            objective="reg:squarederror",
            eval_metric="mae",
            **XGB_SHARED,
        )
        self.urgency_model = xgb.XGBClassifier(
            objective="multi:softmax",
            num_class=4,
            eval_metric="mlogloss",
            **XGB_SHARED,
        )
        self._fitted = False

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def fit(self, df: pd.DataFrame, verbose: bool = True) -> PotholeRiskModel:
        df = build_features(df)
        df = compute_risk_labels(df)

        X = df[FEATURE_COLS].values.astype(np.float32)
        y_risk = df["risk_score"].values.astype(np.float32)
        y_tier = df["urgency_tier"].values.astype(np.int32)

        X_tr, X_val, yr_tr, yr_val, yt_tr, yt_val = train_test_split(
            X, y_risk, y_tier, test_size=0.15, random_state=42
        )

        self.risk_model.fit(
            X_tr, yr_tr,
            eval_set=[(X_val, yr_val)],
            verbose=False,
        )
        self.urgency_model.fit(
            X_tr, yt_tr,
            eval_set=[(X_val, yt_val)],
            verbose=False,
        )

        if verbose:
            risk_mae = mean_absolute_error(yr_val, self.risk_model.predict(X_val))
            urgency_acc = accuracy_score(yt_val, self.urgency_model.predict(X_val))
            print(f"  risk_score  MAE  : {risk_mae:.2f} pts")
            print(f"  urgency_tier Acc : {urgency_acc:.3f}")

        self._fitted = True
        return self

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self._fitted:
            raise RuntimeError("Model not fitted — call fit() or load() first")

        df = build_features(df)
        X = df[FEATURE_COLS].values.astype(np.float32)

        risk_scores = np.clip(self.risk_model.predict(X), 0, 100).round(1)
        urgency_tiers = self.urgency_model.predict(X).astype(int)

        out = df.copy()
        out["risk_score"] = risk_scores
        out["urgency_tier"] = urgency_tiers
        out["urgency_label"] = [tier_to_label(t) for t in urgency_tiers]
        out["fix_days_estimate"] = [tier_to_fix_days(t) for t in urgency_tiers]
        return out

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, directory: Path | str = MODEL_DIR) -> None:
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        self.risk_model.save_model(d / "risk_model.json")
        self.urgency_model.save_model(d / "urgency_model.json")
        print(f"  Models saved to {d}/")

    @classmethod
    def load(cls, directory: Path | str = MODEL_DIR) -> "PotholeRiskModel":
        d = Path(directory)
        m = cls()
        m.risk_model.load_model(d / "risk_model.json")
        m.urgency_model.load_model(d / "urgency_model.json")
        m._fitted = True
        return m


# ------------------------------------------------------------------
# Convenience function for the FastAPI backend
# ------------------------------------------------------------------

_cached_model: PotholeRiskModel | None = None


def score_potholes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Load the saved model once and score a DataFrame of potholes.

    Returns df with added columns:
      risk_score (float 0–100), urgency_label (str), fix_days_estimate (int)
    """
    global _cached_model
    if _cached_model is None:
        _cached_model = PotholeRiskModel.load()
    return _cached_model.predict(df)
