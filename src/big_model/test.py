"""Evaluation utilities for the binary big fraud model."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)

from .handle_data import (
    MODEL_FEATURES,
)


def labels_from_probabilities(
    probabilities: np.ndarray,
    unusual_threshold: float = 0.70,
    suspicious_threshold: float = 0.90,
) -> np.ndarray:
    """Convert probabilities to operational labels."""

    if not (
        0
        <= unusual_threshold
        < suspicious_threshold
        <= 1
    ):
        raise ValueError(
            "Thresholds must satisfy "
            "0 <= unusual < suspicious <= 1."
        )

    return np.where(
        probabilities
        >= suspicious_threshold,
        "suspicious",
        np.where(
            probabilities
            >= unusual_threshold,
            "unusual",
            "legitimate",
        ),
    )


def evaluate_model(
    model,
    evaluation_data: pd.DataFrame,
    unusual_threshold: float = 0.70,
    suspicious_threshold: float = 0.90,
    print_results: bool = True,
) -> dict[str, Any]:
    """Evaluate probabilities and operational labels."""

    if evaluation_data.empty:
        raise ValueError(
            "Evaluation data is empty."
        )

    X_test = evaluation_data[
        MODEL_FEATURES
    ]

    y_test = (
        evaluation_data["target"]
        .astype(int)
        .to_numpy()
    )

    fraud_probabilities = (
        model.predict_proba(
            X_test
        )[:, 1]
    )

    binary_predictions = (
        fraud_probabilities
        >= unusual_threshold
    ).astype(int)

    operational_labels = (
        labels_from_probabilities(
            fraud_probabilities,
            unusual_threshold,
            suspicious_threshold,
        )
    )

    matrix = confusion_matrix(
        y_test,
        binary_predictions,
        labels=[0, 1],
    )

    metrics: dict[str, Any] = {
        "number_of_transactions":
            int(len(evaluation_data)),

        "unusual_threshold":
            unusual_threshold,

        "suspicious_threshold":
            suspicious_threshold,

        "accuracy":
            float(
                accuracy_score(
                    y_test,
                    binary_predictions,
                )
            ),

        "f1":
            float(
                f1_score(
                    y_test,
                    binary_predictions,
                    zero_division=0,
                )
            ),

        "fraud_precision":
            float(
                precision_score(
                    y_test,
                    binary_predictions,
                    zero_division=0,
                )
            ),

        "fraud_recall":
            float(
                recall_score(
                    y_test,
                    binary_predictions,
                    zero_division=0,
                )
            ),

        "false_positive_count":
            int(
                (
                    (y_test == 0)
                    & (
                        binary_predictions
                        == 1
                    )
                ).sum()
            ),

        "false_negative_count":
            int(
                (
                    (y_test == 1)
                    & (
                        binary_predictions
                        == 0
                    )
                ).sum()
            ),

        "confusion_matrix":
            matrix.tolist(),

        "log_loss":
            float(
                log_loss(
                    y_test,
                    fraud_probabilities,
                    labels=[0, 1],
                )
            ),

        "operational_label_counts": {
            label: int(
                (
                    operational_labels
                    == label
                ).sum()
            )
            for label in [
                "legitimate",
                "unusual",
                "suspicious",
            ]
        },
    }

    if (
        len(np.unique(y_test))
        == 2
    ):
        metrics["roc_auc"] = float(
            roc_auc_score(
                y_test,
                fraud_probabilities,
            )
        )

        metrics[
            "average_precision"
        ] = float(
            average_precision_score(
                y_test,
                fraud_probabilities,
            )
        )
    else:
        metrics["roc_auc"] = None
        metrics[
            "average_precision"
        ] = None

    if print_results:
        print(
            "\nBinary classification report"
        )

        print(
            classification_report(
                y_test,
                binary_predictions,
                target_names=[
                    "mature_non_fraud",
                    "mature_fraud",
                ],
                zero_division=0,
            )
        )

        print(
            "Confusion matrix "
            "[[TN, FP], [FN, TP]]"
        )

        print(matrix)

        print("\nMetrics")

        for key, value in (
            metrics.items()
        ):
            print(
                f"{key}: {value}"
            )

    return metrics