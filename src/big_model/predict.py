"""Live fraud probability and operational label prediction."""

from typing import Any, Dict, Optional

import pandas as pd

from src.big_model.config import (
    BIG_MODEL_SUSPICIOUS_THRESHOLD,
    BIG_MODEL_UNUSUAL_THRESHOLD,
)
from src.big_model.train import load_bundle
from src.features import MODEL_FEATURES


def probability_to_label(
    probability: float,
    unusual_threshold: float = BIG_MODEL_UNUSUAL_THRESHOLD,
    suspicious_threshold: float = BIG_MODEL_SUSPICIOUS_THRESHOLD,
) -> str:
    if not 0 <= unusual_threshold < suspicious_threshold <= 1:
        raise ValueError("Thresholds must satisfy 0 <= unusual < suspicious <= 1.")
    if probability >= suspicious_threshold:
        return "suspicious"
    if probability >= unusual_threshold:
        return "unusual"
    return "legitimate"


def predict_transaction(
    features: pd.DataFrame,
    bundle: Optional[Dict[str, Any]] = None,
    unusual_threshold: float = BIG_MODEL_UNUSUAL_THRESHOLD,
    suspicious_threshold: float = BIG_MODEL_SUSPICIOUS_THRESHOLD,
) -> Dict[str, Any]:
    """Score exactly one canonical feature row."""
    if len(features) != 1:
        raise ValueError("Big-model prediction expects exactly one feature row.")
    missing = [name for name in MODEL_FEATURES if name not in features]
    if missing:
        raise ValueError(f"Big-model feature row is missing: {missing}")
    loaded = bundle or load_bundle()
    probability = float(loaded["model"].predict_proba(features[MODEL_FEATURES])[0, 1])
    return {
        "predicted_label": probability_to_label(
            probability, unusual_threshold, suspicious_threshold
        ),
        "fraud_probability": round(probability, 6),
        "risk_score": round(probability * 100, 2),
        "unusual_threshold": unusual_threshold,
        "suspicious_threshold": suspicious_threshold,
        "model_version": loaded["metadata"].get("version"),
    }
