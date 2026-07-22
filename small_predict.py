"""Assign incoming transactions to trained fraud clusters."""

from __future__ import annotations

from typing import Any

import pandas as pd

from small_train import load_small_model_bundle


def find_cluster_statistics(
    cluster_id: int,
    statistics: list[dict[str, Any]],
) -> dict[str, Any]:
    """Find statistics for one cluster."""

    for cluster in statistics:
        if int(cluster["cluster_id"]) == cluster_id:
            return cluster

    return {
        "cluster_id": cluster_id,
        "transaction_count": 0,
        "confirmed_count": 0,
        "confirmed_fraud_count": 0,
        "confirmed_legitimate_count": 0,
        "raw_fraud_rate": 0.0,
        "smoothed_fraud_rate": 0.0,
        "risk_level": "insufficient_data",
        "recommended_action": "review",
    }


def predict_cluster(
    feature_data: pd.DataFrame,
) -> dict[str, Any]:
    """Assign one transaction to its nearest cluster."""

    if len(feature_data) != 1:
        raise ValueError(
            "predict_cluster expects exactly one transaction."
        )

    bundle = load_small_model_bundle()

    model = bundle["model"]
    feature_columns = bundle["feature_columns"]

    missing_features = [
        feature
        for feature in feature_columns
        if feature not in feature_data.columns
    ]

    if missing_features:
        raise ValueError(
            "Incoming transaction is missing features: "
            f"{missing_features}"
        )

    cluster_id = int(
        model.predict(
            feature_data[feature_columns]
        )[0]
    )

    cluster = find_cluster_statistics(
        cluster_id=cluster_id,
        statistics=bundle["cluster_statistics"],
    )

    return {
        "cluster_id": cluster_id,
        "cluster_transaction_count": int(
            cluster["transaction_count"]
        ),
        "confirmed_count": int(
            cluster["confirmed_count"]
        ),
        "confirmed_fraud_count": int(
            cluster["confirmed_fraud_count"]
        ),
        "confirmed_legitimate_count": int(
            cluster["confirmed_legitimate_count"]
        ),
        "raw_cluster_fraud_rate": round(
            float(cluster["raw_fraud_rate"]),
            4,
        ),
        "smoothed_cluster_fraud_rate": round(
            float(cluster["smoothed_fraud_rate"]),
            4,
        ),
        "cluster_risk_level": cluster[
            "risk_level"
        ],
        "recommended_action": cluster[
            "recommended_action"
        ],
    }


def predict_multiple_clusters(
    feature_data: pd.DataFrame,
) -> pd.DataFrame:
    """Assign multiple transactions to clusters."""

    if feature_data.empty:
        raise ValueError(
            "Incoming transaction data is empty."
        )

    bundle = load_small_model_bundle()

    model = bundle["model"]
    feature_columns = bundle["feature_columns"]

    missing_features = [
        feature
        for feature in feature_columns
        if feature not in feature_data.columns
    ]

    if missing_features:
        raise ValueError(
            "Incoming transaction data is missing features: "
            f"{missing_features}"
        )

    cluster_ids = model.predict(
        feature_data[feature_columns]
    )

    predictions = []

    for cluster_id in cluster_ids:
        cluster = find_cluster_statistics(
            cluster_id=int(cluster_id),
            statistics=bundle["cluster_statistics"],
        )

        predictions.append(
            {
                "cluster_id": int(cluster_id),
                "cluster_transaction_count": int(
                    cluster["transaction_count"]
                ),
                "confirmed_count": int(
                    cluster["confirmed_count"]
                ),
                "confirmed_fraud_count": int(
                    cluster["confirmed_fraud_count"]
                ),
                "cluster_fraud_rate": float(
                    cluster["smoothed_fraud_rate"]
                ),
                "cluster_risk_level": cluster[
                    "risk_level"
                ],
                "recommended_action": cluster[
                    "recommended_action"
                ],
            }
        )

    return pd.DataFrame(
        predictions
    )