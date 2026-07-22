"""Update cluster statistics using confirmed feedback."""

from __future__ import annotations

from typing import Any

import joblib
import pandas as pd

from small_config import SMALL_MODEL_PATH
from small_train import (
    determine_cluster_risk,
    load_small_model_bundle,
)


ACTION_MAPPING = {
    "insufficient_data": "review",
    "low": "approve",
    "medium": "step_up_authentication",
    "high": "review",
    "critical": "block",
}


def update_cluster_feedback(
    cluster_id: int,
    confirmed_fraud: bool,
) -> dict[str, Any]:
    """
    Update cluster statistics after confirmed feedback.

    Call this only once for each confirmed transaction.
    """

    bundle = load_small_model_bundle()

    statistics = pd.DataFrame(
        bundle["cluster_statistics"]
    )

    matching_cluster = (
        statistics["cluster_id"].astype(int)
        == int(cluster_id)
    )

    if not matching_cluster.any():
        raise ValueError(
            f"Cluster {cluster_id} does not exist."
        )

    row_index = statistics.index[
        matching_cluster
    ][0]

    statistics.loc[
        row_index,
        "confirmed_count",
    ] += 1

    if confirmed_fraud:
        statistics.loc[
            row_index,
            "confirmed_fraud_count",
        ] += 1
    else:
        statistics.loc[
            row_index,
            "confirmed_legitimate_count",
        ] += 1

    confirmed_count = int(
        statistics.loc[
            row_index,
            "confirmed_count",
        ]
    )

    fraud_count = int(
        statistics.loc[
            row_index,
            "confirmed_fraud_count",
        ]
    )

    raw_fraud_rate = (
        fraud_count / confirmed_count
        if confirmed_count > 0
        else 0.0
    )

    smoothed_fraud_rate = (
        fraud_count + 1
    ) / (
        confirmed_count + 2
    )

    statistics.loc[
        row_index,
        "raw_fraud_rate",
    ] = raw_fraud_rate

    statistics.loc[
        row_index,
        "smoothed_fraud_rate",
    ] = smoothed_fraud_rate

    cluster_row = statistics.loc[
        row_index
    ]

    risk_level = determine_cluster_risk(
        cluster_row
    )

    recommended_action = (
        ACTION_MAPPING[risk_level]
    )

    statistics.loc[
        row_index,
        "risk_level",
    ] = risk_level

    statistics.loc[
        row_index,
        "recommended_action",
    ] = recommended_action

    bundle["cluster_statistics"] = (
        statistics.to_dict(
            orient="records"
        )
    )

    joblib.dump(
        bundle,
        SMALL_MODEL_PATH,
    )

    return {
        "cluster_id": int(cluster_id),
        "confirmed_count": confirmed_count,
        "confirmed_fraud_count": fraud_count,
        "raw_fraud_rate": round(
            raw_fraud_rate,
            4,
        ),
        "smoothed_fraud_rate": round(
            smoothed_fraud_rate,
            4,
        ),
        "risk_level": risk_level,
        "recommended_action": recommended_action,
    }