"""Train and demonstrate the standalone small clustering model."""

from __future__ import annotations

import argparse

import pandas as pd

from small_config import (
    DATA_PATH,
    MODEL_FEATURES,
    SMALL_MODEL_PATH,
)
from small_feedback import update_cluster_feedback
from small_predict import predict_cluster
from small_train import (
    save_small_model_bundle,
    train_small_model,
)


def load_transaction_data() -> pd.DataFrame:
    """Load transactions from the local CSV file."""

    if not DATA_PATH.exists():
        raise FileNotFoundError(
            f"Could not find {DATA_PATH}."
        )

    data = pd.read_csv(
        DATA_PATH
    )

    data["transaction_time"] = pd.to_datetime(
        data["transaction_time"],
        errors="coerce",
        utc=True,
    )

    return data


def train_initial_small_model(
    number_of_clusters: int,
) -> None:
    """Train and save the small model."""

    transaction_data = load_transaction_data()

    print(
        f"Loaded transactions: {len(transaction_data)}"
    )

    model, statistics, metadata = (
        train_small_model(
            training_data=transaction_data,
            number_of_clusters=number_of_clusters,
        )
    )

    save_small_model_bundle(
        model=model,
        cluster_statistics=statistics,
        metadata=metadata,
    )

    print("\nCluster statistics")

    print(
        statistics.to_string(
            index=False
        )
    )

    print(
        f"\nSmall model saved to {SMALL_MODEL_PATH}"
    )


def demonstrate_small_model() -> None:
    """Demonstrate a prediction using one example transaction."""

    example_transaction = pd.DataFrame(
        [
            {
                "amount": 12500,
                "hour_of_day": 2,
                "day_of_week": 5,
                "is_weekend": 1,
                "is_new_device": 1,
                "is_new_payee": 1,
                "spend_24h": 15000,
                "spend_7d": 2200,
                "distance_km": 900,
            }
        ]
    )

    result = predict_cluster(
        example_transaction[
            MODEL_FEATURES
        ]
    )

    print("\nExample transaction")

    print(
        example_transaction.to_string(
            index=False
        )
    )

    print("\nPrediction")

    for key, value in result.items():
        print(f"{key}: {value}")


def apply_example_feedback(
    cluster_id: int,
    confirmed_fraud: bool,
) -> None:
    """Apply one example confirmed result."""

    result = update_cluster_feedback(
        cluster_id=cluster_id,
        confirmed_fraud=confirmed_fraud,
    )

    print("\nUpdated cluster statistics")

    for key, value in result.items():
        print(f"{key}: {value}")


def parse_args() -> argparse.Namespace:
    """Read command-line arguments."""

    parser = argparse.ArgumentParser(
        description="Standalone CBA small clustering model"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    train_parser = subparsers.add_parser(
        "train"
    )

    train_parser.add_argument(
        "--clusters",
        type=int,
        default=2,
        help="Number of K-means clusters.",
    )

    subparsers.add_parser(
        "demo"
    )

    feedback_parser = subparsers.add_parser(
        "feedback"
    )

    feedback_parser.add_argument(
        "--cluster-id",
        type=int,
        required=True,
    )

    feedback_parser.add_argument(
        "--fraud",
        action="store_true",
        help="Mark the feedback as confirmed fraud.",
    )

    return parser.parse_args()


def main() -> None:
    """Run the selected command."""

    args = parse_args()

    if args.command == "train":
        train_initial_small_model(
            number_of_clusters=args.clusters,
        )

    elif args.command == "demo":
        demonstrate_small_model()

    elif args.command == "feedback":
        apply_example_feedback(
            cluster_id=args.cluster_id,
            confirmed_fraud=args.fraud,
        )


if __name__ == "__main__":
    main()