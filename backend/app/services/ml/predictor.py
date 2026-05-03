"""
predictor.py
Loads the trained XGBoost model and runs inference.
Falls back gracefully if the model file is not found (optional component).
"""
import os
import structlog
from pathlib import Path
from typing import Optional

from app.services.ml.feature_extractor import extract_features, features_to_vector, EXPECTED_FEATURE_NAMES

log = structlog.get_logger(__name__)

MODEL_PATH = Path("app/services/ml/model/xgboost_v1.pkl")

LABEL_CLASSES = ["No Discrepancy", "Omission", "Commission", "Inconsistency", "Illegibility"]

_model = None   # lazy-loaded singleton


def _load_model():
    global _model
    if _model is not None:
        return _model
    if not MODEL_PATH.exists():
        log.warning("predictor.model_not_found", path=str(MODEL_PATH))
        return None
    try:
        import joblib
        _model = joblib.load(MODEL_PATH)
        log.info("predictor.model_loaded", path=str(MODEL_PATH))
        return _model
    except Exception as e:
        log.error("predictor.load_error", error=str(e))
        return None


def predict(
    extracted_fields: dict,
    validation_result: dict,
    ocr_confidence: float,
) -> Optional[dict]:
    """
    Run XGBoost classification.

    Returns:
        {
          "label": str,
          "confidence": float,
          "top_features": list[{"name": str, "value": float, "importance": float}],
        }
        or None if model unavailable.
    """
    model = _load_model()
    if model is None:
        return None

    features = extract_features(extracted_fields, validation_result, ocr_confidence)
    vector = features_to_vector(features)

    try:
        import numpy as np
        X = np.array([vector], dtype=np.float32)
        probas = model.predict_proba(X)[0]
        pred_idx = int(probas.argmax())
        label = LABEL_CLASSES[pred_idx] if pred_idx < len(LABEL_CLASSES) else "No Discrepancy"
        confidence = float(probas[pred_idx])

        # Top features by feature importance (SHAP-lite: just importance × value)
        importances = getattr(model, "feature_importances_", [0.0] * len(EXPECTED_FEATURE_NAMES))
        ranked = sorted(
            zip(EXPECTED_FEATURE_NAMES, vector, importances),
            key=lambda x: abs(x[2]),
            reverse=True,
        )
        top_features = [
            {"name": n, "value": round(v, 4), "importance": round(imp, 4)}
            for n, v, imp in ranked[:5]
        ]

        log.info("predictor.done", label=label, confidence=confidence)
        return {"label": label, "confidence": confidence, "top_features": top_features}

    except Exception as e:
        log.error("predictor.inference_error", error=str(e))
        return None