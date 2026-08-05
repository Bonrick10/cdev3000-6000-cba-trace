"""Cluster assignment confidence and supported fraud concentration."""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd

from src.label import Label
from src.small_model.config import (
    SMALL_MODEL_MIN_CLUSTER_SIZE,
    SMALL_MODEL_MIN_FRAUD_COUNT,
    SMALL_MODEL_SUSPICIOUS_LOWER_BOUND,
    SMALL_MODEL_SUSPICIOUS_RATE,
    SMALL_MODEL_UNUSUAL_RATE,
)


def wilson_lower_bound(successes: int, total: int, z: float = 1.96) -> float:
    """Return a conservative binomial proportion lower bound."""
    if total <= 0:
        return 0.0
    proportion = successes / total
    denominator = 1 + z**2 / total
    centre = proportion + z**2 / (2 * total)
    margin = z * math.sqrt(
        proportion * (1 - proportion) / total + z**2 / (4 * total**2)
    )
    return max((centre - margin) / denominator, 0.0)


def assignment_details(
    transformed: Any,
    clusterer,
    distance_limits: Dict[int, float],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return nearest cluster, distance, confidence, and accepted membership."""
    distances = np.asarray(clusterer.transform(transformed), dtype=float)
    cluster_ids = distances.argmin(axis=1).astype(int)
    nearest = distances[np.arange(len(distances)), cluster_ids]
    confidence = np.zeros(len(distances), dtype=float)
    accepted = np.zeros(len(distances), dtype=bool)
    for index, (cluster_id, distance) in enumerate(zip(cluster_ids, nearest)):
        limit = max(float(distance_limits[int(cluster_id)]), 1e-9)
        distance_confidence = math.exp(-float(distance) / limit)
        if distances.shape[1] > 1:
            ordered = np.partition(distances[index], 1)
            margin_confidence = max(
                (ordered[1] - ordered[0]) / max(ordered[1], 1e-9), 0.0
            )
            confidence[index] = (distance_confidence + margin_confidence) / 2
        else:
            confidence[index] = distance_confidence
        accepted[index] = distance <= limit
    return cluster_ids, nearest, confidence, accepted


def risk_label(statistic: Dict[str, Any]) -> str:
    """Map supported concentration to an operational model label."""
    size = int(statistic["cluster_size"])
    frauds = int(statistic["reported_fraud_count"])
    smoothed = float(statistic["smoothed_fraud_percentage"]) / 100
    lower = float(statistic["fraud_rate_lower_bound"]) / 100
    if size < SMALL_MODEL_MIN_CLUSTER_SIZE or frauds < SMALL_MODEL_MIN_FRAUD_COUNT:
        return Label.LEGITIMATE.value
    if (
        smoothed >= SMALL_MODEL_SUSPICIOUS_RATE
        and lower >= SMALL_MODEL_SUSPICIOUS_LOWER_BOUND
    ):
        return Label.SUSPICIOUS.value
    if smoothed >= SMALL_MODEL_UNUSUAL_RATE:
        return Label.UNUSUAL.value
    return Label.LEGITIMATE.value


def calculate_cluster_statistics(
    eligible: pd.DataFrame,
    cluster_ids: Iterable[int],
    accepted: Iterable[bool],
    number_of_clusters: int,
) -> List[Dict[str, Any]]:
    """Calculate risk using eligible transactions inside fraud neighbourhoods."""
    assigned = eligible.copy()
    assigned["nearest_cluster_id"] = np.asarray(list(cluster_ids), dtype=int)
    assigned["within_fraud_neighbourhood"] = np.asarray(list(accepted), dtype=bool)
    assigned["is_reported_fraud"] = (
        assigned["observed_label"] == Label.REPORTED_FRAUD.value
    )
    output = []
    for cluster_id in range(number_of_clusters):
        all_nearest = assigned[assigned["nearest_cluster_id"] == cluster_id]
        neighbourhood = all_nearest[all_nearest["within_fraud_neighbourhood"]]
        size = int(len(neighbourhood))
        fraud_count = int(neighbourhood["is_reported_fraud"].sum())
        raw_rate = fraud_count / size if size else 0.0
        smoothed_rate = (fraud_count + 1) / (size + 2)
        statistic = {
            "cluster_id": cluster_id,
            "total_assigned_transactions": int(len(all_nearest)),
            "cluster_size": size,
            "reported_fraud_count": fraud_count,
            "reported_fraud_percentage": round(raw_rate * 100, 4),
            "smoothed_fraud_percentage": round(smoothed_rate * 100, 4),
            "fraud_rate_lower_bound": round(
                wilson_lower_bound(fraud_count, size) * 100, 4
            ),
        }
        statistic["predicted_label"] = risk_label(statistic)
        statistic["cluster_flagged"] = (
            statistic["predicted_label"] != Label.LEGITIMATE.value
        )
        output.append(statistic)
    return output
