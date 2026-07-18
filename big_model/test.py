"""Evaluation functions for the big fraud model."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
)

from Handle_data import MODEL_FEATURES


LABEL_ORDER = [
    "legitimate",
    "unusual",
    "suspicious",
]


def get_class_probability(
    model,
    probabilities: np.ndarray,
    class_name: str,
) -> np.ndarray:
    """Get one class probability, or zeros if class was absent."""

    classes = list(model.named_steps["classifier"].classes_)

    if class_name not in classes:
        return np.zeros(len(probabilities))

    class_index = classes.index(class_name)

    return probabilities[:, class_index]


def calculate_risk_scores(model, X: pd.DataFrame) -> np.ndarray:
    """
    Convert class probabilities into a 0-100 fraud-risk score.

    unusual receives partial risk weight;
    suspicious receives full risk weight.
    """

    probabilities = model.predict_proba(X)

    unusual_probability = get_class_probability(
        model,
        probabilities,
        "unusual",
    )

    suspicious_probability = get_class_probability(
        model,
        probabilities,
        "suspicious",
    )

    risk_score = (
        0.50 * unusual_probability
        + 1.00 * suspicious_probability
    ) * 100

    return risk_score


def evaluate_model(
    model,
    evaluation_data: pd.DataFrame,
    print_results: bool = True,
) -> dict[str, Any]:
    """Evaluate the model on unseen chronological data."""

    X_test = evaluation_data[MODEL_FEATURES]
    y_test = evaluation_data["model_label"]

    predicted_labels = model.predict(X_test)
    probabilities = model.predict_proba(X_test)

    classes = list(model.named_steps["classifier"].classes_)

    report = classification_report(
        y_test,
        predicted_labels,
        labels=LABEL_ORDER,
        output_dict=True,
        zero_division=0,
    )

    matrix = confusion_matrix(
        y_test,
        predicted_labels,
        labels=LABEL_ORDER,
    )

    risk_scores = calculate_risk_scores(model, X_test)

    actual_fraud_like = (
        y_test == "suspicious"
    ).astype(int)

    predicted_fraud_like = (
        risk_scores >= 70
    ).astype(int)

    metrics = {
        "number_of_transactions": int(len(evaluation_data)),
        "accuracy": float(
            accuracy_score(y_test, predicted_labels)
        ),
        "macro_f1": float(
            f1_score(
                y_test,
                predicted_labels,
                average="macro",
                zero_division=0,
            )
        ),
        "suspicious_precision": float(
            precision_score(
                actual_fraud_like,
                predicted_fraud_like,
                zero_division=0,
            )
        ),
        "suspicious_recall": float(
            recall_score(
                actual_fraud_like,
                predicted_fraud_like,
                zero_division=0,
            )
        ),
        "false_positive_count": int(
            (
                (actual_fraud_like == 0)
                & (predicted_fraud_like == 1)
            ).sum()
        ),
        "false_negative_count": int(
            (
                (actual_fraud_like == 1)
                & (predicted_fraud_like == 0)
            ).sum()
        ),
        "classification_report": report,
        "confusion_matrix": matrix.tolist(),
        "classes": classes,
    }

    if len(set(y_test).intersection(classes)) > 1:
        try:
            metrics["log_loss"] = float(
                log_loss(
                    y_test,
                    probabilities,
                    labels=classes,
                )
            )
        except ValueError:
            metrics["log_loss"] = None
    else:
        metrics["log_loss"] = None

    if print_results:
        print("\nClassification report")
        print(
            classification_report(
                y_test,
                predicted_labels,
                labels=LABEL_ORDER,
                zero_division=0,
            )
        )

        print("Confusion matrix")
        print(
            pd.DataFrame(
                matrix,
                index=[
                    f"actual_{label}"
                    for label in LABEL_ORDER
                ],
                columns=[
                    f"predicted_{label}"
                    for label in LABEL_ORDER
                ],
            )
        )

        print("\nModel-health summary")

        summary_keys = [
            "accuracy",
            "macro_f1",
            "suspicious_precision",
            "suspicious_recall",
            "false_positive_count",
            "false_negative_count",
            "log_loss",
        ]

        for key in summary_keys:
            print(f"{key}: {metrics[key]}")

    return metrics