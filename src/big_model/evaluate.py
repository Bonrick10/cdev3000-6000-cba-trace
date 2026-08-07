"""Evaluation utilities for chronological big-model holdouts."""

from typing import Any, Dict

import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.big_model.config import BIG_MODEL_UNUSUAL_THRESHOLD
from src.features import MODEL_FEATURES


def evaluate_model(model, evaluation_data: pd.DataFrame) -> Dict[str, Any]:
    """Return fraud-focused metrics without assuming both holdout classes."""
    if evaluation_data.empty:
        raise ValueError("Big-model evaluation data is empty.")
    target = evaluation_data["target"].astype(int).to_numpy()
    probabilities = model.predict_proba(evaluation_data[MODEL_FEATURES])[:, 1]
    predictions = (probabilities >= BIG_MODEL_UNUSUAL_THRESHOLD).astype(int)
    matrix = confusion_matrix(target, predictions, labels=[0, 1])
    both_classes = len(set(target)) == 2
    return {
        "number_of_transactions": int(len(target)),
        "accuracy": float(accuracy_score(target, predictions)),
        "f1": float(f1_score(target, predictions, zero_division=0)),
        "fraud_precision": float(precision_score(target, predictions, zero_division=0)),
        "fraud_recall": float(recall_score(target, predictions, zero_division=0)),
        "confusion_matrix": matrix.tolist(),
        "log_loss": float(log_loss(target, probabilities, labels=[0, 1])),
        "roc_auc": float(roc_auc_score(target, probabilities))
        if both_classes
        else None,
        "average_precision": float(average_precision_score(target, probabilities))
        if both_classes
        else None,
    }
