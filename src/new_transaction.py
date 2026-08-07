<<<<<<< HEAD
"""Fraud detection system that runs when a new transaction is entered, the process goes as follows
1. Checks the transaction against the ruleset
2. Uses the large model to determine a score, and checks if that score exceeds a threshold
3. Uses the small model to determine whether the transaction falls in a cluster that
    has many cases of fraud
If any point fails then the transaction is blocked, otherwise it is allowed to go through
"""

import json

from src.label import Label
from src.rules.rules import check_rules
=======
"""End-to-end processing for one pending bank transaction."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Dict, Optional
>>>>>>> cb9cd5a8bd1209222dfe2d28609f9f202e9ac8b9

from src.big_model.predict import predict_transaction as predict_big_model
from src.contracts import PipelineResult
from src.decision import combine_model_labels, decision_for_rule_exit
from src.features import build_live_features
from src.label import Label
from src.rules.context import read_context
from src.rules.rules import check_rules
from src.small_model.predict import predict_transaction as predict_small_model
from src.transactions.repository import persist_pipeline_result
from src.transactions.validation import validate_transaction
from src.utils.db import NeonDB

<<<<<<< HEAD

# For now this will just read in the new transaction from a json file
# Ideally for the final demo the user would be able to enter a transaction through the frontend UI
# Which would send the transaction in a JSON format to the backend which can then call this function
def read_transaction(filename):
    """Reads in transaction from json file"""
    with open(filename, "r", encoding="utf-8") as file:
=======
Predictor = Callable[[Any], Dict[str, Any]]


def read_transaction(filename: str | Path) -> Dict[str, Any]:
    """Read a transaction JSON object from disk."""
    with Path(filename).open("r", encoding="utf-8") as file:
>>>>>>> cb9cd5a8bd1209222dfe2d28609f9f202e9ac8b9
        contents = json.load(file)
    if not isinstance(contents, dict):
        raise ValueError("Transaction JSON must contain one object.")
    return contents


<<<<<<< HEAD
def process_transaction(transaction):
    """Fraud detection pipeline that determines whether a transaction is fraud or not
    Using ruleset, large and small models
=======
def _model_label(result: Dict[str, Any], model_name: str) -> Label:
    try:
        label = Label.parse(result["predicted_label"])
    except KeyError as error:
        raise ValueError(f"{model_name} did not return predicted_label.") from error
    if label not in (Label.LEGITIMATE, Label.UNUSUAL, Label.SUSPICIOUS):
        raise ValueError(
            f"{model_name} returned {label.value}; models may only return "
            "legitimate, unusual, or suspicious."
        )
    return label


def process_transaction(
    transaction: Dict[str, Any],
    *,
    db: Optional[NeonDB] = None,
    context: Optional[Dict[str, Any]] = None,
    persist: bool = False,
    big_predictor: Predictor = predict_big_model,
    small_predictor: Predictor = predict_small_model,
) -> Dict[str, Any]:
    """
    Evaluate rules and route eligible attempts to both models.

    Persistence is deliberately opt-in so demos and tests cannot accidentally
    insert transactions. Production callers must pass ``persist=True``.
>>>>>>> cb9cd5a8bd1209222dfe2d28609f9f202e9ac8b9
    """
    pending = validate_transaction(transaction)
    database = db
    prior_context = (
        dict(context) if context is not None else read_context(pending, database)
    )
    rules = check_rules(pending, prior_context)

    if rules.label in (
        Label.RULE_APPROVAL,
        Label.RULE_ALERT,
        Label.RULE_VIOLATION,
    ):
        result = PipelineResult(
            final=decision_for_rule_exit(rules.label),
            rules=rules,
        )
    else:
        features = build_live_features(pending, prior_context)
        with ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="fraud-model"
        ) as pool:
            big_future = pool.submit(big_predictor, features)
            small_future = pool.submit(small_predictor, features)
            big_evidence = dict(big_future.result())
            small_evidence = dict(small_future.result())
        final = combine_model_labels(
            _model_label(big_evidence, "Big model"),
            _model_label(small_evidence, "Small model"),
        )
        result = PipelineResult(
            final=final,
            rules=rules,
            big_model=big_evidence,
            small_model=small_evidence,
        )

<<<<<<< HEAD
    # Call Small Model

    if ruleset_result == Label.LEGITIMATE and not DRYRUN_FLAG:
        # Insert new transaction into db
        pass
    return ruleset_result


process_transaction(read_transaction("src/test_new_transaction.json"))
=======
    if persist:
        result.transaction_id = persist_pipeline_result(
            pending, result, prior_context, database
        )
    return result.to_dict()
>>>>>>> cb9cd5a8bd1209222dfe2d28609f9f202e9ac8b9
