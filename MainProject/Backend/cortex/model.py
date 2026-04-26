"""
PotholeRiskModel — XGBoost pipeline with GridSearchCV / RandomizedSearchCV tuning.

Three models:
  risk_model      → RMSE (regression, risk_score 0-100)
  urgency_model   → ROC-AUC one-vs-rest weighted (4-class classification)
  accident_model   → ROC-AUC binary (probability of crash near pothole)

Serialization: joblib (sklearn-compatible, supports pipeline objects)

Public API:
  model = PotholeRiskModel()
  model.fit(df, deep=False)   trains models (deep=True → 2-3 hr randomized search)
  model.predict(df)            returns df enriched with predictions
  model.save()                 writes cortex/models/*.joblib
  PotholeRiskModel.load()      restores from disk
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
    f1_score,
    classification_report,
)
from sklearn.model_selection import (
    GridSearchCV,
    RandomizedSearchCV,
    train_test_split,
)

from .features import (
    FEATURE_COLS,
    ACCIDENT_FEATURE_COLS,
    build_features,
    compute_risk_labels,
    compute_accident_label,
    tier_to_label,
    tier_to_fix_days,
)

MODEL_DIR                = Path(__file__).parent / "models"
RISK_MODEL_PATH          = MODEL_DIR / "risk_model.joblib"
URGENCY_MODEL_PATH       = MODEL_DIR / "urgency_model.joblib"
ACCIDENT_MODEL_PATH      = MODEL_DIR / "accident_model.joblib"

# ── Quick grid: finishes in ~2 min on a laptop ────────────────────────────────
_QUICK_GRID = {
    "max_depth":     [4, 6],
    "learning_rate": [0.05, 0.1],
    "n_estimators":  [200, 400],
    "subsample":     [0.8],
}

# ── Deep grid: 2-3 hours with RandomizedSearchCV n_iter=150 cv=5 ───────────────
_DEEP_GRID = {
    "max_depth":         [3, 4, 5, 6, 7, 8, 9],
    "learning_rate":     [0.01, 0.02, 0.03, 0.05, 0.08, 0.1, 0.15, 0.2],
    "n_estimators":      [200, 300, 400, 600, 800, 1000, 1200],
    "subsample":         [0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0],
    "colsample_bytree":  [0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    "min_child_weight":  [1, 3, 5, 7, 10],
    "gamma":             [0, 0.01, 0.05, 0.1, 0.2, 0.3],
    "reg_alpha":         [0, 0.001, 0.01, 0.05, 0.1, 0.5],
    "reg_lambda":        [0.5, 1.0, 1.5, 2.0],
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
        self.risk_model     = xgb.XGBRegressor(
            objective="reg:squarederror", eval_metric="rmse", **_XGB_BASE
        )
        self.urgency_model  = xgb.XGBClassifier(
            objective="multi:softmax", num_class=4,
            eval_metric="mlogloss", **_XGB_BASE
        )
        self.accident_model = xgb.XGBClassifier(
            objective="binary:logistic", eval_metric="logloss", **_XGB_BASE
        )
        self._fitted = False

    # ── Training ──────────────────────────────────────────────────────────────

    def fit(
        self,
        df: pd.DataFrame,
        tune: bool = True,
        deep: bool = False,
        n_iter: int = 150,
        cv: int = 5,
        verbose: bool = True,
    ) -> "PotholeRiskModel":
        """
        Train all three models.

        tune=True, deep=False  → GridSearchCV with quick grid (~2 min)
        tune=True, deep=True   → RandomizedSearchCV with deep grid (~2-3 hr)
        tune=False              → Default params, no search (~30 sec)
        """
        df = build_features(df)
        df = compute_risk_labels(df)
        df = compute_accident_label(df)

        X      = df[FEATURE_COLS].values.astype(np.float32)
        X_acc  = df[ACCIDENT_FEATURE_COLS].values.astype(np.float32)
        y_risk = df["risk_score"].values.astype(np.float32)
        y_tier = df["urgency_tier"].values.astype(int)
        y_acc  = df["has_accident"].values.astype(int)

        # Split risk/urgency features (11 cols) and accident features (9 cols) separately
        idx = train_test_split(np.arange(len(X)), test_size=0.20, random_state=42)[1]
        mask_val = np.zeros(len(X), dtype=bool)
        mask_val[idx] = True
        mask_tr = ~mask_val

        X_tr     = X[mask_tr]
        X_val    = X[mask_val]
        Xa_tr    = X_acc[mask_tr]
        Xa_val   = X_acc[mask_val]
        yr_tr    = y_risk[mask_tr]
        yr_val   = y_risk[mask_val]
        yt_tr    = y_tier[mask_tr]
        yt_val   = y_tier[mask_val]
        ya_tr    = y_acc[mask_tr]
        ya_val   = y_acc[mask_val]

        if tune and deep:
            self._train_deep(X_tr, Xa_tr, yr_tr, yt_tr, ya_tr, n_iter=n_iter, cv=cv, verbose=verbose)
        elif tune:
            self._train_quick(X_tr, Xa_tr, yr_tr, yt_tr, ya_tr, verbose=verbose)
        else:
            self._train_defaults(X_tr, Xa_tr, yr_tr, yt_tr, ya_tr, verbose=verbose)

        # ── Evaluation on held-out 20% ───────────────────────────────────────
        if verbose:
            self._evaluate(X_val, Xa_val, yr_val, yt_val, ya_val)

        self._fitted = True
        return self

    def _train_quick(self, X, Xa, yr, yt, ya, verbose=True):
        if verbose:
            print("  [model] GridSearchCV (quick) — risk model …")
        gs = GridSearchCV(
            xgb.XGBRegressor(objective="reg:squarederror", **_XGB_BASE),
            _QUICK_GRID, cv=3, scoring="neg_root_mean_squared_error",
            n_jobs=-1, refit=True, verbose=0,
        )
        gs.fit(X, yr)
        self.risk_model = gs.best_estimator_
        if verbose:
            print(f"       best params: {gs.best_params_}")

        if verbose:
            print("  [model] GridSearchCV (quick) — urgency model …")
        gs = GridSearchCV(
            xgb.XGBClassifier(objective="multi:softmax", num_class=4,
                              eval_metric="mlogloss", **_XGB_BASE),
            _QUICK_GRID, cv=3, scoring="accuracy",
            n_jobs=-1, refit=True, verbose=0,
        )
        gs.fit(X, yt)
        self.urgency_model = gs.best_estimator_
        if verbose:
            print(f"       best params: {gs.best_params_}")

        if verbose:
            print("  [model] GridSearchCV (quick) — accident model …")
        gs = GridSearchCV(
            xgb.XGBClassifier(objective="binary:logistic", eval_metric="logloss",
                              **_XGB_BASE),
            _QUICK_GRID, cv=3, scoring="roc_auc",
            n_jobs=-1, refit=True, verbose=0,
        )
        gs.fit(Xa, ya)
        self.accident_model = gs.best_estimator_
        if verbose:
            print(f"       best params: {gs.best_params_}")

    def _train_deep(self, X, Xa, yr, yt, ya, n_iter=150, cv=5, verbose=True):
        if verbose:
            print(f"  [model] RandomizedSearchCV (deep, n_iter={n_iter}, cv={cv}) — risk model …")
        rs = RandomizedSearchCV(
            xgb.XGBRegressor(objective="reg:squarederror", **_XGB_BASE),
            _DEEP_GRID, n_iter=n_iter, cv=cv,
            scoring="neg_root_mean_squared_error",
            n_jobs=-1, refit=True, verbose=0, random_state=42,
        )
        rs.fit(X, yr)
        self.risk_model = rs.best_estimator_
        if verbose:
            print(f"       best params: {rs.best_params_}")
            print(f"       best RMSE:   {-rs.best_score_:.3f}")

        if verbose:
            print(f"  [model] RandomizedSearchCV (deep, n_iter={n_iter}, cv={cv}) — urgency model …")
        rs = RandomizedSearchCV(
            xgb.XGBClassifier(objective="multi:softmax", num_class=4,
                              eval_metric="mlogloss", **_XGB_BASE),
            _DEEP_GRID, n_iter=n_iter, cv=cv,
            scoring="accuracy",
            n_jobs=-1, refit=True, verbose=0, random_state=42,
        )
        rs.fit(X, yt)
        self.urgency_model = rs.best_estimator_
        if verbose:
            print(f"       best params: {rs.best_params_}")
            print(f"       best accuracy: {rs.best_score_:.4f}")

        if verbose:
            print(f"  [model] RandomizedSearchCV (deep, n_iter={n_iter}, cv={cv}) — accident model …")
        rs = RandomizedSearchCV(
            xgb.XGBClassifier(objective="binary:logistic", eval_metric="logloss",
                              **_XGB_BASE),
            _DEEP_GRID, n_iter=n_iter, cv=cv,
            scoring="roc_auc",
            n_jobs=-1, refit=True, verbose=0, random_state=42,
        )
        rs.fit(Xa, ya)
        self.accident_model = rs.best_estimator_
        if verbose:
            print(f"       best params: {rs.best_params_}")
            print(f"       best ROC-AUC: {rs.best_score_:.4f}")

    def _train_defaults(self, X, Xa, yr, yt, ya, verbose=True):
        if verbose:
            print("  [model] Training with default params (no tuning) — risk model …")
        self.risk_model.fit(X, yr)

        if verbose:
            print("  [model] Training with default params — urgency model …")
        self.urgency_model.fit(X, yt)

        if verbose:
            print("  [model] Training with default params — accident model …")
        self.accident_model.fit(Xa, ya)

    def _evaluate(self, X_val, Xa_val, yr_val, yt_val, ya_val):
        yr_pred  = self.risk_model.predict(X_val)
        yt_pred  = self.urgency_model.predict(X_val)
        yt_proba = self.urgency_model.predict_proba(X_val)
        ya_pred  = self.accident_model.predict(Xa_val)
        ya_proba = self.accident_model.predict_proba(Xa_val)

        rmse     = np.sqrt(mean_squared_error(yr_val, yr_pred))
        roc_auc  = roc_auc_score(yt_val, yt_proba, multi_class="ovr", average="weighted")
        acc      = accuracy_score(yt_val, yt_pred)

        # Binary metrics for accident model
        acc_auc  = roc_auc_score(ya_val, ya_proba[:, 1])
        acc_f1   = f1_score(ya_val, ya_pred)
        acc_acc  = accuracy_score(ya_val, ya_pred)

        print(f"\n  ── Eval (20% hold-out, n={len(X_val)}) ──")
        print(f"  risk_score    RMSE     : {rmse:.3f} pts")
        print(f"  urgency_tier  ROC-AUC  : {roc_auc:.4f}  (OvR weighted)")
        print(f"  urgency_tier  Accuracy : {acc:.4f}")
        print(f"  accident_prob ROC-AUC  : {acc_auc:.4f}  (binary)")
        print(f"  accident_prob F1       : {acc_f1:.4f}")
        print(f"  accident_prob Accuracy : {acc_acc:.4f}")

        print(f"\n  ── Feature Importances ──")
        for name, model, cols in [
            ("risk",     self.risk_model,     FEATURE_COLS),
            ("urgency",  self.urgency_model,   FEATURE_COLS),
            ("accident", self.accident_model,  ACCIDENT_FEATURE_COLS),
        ]:
            importances = model.feature_importances_
            paired = sorted(zip(cols, importances), key=lambda x: -x[1])
            print(f"\n  {name}_model:")
            for feat, imp in paired:
                print(f"    {feat:25s} {imp:.4f}")

    # ── Inference ─────────────────────────────────────────────────────────────

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self._fitted:
            raise RuntimeError("Call fit() or load() first")

        df_feat = build_features(df)
        X       = df_feat[FEATURE_COLS].values.astype(np.float32)
        X_acc   = df_feat[ACCIDENT_FEATURE_COLS].values.astype(np.float32)

        risk_scores    = np.clip(self.risk_model.predict(X), 0, 100).round(1)
        urgency_tiers  = self.urgency_model.predict(X).astype(int)
        urgency_probas = self.urgency_model.predict_proba(X)
        accident_probas = self.accident_model.predict_proba(X_acc)[:, 1]

        # pad urgency probas to 4 columns if a tier was absent from training data
        if urgency_probas.shape[1] < 4:
            pad = np.zeros((len(urgency_probas), 4))
            classes = self.urgency_model.classes_
            for i, c in enumerate(classes):
                pad[:, int(c)] = urgency_probas[:, i]
            urgency_probas = pad

        out = df_feat.copy()
        out["risk_score"]            = risk_scores
        out["urgency_tier"]          = urgency_tiers
        out["urgency_label"]         = [tier_to_label(t)    for t in urgency_tiers]
        out["fix_days_estimate"]     = [tier_to_fix_days(t) for t in urgency_tiers]
        out["prob_low"]              = urgency_probas[:, 0].round(3)
        out["prob_medium"]           = urgency_probas[:, 1].round(3)
        out["prob_high"]             = urgency_probas[:, 2].round(3)
        out["prob_critical"]         = urgency_probas[:, 3].round(3)
        out["accident_probability"]  = np.clip(accident_probas, 0, 1).round(3)
        return out

    # ── Persistence (joblib) ──────────────────────────────────────────────────

    def save(self, directory: Path | str = MODEL_DIR) -> None:
        d = Path(directory)
        d.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.risk_model,     d / "risk_model.joblib",     compress=3)
        joblib.dump(self.urgency_model,  d / "urgency_model.joblib",  compress=3)
        joblib.dump(self.accident_model, d / "accident_model.joblib",  compress=3)
        print(f"  Models saved → {d}/")

    @classmethod
    def load(cls, directory: Path | str = MODEL_DIR) -> "PotholeRiskModel":
        d = Path(directory)
        m = cls()
        m.risk_model     = joblib.load(d / "risk_model.joblib")
        m.urgency_model  = joblib.load(d / "urgency_model.joblib")
        # accident_model is optional — heuristic fallback if missing
        accident_path = d / "accident_model.joblib"
        if accident_path.exists():
            m.accident_model = joblib.load(accident_path)
        else:
            m.accident_model = None
        m._fitted = True
        return m


# ── Convenience for FastAPI ────────────────────────────────────────────────────

_cached_model: PotholeRiskModel | None = None


def score_potholes(df: pd.DataFrame) -> pd.DataFrame:
    """Load saved model once and score a DataFrame of potholes."""
    global _cached_model
    if _cached_model is None:
        _cached_model = PotholeRiskModel.load()
    return _cached_model.predict(df)