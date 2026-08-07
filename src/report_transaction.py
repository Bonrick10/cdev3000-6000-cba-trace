<<<<<<< HEAD
"""Runs when a user reports a transaction as fraud, the fraud detection system
1. Determines which cluster that transaction is in
2. Marks that transaction as confirmed_fraud
3. Check if number of transactions in cluster marked as fraud exceed threshold (eg. 10%)
4. If it does exceed suspect other transactions in cluster for fraud
    -> possibly call up or implement investigation process.
5. Re-cluster appropriately after fraudulent/legitimate labels are confirmed, to segregate
    confirmed legitimate cases and confirmed fraudulent cases,
    and sort unconfirmed legitimate cases.
6. Once clusters contain sufficient fraud, use Bayesian optimization to discover new rules.
"""
=======
"""Customer feedback entry point and small-model statistics refresh."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from src.label import Label
from src.small_model.feedback import rebuild_from_database
from src.transactions.repository import correct_transaction
from src.utils.db import NeonDB


def report_transaction(
    transaction_id: int,
    label: Label | str,
    *,
    correction_time: Optional[datetime] = None,
    db: Optional[NeonDB] = None,
    refresh_small_model: bool = True,
) -> Dict[str, Any]:
    """Record a confirmed outcome and rebuild after a new fraud report."""
    confirmed_label = Label.parse(label)
    correction = correct_transaction(
        transaction_id, confirmed_label, correction_time, db
    )
    refresh_status: Dict[str, Any] = {"status": "not_requested"}
    if refresh_small_model and confirmed_label is Label.CONFIRMED_FRAUDULENT:
        try:
            bundle = rebuild_from_database(db=db)
            refresh_status = {
                "status": "rebuilt",
                "model_version": bundle["metadata"]["version"],
                "cluster_statistics": bundle["cluster_statistics"],
            }
        except FileNotFoundError as error:
            refresh_status = {
                "status": "model_not_trained",
                "message": str(error),
            }
        except Exception as error:
            # The correction is already committed. Return that success and make
            # the independent rebuild failure visible instead of inviting a retry.
            refresh_status = {
                "status": "rebuild_failed",
                "message": str(error),
            }

    return {
        "correction": correction,
        "small_model_statistics": refresh_status,
        "cluster_rebuild_completed": refresh_status.get("status") == "rebuilt",
    }
>>>>>>> cb9cd5a8bd1209222dfe2d28609f9f202e9ac8b9
