"""Assign a canonical feature row to a supported fraud neighbourhood."""

from typing import Any, Dict, Optional

import pandas as pd

from src.features import MODEL_FEATURES
from src.label import Label
from src.small_model.statistics import assignment_details
from src.small_model.train import load_bundle


def predict_transaction(
    features: pd.DataFrame, bundle: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Return versioned cluster evidence and an operational model label."""
    if len(features) != 1:
        raise ValueError("Small-model prediction expects exactly one feature row.")
    missing = [name for name in MODEL_FEATURES if name not in features]
    if missing:
        raise ValueError(f"Small-model feature row is missing: {missing}")
    loaded = bundle or load_bundle()
    transformed = loaded["preprocessor"].transform(features[MODEL_FEATURES])
    clusters, distances, confidence, accepted = assignment_details(
        transformed, loaded["clusterer"], loaded["distance_limits"]
    )
    nearest_cluster = int(clusters[0])
    statistic = next(
        item
        for item in loaded["cluster_statistics"]
        if int(item["cluster_id"]) == nearest_cluster
    )
    within = bool(accepted[0])
    predicted = statistic["predicted_label"] if within else Label.LEGITIMATE.value
    return {
        "cluster_id": nearest_cluster if within else None,
        "nearest_cluster_id": nearest_cluster,
        "model_version": loaded["metadata"].get("version"),
        "cluster_size": int(statistic["cluster_size"]) if within else 0,
        "total_assigned_transactions": int(statistic["total_assigned_transactions"]),
        "reported_fraud_count": int(statistic["reported_fraud_count"]) if within else 0,
        "reported_fraud_percentage": float(statistic["reported_fraud_percentage"])
        if within
        else 0.0,
        "smoothed_fraud_percentage": float(statistic["smoothed_fraud_percentage"])
        if within
        else 0.0,
        "fraud_rate_lower_bound": float(statistic["fraud_rate_lower_bound"])
        if within
        else 0.0,
        "assignment_distance": round(float(distances[0]), 6),
        "membership_confidence": round(float(confidence[0]), 6),
        "within_fraud_neighbourhood": within,
        "cluster_flagged": bool(statistic["cluster_flagged"]) if within else False,
        "predicted_label": predicted,
    }
