"""Big-model configuration."""

from src.settings import (
    BIG_MODEL_SUSPICIOUS_THRESHOLD,
    BIG_MODEL_UNUSUAL_THRESHOLD,
    MODEL_DIRECTORY,
)

MODEL_PATH = MODEL_DIRECTORY / "big_model_current.joblib"

MATURE_LABEL_MAPPING = {
    "confirmed_legitimate": 0,
    "legitimate": 0,
    "unusual": 0,
    "suspicious": 1,
    "confirmed_fraudulent": 1,
    "rule_violation": 1,
    "rule_approval": 0,
    "rule_alert": 0,
}

__all__ = [
    "BIG_MODEL_SUSPICIOUS_THRESHOLD",
    "BIG_MODEL_UNUSUAL_THRESHOLD",
    "MATURE_LABEL_MAPPING",
    "MODEL_PATH",
]
