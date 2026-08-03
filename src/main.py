"""Command-line entry points for processing, training, and feedback."""

from __future__ import annotations

import argparse
import json
from typing import Any

from src.big_model.train import train_from_database as train_big_model
from src.new_transaction import process_transaction, read_transaction
from src.report_transaction import report_transaction
from src.small_model.feedback import refresh_statistics_from_database
from src.small_model.train import train_from_database as train_small_model


def _json_default(value: Any):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    raise TypeError(f"{type(value).__name__} is not JSON serializable.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fraud-detection pipeline")
    commands = parser.add_subparsers(dest="command", required=True)

    process = commands.add_parser("process", help="process one transaction JSON file")
    process.add_argument("transaction_json")
    process.add_argument(
        "--persist",
        action="store_true",
        help="insert the transaction and decision evidence (default: dry run)",
    )

    commands.add_parser("train-big", help="train the mature supervised model")
    commands.add_parser("train-small", help="rebuild fraud-pattern clusters")
    commands.add_parser(
        "refresh-small", help="refresh cluster rates without rebuilding clusters"
    )

    report = commands.add_parser("report", help="record a confirmed customer outcome")
    report.add_argument("transaction_id", type=int)
    report.add_argument(
        "label", choices=("confirmed_legitimate", "confirmed_fraudulent")
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "process":
        output = process_transaction(
            read_transaction(args.transaction_json),
            persist=args.persist,
        )
    elif args.command == "train-big":
        output = train_big_model()["metadata"]
    elif args.command == "train-small":
        output = train_small_model()["metadata"]
    elif args.command == "refresh-small":
        bundle = refresh_statistics_from_database()
        output = {
            "metadata": bundle["metadata"],
            "cluster_statistics": bundle["cluster_statistics"],
        }
    else:
        output = report_transaction(args.transaction_id, args.label)
    print(json.dumps(output, indent=2, default=_json_default))


if __name__ == "__main__":
    main()
