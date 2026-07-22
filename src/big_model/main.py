"""Train, evaluate, health-check and retrain the big fraud model."""

from __future__ import annotations

import argparse
import json

import pandas as pd

from .handle_data import (
    MATURE_LABEL_MAPPING,
    START_DATE,
    chronological_split,
    create_features,
    get_maturity_cutoff,
    read_all_mature_transactions,
    read_transactions,
)

from .test import (
    evaluate_model,
)

from .train import (
    CURRENT_MODEL_PATH,
    load_model_bundle,
    save_model_bundle,
    train_model,
)


def get_target_counts(
    dataframe: pd.DataFrame,
) -> dict[str, int]:
    """Return target counts that can be saved as JSON."""

    return {
        str(key): int(value)
        for key, value
        in dataframe[
            "target"
        ].value_counts().items()
    }


def train_initial_model(
    as_of_date: pd.Timestamp | None = None,
) -> None:
    """Train using transactions older than two months."""

    raw_data, maturity_cutoff = (
        read_all_mature_transactions(
            as_of_date
        )
    )

    model_data = create_features(
        raw_data
    )

    if model_data.empty:
        raise ValueError(
            "No mature labelled "
            "transactions were found."
        )

    train_data, test_data = (
        chronological_split(
            model_data,
            train_fraction=0.80,
        )
    )

    if (
        train_data[
            "target"
        ].nunique()
        != 2
    ):
        raise ValueError(
            "The chronological training "
            "portion does not contain "
            "both target classes."
        )

    print(
        "Historical transactions: "
        f"{len(raw_data)}"
    )

    print(
        "Mature model rows: "
        f"{len(model_data)}"
    )

    print(
        "Maturity cutoff: "
        f"{maturity_cutoff}"
    )

    print(
        "\nTarget counts "
        "(0=non-fraud, 1=fraud)"
    )

    print(
        model_data[
            "target"
        ]
        .value_counts()
        .sort_index()
    )

    print(
        "\nTraining period:"
    )

    print(
        train_data[
            "transaction_time"
        ].min(),
        "to",
        train_data[
            "transaction_time"
        ].max(),
    )

    print(
        "\nTesting period:"
    )

    print(
        test_data[
            "transaction_time"
        ].min(),
        "to",
        test_data[
            "transaction_time"
        ].max(),
    )

    model = train_model(
        train_data
    )

    metrics = evaluate_model(
        model,
        test_data,
        print_results=True,
    )

    metadata = {
        "training_data_start":
            str(
                model_data[
                    "transaction_time"
                ].min()
            ),

        "maturity_cutoff":
            str(
                maturity_cutoff
            ),

        "training_rows":
            int(
                len(train_data)
            ),

        "testing_rows":
            int(
                len(test_data)
            ),

        "target_counts":
            get_target_counts(
                model_data
            ),

        "mature_label_mapping":
            MATURE_LABEL_MAPPING,

        "test_metrics":
            metrics,
    }

    save_model_bundle(
        model,
        metadata,
    )

    print(
        "\nModel saved to "
        f"{CURRENT_MODEL_PATH}"
    )


def health_check_and_retrain(
    as_of_date: pd.Timestamp | None = None,
) -> None:
    """
    Evaluate the old model on newly matured data,
    then retrain using all mature data.
    """

    bundle = load_model_bundle()

    current_model = bundle[
        "model"
    ]

    old_cutoff_value = bundle[
        "metadata"
    ].get(
        "maturity_cutoff"
    )

    if old_cutoff_value is None:
        raise ValueError(
            "Saved model has no "
            "maturity cutoff."
        )

    old_cutoff = pd.Timestamp(
        old_cutoff_value
    )

    if old_cutoff.tzinfo is None:
        old_cutoff = (
            old_cutoff
            .tz_localize("UTC")
        )
    else:
        old_cutoff = (
            old_cutoff
            .tz_convert("UTC")
        )

    new_cutoff = get_maturity_cutoff(
        as_of_date
    )

    if new_cutoff <= old_cutoff:
        print(
            "No newly matured period "
            "is available."
        )
        return

    raw_history = read_transactions(
        START_DATE,
        new_cutoff,
    )

    all_features = create_features(
        raw_history
    )

    health_window = all_features[
        (
            all_features[
                "transaction_time"
            ]
            >= old_cutoff
        )
        & (
            all_features[
                "transaction_time"
            ]
            < new_cutoff
        )
    ].copy()

    if health_window.empty:
        print(
            "No newly matured "
            "transactions were found."
        )
        return

    print(
        "\nOld-model health on "
        "newly matured transactions"
    )

    health_metrics = evaluate_model(
        current_model,
        health_window,
        print_results=True,
    )

    health_path = (
        CURRENT_MODEL_PATH.parent
        / (
            "health_"
            f"{old_cutoff.date()}"
            "_to_"
            f"{new_cutoff.date()}"
            ".json"
        )
    )

    with health_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            health_metrics,
            file,
            indent=2,
        )

    train_data, test_data = (
        chronological_split(
            all_features,
            train_fraction=0.80,
        )
    )

    if (
        train_data[
            "target"
        ].nunique()
        != 2
    ):
        raise ValueError(
            "The updated training "
            "portion does not contain "
            "both target classes."
        )

    candidate_model = train_model(
        train_data
    )

    print(
        "\nCandidate-model evaluation"
    )

    candidate_metrics = evaluate_model(
        candidate_model,
        test_data,
        print_results=True,
    )

    metadata = {
        "training_data_start":
            str(
                all_features[
                    "transaction_time"
                ].min()
            ),

        "maturity_cutoff":
            str(
                new_cutoff
            ),

        "training_rows":
            int(
                len(train_data)
            ),

        "testing_rows":
            int(
                len(test_data)
            ),

        "target_counts":
            get_target_counts(
                all_features
            ),

        "mature_label_mapping":
            MATURE_LABEL_MAPPING,

        "old_model_health_metrics":
            health_metrics,

        "candidate_test_metrics":
            candidate_metrics,
    }

    save_model_bundle(
        candidate_model,
        metadata,
    )

    print(
        "\nNew model promoted to "
        f"{CURRENT_MODEL_PATH}"
    )


def parse_args() -> argparse.Namespace:
    """Read command-line arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "TRACE mature-label "
            "big fraud model"
        )
    )

    parser.add_argument(
        "command",
        choices=[
            "train",
            "health-retrain",
        ],
    )

    parser.add_argument(
        "--as-of-date",
        default=None,
        help=(
            "Optional UTC run date, "
            "for example 2026-07-22."
        ),
    )

    return parser.parse_args()


def main() -> None:
    """Run the selected command."""

    args = parse_args()

    if args.as_of_date:
        as_of_date = pd.Timestamp(
            args.as_of_date,
            tz="UTC",
        )
    else:
        as_of_date = None

    if args.command == "train":
        train_initial_model(
            as_of_date
        )
    else:
        health_check_and_retrain(
            as_of_date
        )


if __name__ == "__main__":
    main()