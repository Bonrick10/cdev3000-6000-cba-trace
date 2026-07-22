"""Build, train, save and load the standalone small model."""

from __future__ import annotations

from typing import Any

import joblib
import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from small_config import (
    MODEL_FEATURES,
    SMALL_MODEL_PATH,
)


def build_small_model(
    number_of_clusters: int = 5,
) -> Pipeline:
    """Create the clustering pipeline."""

    if number_of_clusters < 2:
        raise ValueError(
            "number_of_clusters must be at least 2."
        )

    return Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="median"),
            ),
            (
                "scaler",
                StandardScaler(),
            ),
            (
                "clusterer",
                MiniBatchKMeans(
                    n_clusters=number_of_clusters,
                    batch_size=1024,
                    n_init=10,
                    max_iter=300,
                    random_state=42,
                ),
            ),
        ]
    )


def validate_training_data(
    training_data: pd.DataFrame,
    number_of_clusters: int,
) -> None:
    """Validate the transaction data before training."""

    if training_data.empty:
        raise ValueError(
            "Training data is empty."
        )

    required_columns = [
        *MODEL_FEATURES,
        "transaction_id",
        "transaction_time",
        "confirmed_fraud",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in training_data.columns
    ]

    if missing_columns:
        raise ValueError(
            "Training data is missing columns: "
            f"{missing_columns}"
        )

    if len(training_data) < number_of_clusters:
        raise ValueError(
            "The number of transactions must be at least "
            "equal to the number of clusters."
        )


def determine_cluster_risk(
    cluster: pd.Series,
) -> str:
    """Assign a risk level using confirmed labels."""

    confirmed_count = int(
        cluster["confirmed_count"]
    )

    fraud_count = int(
        cluster["confirmed_fraud_count"]
    )

    fraud_rate = float(
        cluster["smoothed_fraud_rate"]
    )

    if confirmed_count < 2:
        return "insufficient_data"

    if fraud_count >= 2 and fraud_rate >= 0.80:
        return "critical"

    if fraud_count >= 2 and fraud_rate >= 0.50:
        return "high"

    if fraud_count >= 1 and fraud_rate >= 0.30:
        return "medium"

    return "low"


def calculate_cluster_statistics(
    clustered_data: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate confirmed fraud statistics for each cluster."""

    result = clustered_data.copy()

    result["confirmed_fraud"] = pd.to_numeric(
        result["confirmed_fraud"],
        errors="coerce",
    )

    all_clusters = (
        result.groupby("cluster_id")
        .size()
        .rename("transaction_count")
        .reset_index()
    )

    confirmed_data = result[
        result["confirmed_fraud"].isin([0, 1])
    ].copy()

    confirmed_statistics = (
        confirmed_data.groupby("cluster_id")
        .agg(
            confirmed_count=(
                "confirmed_fraud",
                "size",
            ),
            confirmed_fraud_count=(
                "confirmed_fraud",
                "sum",
            ),
        )
        .reset_index()
    )

    statistics = all_clusters.merge(
        confirmed_statistics,
        on="cluster_id",
        how="left",
    )

    count_columns = [
        "confirmed_count",
        "confirmed_fraud_count",
    ]

    statistics[count_columns] = (
        statistics[count_columns]
        .fillna(0)
        .astype(int)
    )

    statistics["confirmed_legitimate_count"] = (
        statistics["confirmed_count"]
        - statistics["confirmed_fraud_count"]
    )

    statistics["raw_fraud_rate"] = (
        statistics["confirmed_fraud_count"]
        / statistics["confirmed_count"].replace(
            0,
            pd.NA,
        )
    ).fillna(0.0)

    statistics["smoothed_fraud_rate"] = (
        statistics["confirmed_fraud_count"] + 1
    ) / (
        statistics["confirmed_count"] + 2
    )

    statistics["risk_level"] = statistics.apply(
        determine_cluster_risk,
        axis=1,
    )

    action_mapping = {
        "insufficient_data": "review",
        "low": "approve",
        "medium": "step_up_authentication",
        "high": "review",
        "critical": "block",
    }

    statistics["recommended_action"] = (
        statistics["risk_level"].map(
            action_mapping
        )
    )

    return statistics.sort_values(
        "cluster_id"
    ).reset_index(drop=True)


def train_small_model(
    training_data: pd.DataFrame,
    number_of_clusters: int = 5,
) -> tuple[
    Pipeline,
    pd.DataFrame,
    dict[str, Any],
]:
    """Train the small clustering model."""

    validate_training_data(
        training_data=training_data,
        number_of_clusters=number_of_clusters,
    )

    features = training_data[
        MODEL_FEATURES
    ].copy()

    model = build_small_model(
        number_of_clusters=number_of_clusters
    )

    cluster_ids = model.fit_predict(
        features
    )

    clustered_data = training_data.copy()
    clustered_data["cluster_id"] = cluster_ids

    cluster_statistics = calculate_cluster_statistics(
        clustered_data
    )

    metadata = {
        "number_of_training_rows": int(
            len(training_data)
        ),
        "number_of_clusters": int(
            number_of_clusters
        ),
        "training_start": str(
            training_data["transaction_time"].min()
        ),
        "training_end": str(
            training_data["transaction_time"].max()
        ),
    }

    return (
        model,
        cluster_statistics,
        metadata,
    )


def save_small_model_bundle(
    model: Pipeline,
    cluster_statistics: pd.DataFrame,
    metadata: dict[str, Any],
) -> None:
    """Save the trained model and cluster statistics."""

    SMALL_MODEL_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    bundle = {
        "model": model,
        "feature_columns": MODEL_FEATURES,
        "cluster_statistics": (
            cluster_statistics.to_dict(
                orient="records"
            )
        ),
        "metadata": metadata,
    }

    joblib.dump(
        bundle,
        SMALL_MODEL_PATH,
    )


def load_small_model_bundle() -> dict[str, Any]:
    """Load the trained small model."""

    if not SMALL_MODEL_PATH.exists():
        raise FileNotFoundError(
            f"No model exists at {SMALL_MODEL_PATH}. "
            "Train the model first."
        )

    return joblib.load(
        SMALL_MODEL_PATH
    )