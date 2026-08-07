<<<<<<< HEAD
"""Main Module"""

from db_init.populate_data import gen_all_txns, generate_seed_data, init_sting_txns, gen_sting_txns, gen_high_freq_txns, fix_sting_txns_device

if __name__ == "__main__":
    # generate_seed_data()
    # gen_all_txns()
    # init_sting_txns()
    # gen_sting_txns()
    # gen_high_freq_txns()
    fix_sting_txns_device()
=======
"""Command-line entry points for processing, training, and feedback."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from src.big_model.train import train_from_database as train_big_model
from src.evaluation import evaluate_from_database, format_evaluation
from src.new_transaction import process_transaction, read_transaction
from src.report_transaction import report_transaction
from src.small_model.feedback import rebuild_from_database
from src.small_model.train import train_from_database as train_small_model
from src.terminal import format_pipeline_result


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
    process.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON instead of the terminal summary",
    )

    commands.add_parser("train-big", help="train the mature supervised model")
    commands.add_parser("train-small", help="rebuild fraud-pattern clusters")
    evaluate = commands.add_parser(
        "evaluate", help="run a read-only integrated evaluation on hidden truth"
    )
    evaluate.add_argument(
        "--json", action="store_true", help="emit machine-readable JSON"
    )
    commands.add_parser(
        "refresh-small", help="rebuild clusters from the current 60-day window"
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
        if not args.json:
            print(
                format_pipeline_result(
                    output,
                    persisted=args.persist,
                    color=sys.stdout.isatty(),
                )
            )
            return
    elif args.command == "train-big":
        output = train_big_model()["metadata"]
    elif args.command == "train-small":
        output = train_small_model()["metadata"]
    elif args.command == "evaluate":
        output = evaluate_from_database()
        if not args.json:
            print(format_evaluation(output))
            return
    elif args.command == "refresh-small":
        bundle = rebuild_from_database()
        output = {
            "metadata": bundle["metadata"],
            "cluster_statistics": bundle["cluster_statistics"],
        }
    else:
        output = report_transaction(args.transaction_id, args.label)
    print(json.dumps(output, indent=2, default=_json_default))


if __name__ == "__main__":
    main()
>>>>>>> cb9cd5a8bd1209222dfe2d28609f9f202e9ac8b9
