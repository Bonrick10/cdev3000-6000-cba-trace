"""Atomic persistence operations for the transaction pipeline."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from src.contracts import PipelineResult
from src.label import Label
from src.utils.db import NeonDB

SQL_DIRECTORY = Path(__file__).resolve().parent / "sql"


def persist_pipeline_result(
    transaction: Dict[str, Any],
    result: PipelineResult,
    context: Dict[str, Any],
    db: Optional[NeonDB] = None,
) -> int:
    """Insert the attempt, evidence, and new device session atomically."""
    database = db or NeonDB()
    transaction_params = dict(transaction)
    transaction_params["predicted_label"] = result.final.label.value
    transaction_params.setdefault("merchant_tags", None)

    big = result.big_model or {}
    small = result.small_model or {}
    with database.transaction() as connection:
        rows = database.execute_sql_file(
            SQL_DIRECTORY / "insert_transaction.sql",
            transaction_params,
            connection,
        )
        transaction_id = int(rows[0]["id"])
        database.execute_sql_file(
            SQL_DIRECTORY / "insert_decision.sql",
            {
                "transaction_id": transaction_id,
                "rules_label": result.rules.label.value,
                "rules_reasons": result.rules.reasons,
                "big_model_label": big.get("predicted_label"),
                "big_model_score": big.get("fraud_probability"),
                "big_model_version": big.get("model_version"),
                "big_model_evidence": json.dumps(big) if big else None,
                "small_model_label": small.get("predicted_label"),
                "small_model_version": small.get("model_version"),
                "small_cluster_id": small.get("cluster_id"),
                "small_model_evidence": json.dumps(small) if small else None,
                "final_label": result.final.label.value,
                "decision_source": result.final.source,
                "decision_reason": result.final.reason,
                "action": result.final.action.value,
            },
            connection,
        )
        if result.final.action.value != "block" and not context.get(
            "device_seen_before", False
        ):
            database.execute_sql_file(
                SQL_DIRECTORY / "insert_device_session.sql",
                {
                    "entity_id": context["entity_id"],
                    "device_id": transaction["device_id"],
                    "transaction_time": transaction["transaction_time"],
                },
                connection,
            )
    return transaction_id


def correct_transaction(
    transaction_id: int,
    new_label: Label,
    correction_time: Optional[datetime] = None,
    db: Optional[NeonDB] = None,
) -> Dict[str, Any]:
    """Record customer truth without overwriting the original prediction."""
    if new_label not in (Label.CONFIRMED_LEGITIMATE, Label.CONFIRMED_FRAUDULENT):
        raise ValueError("Customer corrections must be a confirmed label.")
    database = db or NeonDB()
    timestamp = correction_time or datetime.now(timezone.utc)
    with database.transaction() as connection:
        rows = database.execute_sql_file(
            SQL_DIRECTORY / "correct_transaction.sql",
            {
                "transaction_id": int(transaction_id),
                "new_label": new_label.value,
                "correction_time": timestamp,
            },
            connection,
        )
    if not rows:
        raise ValueError(
            f"Transaction {transaction_id} does not exist or already has true label "
            f"{new_label.value}."
        )
    return dict(rows[0])
