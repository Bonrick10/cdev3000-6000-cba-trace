"""Train, evaluate, health-check and retrain the big fraud model."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from Handle_data import (
    START_DATE,
    chronological_split,
    create_features,
    get_maturity_cutoff,
    read_all_mature_transactions,
    read_transactions,
)
from test import evaluate_model
from train import (
    CURRENT_MODEL_PATH,
    load_model_bundle,
    save_model_bundle,
    train_model,
)


def train_initial_model(
    as_of_date: pd.Timestamp | None = None,
) -> None:
    """Train the model using all mature data and an 80/20 split."""

    raw_data, maturity_cutoff = read_all_mature_transactions(
        as_of_date
    )

    print(f"Raw mature transactions: {len(raw_data)}")
    print(f"Maturity cutoff: {maturity_cutoff}")

    feature_data = create_features(raw_data)

    print(f"Model-ready transactions: {len(feature_data)}")
    print("\nModel label counts:")
    print(feature_data["model_label"].value_counts())

    train_data, test_data = chronological_split(
        feature_data,
        train_fraction=0.80,
    )

    print(f"\nTraining rows: {len(train_data)}")
    print(f"Testing rows: {len(test_data)}")
    print(
        "Training period:",
        train_data["transaction_time"].min(),
        "to",
        train_data["transaction_time"].max(),
    )
    print(
        "Testing period:",
        test_data["transaction_time"].min(),
        "to",
        test_data["transaction_time"].max(),
    )

    model = train_model(train_data)

    print("\nEvaluating candidate model on chronological 20%...")
    metrics = evaluate_model(
        model,
        test_data,
        print_results=True,
    )

    metadata = {
        "training_data_start": str(
            feature_data["transaction_time"].min()
        ),
        "maturity_cutoff": str(maturity_cutoff),
        "training_rows": len(train_data),
        "testing_rows": len(test_data),
        "label_counts": (
            feature_data["model_label"]
            .value_counts()
            .to_dict()
        ),
        "test_metrics": metrics,
    }

    save_model_bundle(
        model=model,
        metadata=metadata,
    )

    print(
        f"\nModel saved to {CURRENT_MODEL_PATH}"
    )


def health_check_and_retrain(
    as_of_date: pd.Timestamp | None = None,
) -> None:
    """
    Test the existing model on newly matured data before retraining.

    Then retrain using all data up to the new maturity cutoff.
    """

    bundle = load_model_bundle()
    current_model = bundle["model"]
    old_metadata = bundle["metadata"]

    old_cutoff_value = old_metadata.get("maturity_cutoff")

    if not old_cutoff_value:
        raise ValueError(
            "Saved model has no maturity_cutoff metadata."
        )

    old_cutoff = pd.Timestamp(old_cutoff_value)

    if old_cutoff.tzinfo is None:
        old_cutoff = old_cutoff.tz_localize("UTC")
    else:
        old_cutoff = old_cutoff.tz_convert("UTC")

    new_cutoff = get_maturity_cutoff(as_of_date)

    if new_cutoff <= old_cutoff:
        print(
            "No newly matured period exists yet. "
            f"Old cutoff: {old_cutoff}; "
            f"new cutoff: {new_cutoff}"
        )
        return

    print(
        "Reading newly matured health window:",
        old_cutoff,
        "to",
        new_cutoff,
    )

    # Feature creation requires account history.
    # Read historical data plus the new window, then select the window.
    raw_data = read_transactions(
        START_DATE,
        new_cutoff,
    )

    all_features = create_features(raw_data)

    health_window = all_features[
        (
            all_features["transaction_time"] >= old_cutoff
        )
        & (
            all_features["transaction_time"] < new_cutoff
        )
    ].copy()

    if health_window.empty:
        print("No newly matured transactions were found.")
        return

    print(
        f"Health-window transactions: {len(health_window)}"
    )

    print(
        "\nTesting the OLD model on the newly matured window..."
    )

    health_metrics = evaluate_model(
        current_model,
        health_window,
        print_results=True,
    )

    health_path = Path("models") / (
        "health_"
        f"{old_cutoff.date()}_to_{new_cutoff.date()}.json"
    )

    health_path.parent.mkdir(parents=True, exist_ok=True)

    with health_path.open("w", encoding="utf-8") as file:
        json.dump(
            health_metrics,
            file,
            indent=2,
        )

    print(f"\nHealth results saved to {health_path}")

    print(
        "\nRetraining candidate model using all mature data..."
    )

    train_data, test_data = chronological_split(
        all_features,
        train_fraction=0.80,
    )

    candidate_model = train_model(train_data)

    candidate_metrics = evaluate_model(
        candidate_model,
        test_data,
        print_results=True,
    )

    metadata = {
        "training_data_start": str(
            all_features["transaction_time"].min()
        ),
        "maturity_cutoff": str(new_cutoff),
        "training_rows": len(train_data),
        "testing_rows": len(test_data),
        "label_counts": (
            all_features["model_label"]
            .value_counts()
            .to_dict()
        ),
        "old_model_health_metrics": health_metrics,
        "candidate_test_metrics": candidate_metrics,
    }

    save_model_bundle(
        model=candidate_model,
        metadata=metadata,
    )

    print(
        "\nNew model trained and promoted to "
        f"{CURRENT_MODEL_PATH}"
    )


def parse_args():
    parser = argparse.ArgumentParser(
        description="CBA TRACE big model"
    )

    parser.add_argument(
        "command",
        choices=[
            "train",
            "health-retrain",
        ],
        help=(
            "train: initial model training; "
            "health-retrain: test newly matured data then retrain"
        ),
    )

    parser.add_argument(
        "--as-of-date",
        default=None,
        help=(
            "Optional UTC model run date, e.g. 2026-07-16. "
            "Useful for repeatable testing."
        ),
    )

    return parser.parse_args()


def main():
    args = parse_args()

    as_of_date = None

    if args.as_of_date:
        as_of_date = pd.Timestamp(
            args.as_of_date,
            tz="UTC",
        )

    if args.command == "train":
        train_initial_model(as_of_date)

    elif args.command == "health-retrain":
        health_check_and_retrain(as_of_date)


if __name__ == "__main__":
    main()