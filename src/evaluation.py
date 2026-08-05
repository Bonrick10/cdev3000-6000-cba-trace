"""Leakage-safe, read-only evaluation of the integrated model pipeline."""

from __future__ import annotations

from typing import Any, Dict, Iterable

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from src.big_model.predict import probability_to_label
from src.big_model.train import (
    chronological_split,
    fit_model,
    maturity_cutoff,
    prepare_training_data,
)
from src.features import MODEL_FEATURES
from src.features.data import read_historical_transactions
from src.label import Label
from src.settings import (
    SMALL_MODEL_MIN_CLUSTER_SIZE,
    SMALL_MODEL_MIN_FRAUD_COUNT,
)
from src.small_model.statistics import assignment_details
from src.small_model.train import fit_small_model, prepare_population

SEVERITY = {
    Label.LEGITIMATE.value: 0,
    Label.UNUSUAL.value: 1,
    Label.SUSPICIOUS.value: 2,
}


def _binary_metrics(
    target: np.ndarray, selected: np.ndarray, amounts: np.ndarray
) -> Dict[str, Any]:
    matrix = confusion_matrix(target, selected, labels=[0, 1])
    tn, fp, fn, tp = (int(value) for value in matrix.ravel())
    return {
        "signals": int(selected.sum()),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "precision": float(precision_score(target, selected, zero_division=0)),
        "recall": float(recall_score(target, selected, zero_division=0)),
        "f1": float(f1_score(target, selected, zero_division=0)),
        "false_positive_rate": float(fp / (fp + tn)) if fp + tn else 0.0,
        "fraud_value_captured": float(amounts[(target == 1) & (selected == 1)].sum()),
    }


def _labels_at_least(labels: Iterable[str], minimum: str) -> np.ndarray:
    threshold = SEVERITY[minimum]
    return np.asarray([SEVERITY[label] >= threshold for label in labels], dtype=int)


def _worst_labels(big_labels: Iterable[str], small_labels: Iterable[str]) -> list[str]:
    return [
        big if SEVERITY[big] >= SEVERITY[small] else small
        for big, small in zip(big_labels, small_labels)
    ]


def _fixed_budget_metrics(
    target: np.ndarray,
    amounts: np.ndarray,
    scores: np.ndarray,
    budgets: Iterable[int] = (100, 200, 500, 1_000, 2_000),
) -> Dict[str, Any]:
    order = np.argsort(-scores, kind="stable")
    output = {}
    for requested in budgets:
        budget = min(int(requested), len(target))
        selected = order[:budget]
        frauds = int(target[selected].sum())
        output[str(requested)] = {
            "alerts": budget,
            "fraud_captured": frauds,
            "precision": frauds / budget if budget else 0.0,
            "fraud_value_captured": float(
                amounts[selected][target[selected] == 1].sum()
            ),
        }
    return output


def evaluate_from_database(db=None) -> Dict[str, Any]:
    """Fit in memory and evaluate hidden truth without persisting model artifacts."""
    raw = read_historical_transactions(db=db)
    if raw.empty:
        raise ValueError("The historical transaction snapshot is empty.")
    as_of = pd.to_datetime(raw["transaction_time"], utc=True).max()

    mature_raw = raw[
        pd.to_datetime(raw["transaction_time"], utc=True) < maturity_cutoff(as_of)
    ]
    mature = prepare_training_data(mature_raw)
    train, validation = chronological_split(mature)
    candidate = fit_model(train)
    from src.big_model.evaluate import evaluate_model

    validation_metrics = evaluate_model(candidate, validation)
    big_model = fit_model(mature)

    window = prepare_population(raw, as_of.to_pydatetime())
    small_bundle = fit_small_model(window)
    evaluation = window[
        window["observed_label"] != Label.REPORTED_FRAUD.value
    ].copy()
    evaluation["target"] = (
        evaluation["original_label"] == Label.CONFIRMED_FRAUDULENT.value
    ).astype(int)
    target = evaluation["target"].to_numpy()

    probabilities = big_model.predict_proba(evaluation[MODEL_FEATURES])[:, 1]
    big_labels = [probability_to_label(float(value)) for value in probabilities]
    transformed = small_bundle["preprocessor"].transform(evaluation[MODEL_FEATURES])
    clusters, _, _, accepted = assignment_details(
        transformed,
        small_bundle["clusterer"],
        small_bundle["distance_limits"],
    )
    cluster_labels = {
        int(item["cluster_id"]): item["predicted_label"]
        for item in small_bundle["cluster_statistics"]
    }
    small_labels = [
        cluster_labels[int(cluster_id)] if within else Label.LEGITIMATE.value
        for cluster_id, within in zip(clusters, accepted)
    ]
    combined_labels = _worst_labels(big_labels, small_labels)
    amounts = evaluation["amount"].to_numpy(dtype=float)
    statistic_by_cluster = {
        int(item["cluster_id"]): item
        for item in small_bundle["cluster_statistics"]
    }
    small_report_scores = np.asarray(
        [
            float(statistic_by_cluster[int(cluster_id)]["smoothed_fraud_percentage"])
            / 100
            if within
            else 0.0
            for cluster_id, within in zip(clusters, accepted)
        ]
    )

    results: Dict[str, Any] = {
        "data": {
            "as_of": as_of.isoformat(),
            "maturity_cutoff": maturity_cutoff(as_of).isoformat(),
            "mature_rows": int(len(mature)),
            "small_model_window_rows": int(len(window)),
            "evaluation_rows": int(len(evaluation)),
            "hidden_fraud_rows": int(target.sum()),
        },
        "big_model_validation": validation_metrics,
        "small_model": {
            "metadata": small_bundle["metadata"],
            "cluster_statistics": small_bundle["cluster_statistics"],
        },
        "operational": {},
        "threshold_sensitivity": {},
    }
    for level, minimum in (
        ("alerts", Label.SUSPICIOUS.value),
        ("elevated_risk", Label.UNUSUAL.value),
    ):
        results["operational"][level] = {
            "big_model": _binary_metrics(
                target, _labels_at_least(big_labels, minimum), amounts
            ),
            "small_model": _binary_metrics(
                target, _labels_at_least(small_labels, minimum), amounts
            ),
            "combined": _binary_metrics(
                target, _labels_at_least(combined_labels, minimum), amounts
            ),
        }

    both_classes = len(set(target)) == 2
    results["big_model_recent_ranking"] = {
        "roc_auc": float(roc_auc_score(target, probabilities))
        if both_classes
        else None,
        "average_precision": float(average_precision_score(target, probabilities))
        if both_classes
        else None,
    }
    for threshold in (0.05, 0.075, 0.10, 0.125, 0.15):
        threshold_labels = []
        for cluster_id, within in zip(clusters, accepted):
            statistic = statistic_by_cluster[int(cluster_id)]
            supported = (
                int(statistic["cluster_size"]) >= SMALL_MODEL_MIN_CLUSTER_SIZE
                and int(statistic["reported_fraud_count"])
                >= SMALL_MODEL_MIN_FRAUD_COUNT
            )
            rate = float(statistic["smoothed_fraud_percentage"]) / 100
            lower = float(statistic["fraud_rate_lower_bound"]) / 100
            suspicious = (
                within
                and supported
                and rate >= threshold
                and lower >= threshold * 0.8
            )
            threshold_labels.append(
                Label.SUSPICIOUS.value if suspicious else Label.LEGITIMATE.value
            )
        combined_at_threshold = _worst_labels(big_labels, threshold_labels)
        results["threshold_sensitivity"][f"{threshold:.3f}"] = {
            "small_model": _binary_metrics(
                target,
                _labels_at_least(threshold_labels, Label.SUSPICIOUS.value),
                amounts,
            ),
            "combined": _binary_metrics(
                target,
                _labels_at_least(combined_at_threshold, Label.SUSPICIOUS.value),
                amounts,
            ),
        }

    big_budget_score = (
        np.asarray([SEVERITY[label] for label in big_labels]) + probabilities
    )
    combined_budget_score = np.maximum(
        big_budget_score,
        np.asarray([SEVERITY[label] for label in small_labels])
        + small_report_scores,
    )
    results["fixed_alert_budgets"] = {
        "big_model": _fixed_budget_metrics(
            target, amounts, big_budget_score
        ),
        "combined": _fixed_budget_metrics(
            target, amounts, combined_budget_score
        ),
        "ranking_note": (
            "Severity is ranked first, then big-model probability; small-model "
            "report concentration breaks combined-model risk ties."
        ),
    }
    return results


def format_evaluation(results: Dict[str, Any]) -> str:
    """Render a compact stakeholder-readable terminal report."""
    data = results["data"]
    lines = [
        "INTEGRATED FRAUD PIPELINE EVALUATION",
        "=" * 37,
        f"As of:                 {data['as_of']}",
        f"Mature rows:           {data['mature_rows']:,}",
        f"60-day window rows:    {data['small_model_window_rows']:,}",
        f"Hidden evaluation set: {data['evaluation_rows']:,} "
        f"({data['hidden_fraud_rows']:,} fraud)",
        "",
        "BIG MODEL — CHRONOLOGICAL 80/20 VALIDATION",
        "-" * 45,
    ]
    validation = results["big_model_validation"]
    lines.extend(
        [
            f"Precision: {validation['fraud_precision']:.2%}",
            f"Recall:    {validation['fraud_recall']:.2%}",
            f"F1:        {validation['f1']:.3f}",
            f"ROC-AUC:   {validation['roc_auc']:.3f}",
            "",
            "SMALL MODEL — REPORTED-FRAUD CLUSTERS",
            "-" * 41,
        ]
    )
    metadata = results["small_model"]["metadata"]
    lines.append(
        f"Seeds: {metadata['reported_fraud_training_rows']:,} | "
        f"Clusters: {metadata['number_of_clusters']} | "
        f"Accepted: {metadata['accepted_population_rows']:,}"
    )
    for cluster in results["small_model"]["cluster_statistics"]:
        lines.append(
            f"Cluster {cluster['cluster_id']}: {cluster['predicted_label']} | "
            f"support {cluster['cluster_size']:,} | reports "
            f"{cluster['reported_fraud_count']:,} "
            f"({cluster['reported_fraud_percentage']:.2f}%) | "
            f"Wilson lower {cluster['fraud_rate_lower_bound']:.2f}%"
        )
    lines.extend(["", "OPERATIONAL COMPARISON", "-" * 22])
    comparison_levels = (
        ("alerts", "Suspicious alerts"),
        ("elevated_risk", "Unusual + suspicious"),
    )
    for level, title in comparison_levels:
        lines.append(title)
        for model_name in ("big_model", "small_model", "combined"):
            metric = results["operational"][level][model_name]
            lines.append(
                f"  {model_name.replace('_', ' ').title():12} "
                f"signals {metric['signals']:>5,} | "
                f"fraud {metric['true_positives']:>4,} | "
                f"precision {metric['precision']:.2%} | "
                f"recall {metric['recall']:.2%} | "
                f"FPR {metric['false_positive_rate']:.2%} | "
                f"fraud value ${metric['fraud_value_captured']:,.2f}"
            )
    lines.extend(["", "SUSPICIOUS-THRESHOLD SENSITIVITY", "-" * 34])
    for threshold, comparison in results["threshold_sensitivity"].items():
        combined = comparison["combined"]
        lines.append(
            f"{float(threshold):>5.1%} report rate | "
            f"alerts {combined['signals']:>5,} | "
            f"fraud {combined['true_positives']:>4,} | "
            f"precision {combined['precision']:.2%} | recall {combined['recall']:.2%}"
        )
    lines.extend(["", "EQUAL REVIEW BUDGET (TOP-K)", "-" * 27])
    for budget, big in results["fixed_alert_budgets"]["big_model"].items():
        combined = results["fixed_alert_budgets"]["combined"][budget]
        lines.append(
            f"{int(budget):>5,} reviewed | big {big['fraud_captured']:>4,} fraud | "
            f"combined {combined['fraud_captured']:>4,} fraud"
        )
    return "\n".join(lines)
