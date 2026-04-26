"""
PotholeRiskModel — XGBoost pipeline with GridSearchCV tuning.

Serialization: joblib (sklearn-compatible, supports pipeline objects)
Metrics:
  risk_model    → RMSE  (regression)
  urgency_model → ROC-AUC one-vs-rest weighted (multi-class classification)

Public API:
  model = PotholeRiskModel()
  model.fit(df)           trains both models with GridSearchCV
  model.predict(df)       returns df enriched with risk_score, urgency_label, etc.
  model.save()            writes kevin/ml/models/*.joblib
  PotholeRiskModel.load() restores from disk
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    mean_squared_error,
    roc_auc_score,
    accuracy_score,
)
from sklearn.model_selection import GridSearchCV, train_test_split

from .features import (
    FEATURE_COLS,
    build_features,
    compute_risk_labels,
    tier_to_label,
    tier_to_fix_days,
)

MODEL_DIR          = Path(__file__).parent / "models"
RISK_MODEL_PATH    = MODEL_DIR / "risk_model.joblib"
URGENCY_MODEL_PATH = MODEL_DIR / "urgency_model.joblib"

# Hackathon grid: small enough to finish in ~2 min on a laptop
_PARAM_GRID = {
    "max_depth":     [4, 6],
    "learning_rate": [0.05, 0.1],
    "n_estimators":  [200, 400],
    "subsample":     [0.8],
}

_XGB_BASE = dict(
    colsample_bytree=0.8,
    random_state=42,
    n_jobs=-1,
    verbosity=0,
    enable_categorical=False,
)


class PotholeRiskModel:
    def __init__(self) -> None:
        self.risk_model    = xgb.XGBRegressor(
            objective="reg:squarederror", eval_metric="rmse", **_XGB_BASE
        )
        self.urgency_model = xgb.XGBClassifier(
            objective="multi:softmax", num_class=4,
            eval_metric="mlogloss", **_XGB_BASE
        )
        self._fitted = False

    # ── Training ──────────────────────────────────────────────────────────────

    def fit(self, df: pd.DataFrame, tune: bool = True, verbose: bool = True) -> "PotholeRiskModel":
        """
        Train both models.
        tune=True  runs GridSearchCV (slower, better params)
        tune=False uses defaults (fast, good enough for quick iteration)
        """
        df = build_features(df)
        df = compute_risk_labels(df)

        X      = df[FEATURE_COLS].values.astype(np.float32)
        y_risk = df["risk_score"].values.astype(np.float32)
        y_tier = df["urgency_tier"].values.astype(np.int32)

        X_tr, X_val, yr_tr, yr_val, yt_tr, yt_val = train_test_split(
            X, y_risk, y_tier, test_size=0.20, random_state=42
        )

        if tune:
            if verbose:
                print("  [model] GridSearchCV — risk model …")
            gs_risk = GridSearchCV(
                xgb.XGBRegressor(objective="reg:squarederror", **_XGB_BASE),
                _PARAM_GRID, cv=3, scoring="neg_root_mean_squared_error",
                n_jobs=-1, refit=True, verbose=0,
            )
            gs_risk.fit(X_tr, yr_tr)
            self.risk_model = gs_risk.best_estimator_
            if verbose:
                print(f"       best params: {gs_risk.best_params_}")

            if verbose:
                print("  [model] GridSearchCV — urgency model …")
            gs_urgency = GridSearchCV(
                xgb.XGBClassifier(
                    objective="multi:softmax", num_class=4,
                    eval_metric="mlogloss", **_XGB_BASE
                ),
                _PARAM_GRID, cv=3, scoring="accuracy",
                n_jobs=-1, refit=True, verbose=0,
            )
            gs_urgency.fit(X_tr, yt_tr)
            self.urgency_model = gs_urgency.best_estimator_
            if verbose:
                print(f"       best params: {gs_urgency.best_params_}")
        else:
            self.risk_model.fit(X_tr, yr_tr)
            self.urgency_model.fit(X_tr, yt_tr)

        # ── Evaluation on held-out 20% ────────────────────────────────────────
        if verbose:
            yr_pred  = self.risk_model.predict(X_val)
            yt_pred  = self.urgency_model.predict(X_val)
            yt_proba = self.urgency_model.predict_proba(X_val)

            # Pad probability matrix to 4 columns if some classes were absent
            if yt_proba.shape[1] < 4:
                pad = np.zeros((len(yt_proba), 4))
                classes = self.urgency_model.classes_
                for i, c in enumerate(classes):
                    pad[:, int(c)] = yt_proba[:, i]
                yt_proba = pad

            rmse    = np.sqrt(mean_squared_error(yr_val, yr_pred))
            roc_auc = roc_auc_score(
                yt_val, yt_proba, multi_class="ovr", average="weighted",
                labels=[0, 1, 2, 3],
            )
            acc = accuracy_score(yt_val, yt_pred)

            print(f"\n  ── Eval (20% hold-out, n={len(X_val)}) ──")
            print(f"  risk_score   RMSE    : {rmse:.3f} pts")
            print(f"  urgency_tier ROC-AUC : {roc_auc:.4f}  (OvR weighted)")
            print(f"  urgency_tier Accuracy: {acc:.4f}")

        self._fitted = True
        return self

    # ── Inference ─────────────────────────────────────────────────────────────

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self._fitted:
            raise RuntimeError("Call fit() or load() first")

        df_feat = build_features(df)
        X       = df_feat[FEATURE_COLS].values.astype(np.float32)

        risk_scores    = np.clip(self.risk_model.predict(X), 0, 100).round(1)
        urgency_tiers  = self.urgency_model.predict(X).astype(int)
        urgency_probas = self.urgency_model.predict_proba(X)

        # pad to 4 columns if a tier was absent from training data
        if urgency_probas.shape[1] < 4:
            pad = np.zeros((len(urgency_probas), 4))
            classes = self.urgency_model.classes_
            for i, c in enumerate(classes):
                pad[:, int(c)] = urgency_probas[:, i]
            urgency_probas = pad

        out = df_feat.copy()
        out["risk_score"]        = risk_scores
        out["urgency_tier"]      = urgency_tiers
        out["urgency_label"]     = [tier_to_label(t)    for t in urgency_tiers]
        out["fix_days_estimate"] = [tier_to_fix_days(t) for t in urgency_tiers]
        out["prob_low"]          = urgency_probas[:, 0].round(3)
        out["prob_medium"]       = urgency_probas[:, 1].round(3)
        out["prob_high"]         = urgency_probas[:, 2].round(3)
        out["prob_critical"]     = urgency_probas[:, 3].round(3)
        out["accident_probability"] = (urgency_probas[:, 2] + urgency_probas[:, 3]).round(3)
        return out

    # ── Persistence (joblib) ──────────────────────────────────────────────────

    def save(self, directory: Path | str = MODEL_DIR) -> None:
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.risk_model,    d / "risk_model.joblib",    compress=3)
        joblib.dump(self.urgency_model, d / "urgency_model.joblib", compress=3)
        print(f"  Models saved → {d}/")

    @classmethod
    def load(cls, directory: Path | str = MODEL_DIR) -> "PotholeRiskModel":
        d = Path(directory)
        m = cls()
        m.risk_model    = joblib.load(d / "risk_model.joblib")
        m.urgency_model = joblib.load(d / "urgency_model.joblib")
        m._fitted       = True
        return m


# ── Convenience for FastAPI ────────────────────────────────────────────────────

_cached_model: PotholeRiskModel | None = None


def score_potholes(df: pd.DataFrame) -> pd.DataFrame:
    """Load saved model once and score a DataFrame of potholes."""
    global _cached_model
    if _cached_model is None:
        _cached_model = PotholeRiskModel.load()
    return _cached_model.predict(df)
