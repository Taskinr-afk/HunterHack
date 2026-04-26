"""
ML model loading and prediction for the API layer.

Primary: loads Backend/cortex models (joblib XGBoost).
Fallback: heuristic rules when models are not yet trained.
"""

from __future__ import annotations

import numpy as np

_model = None


def _get_model():
    global _model
    if _model is None:
        try:
            from kevin.cortex.model import PotholeRiskModel
            _model = PotholeRiskModel.load()
        except Exception:
            _model = "heuristic"
    return _model


def predict_for_pothole(pothole: dict) -> dict:
    """
    Returns:
      accident_risk              LOW / MEDIUM / HIGH / CRITICAL
      accident_risk_probability  float 0–1
      predicted_repair_days      int
      risk_score                 float 0–100
      traffic_volume             int or None
    """
    model = _get_model()

    # ── Real model path ────────────────────────────────────────────────────────
    if model != "heuristic":
        try:
            import pandas as pd
            df     = pd.DataFrame([pothole])
            result = model.predict(df)
            row    = result.iloc[0]

            risk   = float(row.get("risk_score", 0))
            label  = str(row.get("urgency_label", "Low"))
            proba  = float(row.get("prob_high", 0) + row.get("prob_critical", 0))
            days   = int(row.get("fix_days_estimate", 14))

            return {
                "accident_risk":              label.upper(),
                "accident_risk_probability":  round(proba, 3),
                "predicted_repair_days":      days,
                "risk_score":                 round(risk, 1),
                "traffic_volume":             int(pothole.get("traffic_volume") or 0) or None,
            }
        except Exception:
            pass   # fall through to heuristic

    # ── Heuristic fallback ─────────────────────────────────────────────────────
    days_open    = float(pothole.get("age_days") or pothole.get("days_open") or 0)
    risk_score   = float(pothole.get("risk_score") or 0)
    borough      = (pothole.get("borough") or "MANHATTAN").upper()
    crashes      = int(pothole.get("nearby_crashes") or 0)

    # derive probability from risk score if available, else age+crashes heuristic
    if risk_score > 0:
        prob = min(risk_score / 100, 0.99)
    else:
        prob = min(days_open * 0.003 + crashes * 0.02, 0.95)

    if prob > 0.75 or risk_score > 75:
        label = "CRITICAL"
    elif prob > 0.50 or risk_score > 50:
        label = "HIGH"
    elif prob > 0.25 or risk_score > 25:
        label = "MEDIUM"
    else:
        label = "LOW"

    base_days = 7 if borough == "MANHATTAN" else 14
    repair    = max(1, base_days + int(days_open // 10))

    return {
        "accident_risk":             label,
        "accident_risk_probability": round(prob, 3),
        "predicted_repair_days":     repair,
        "risk_score":                round(risk_score, 1),
        "traffic_volume":            int(pothole.get("traffic_volume") or 0) or None,
    }
