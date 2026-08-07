<<<<<<< HEAD
"""Checks the transaction against the current rules in ruleset"""

import collections
import datetime
from pathlib import Path

from geopy.distance import geodesic

from label import Label
from src.utils.db import NeonDB
=======
"""Pure evaluation of explicit fraud rules."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Iterable, Optional

from geopy.distance import geodesic
>>>>>>> cb9cd5a8bd1209222dfe2d28609f9f202e9ac8b9

from src.contracts import RuleDecision
from src.label import Label
from src.rules.rule_enum import RuleEnum
from src.settings import (
    FRESH_ACCOUNT_AGE_DAYS,
    FRESH_ACCOUNT_TRANSACTION_THRESHOLD,
    IMPOSSIBLE_TRAVEL_THRESHOLD_KMH,
    NEW_PAYEE_ALERT_THRESHOLD,
    RECURRING_TRANSACTION_MINIMUM,
)

<<<<<<< HEAD
IMPOSSIBLE_TRAVEL_THRESHOLD = 500  # Note that this is km/hr
NEW_PAYEE_UNUSUAL_THRESHOLD = 10000


def check_rules(transaction, dryrun_flag=True):
    """Checks the transaction against the current rules in ruleset"""
    db = NeonDB()
    print(transaction)
    # convert non entries into None - especially for merchant_tags which may not be provided
    surrounding_info = db.query(
        db.read_sql_file(SQL_DIR / "get_surrounding_info.sql"),
        collections.defaultdict(lambda: None, transaction),
    )[0]["json_build_object"]
    print(surrounding_info)

    # Check Suspicious rules first and Instant Exit if fails
    if check_impossible_travel(
        transaction, surrounding_info
    ) or check_merchant_type_suspicious_range(transaction, surrounding_info):
        return Label.SUSPICIOUS

    # Then check unusual rules, but don't instant fail
    return (
        Label.UNUSUAL
        if (
            check_unseen_device(transaction, surrounding_info, db, dryrun_flag)
            or check_exceed_weekly_total(transaction, surrounding_info)
            or check_large_amount_to_new_payee(transaction, surrounding_info)
            or check_merchant_type_suspicious_range(transaction, surrounding_info)
        )
        else Label.LEGITIMATE
    )


def check_unseen_device(transaction, surrounding_info, db, dryrun_flag=True):
    """1. Transaction made from a previously unseen device associated with the customer -> unusual
    """
    if not surrounding_info["device_seen_before"] and not dryrun_flag:
        # If device and entity combination not seen before, add a new session for this combination
        # TODO: Also add session if combination seen before but expired
        db.execute(
            """
            INSERT INTO 
                device_sessions (entity_id, device_id, session_start_time, session_end_time)
            VALUES (%s, %s, %s, NULL)
        """,
            [
                surrounding_info["entity_id"],
                transaction["device_id"],
                transaction["transaction_time"],
            ],
        )
    return not surrounding_info["device_seen_before"]


def check_exceed_weekly_total(transaction, surrounding_info):
    """2. 24 hour spending exceeds customer's cumulative 7 day total -> unusual"""
    return (
        transaction["amount"] + surrounding_info["24_hour_spending"]
        > surrounding_info["7_day_spending"]
    )


def check_impossible_travel(transaction, surrounding_info):
    """3. Two transactions made more than 500km apart per hour -> suspicious"""
    # If no last transaction, skip this check
    if surrounding_info["last_transaction_time"] is None:
        return False
    distance = geodesic(
        (
            surrounding_info["last_transaction_lattitude"],
            surrounding_info["last_transaction_longitude"],
        ),
        (transaction["sender_latitude"], transaction["sender_longitude"]),
    ).km
    delta_time_hours = (
        datetime.datetime.fromisoformat(transaction["transaction_time"])
        - datetime.datetime.fromisoformat(surrounding_info["last_transaction_time"])
    ).total_seconds() / 3600
=======
RuleFunction = Callable[[Dict[str, Any], Dict[str, Any]], Optional[RuleEnum]]


def normalise_datetime(value: Any) -> datetime:
    """Accept PostgreSQL datetimes and ISO timestamp strings."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise TypeError(f"Expected datetime or ISO string, got {type(value).__name__}.")


def _triggered(
    functions: Iterable[RuleFunction],
    transaction: Dict[str, Any],
    context: Dict[str, Any],
):
    return [
        result.value
        for function in functions
        for result in [function(transaction, context)]
        if result is not None
    ]


def check_rules(transaction: Dict[str, Any], context: Dict[str, Any]) -> RuleDecision:
    """Evaluate rules in safety order without changing database state."""
    violations = _triggered(
        (check_impossible_travel, check_merchant_type_suspicious_range),
        transaction,
        context,
    )
    if violations:
        return RuleDecision(Label.RULE_VIOLATION, violations)

    alerts = _triggered(
        (
            check_unseen_device,
            check_exceed_7d_total,
            check_large_amount_to_new_payee,
            check_merchant_type_unusual_range,
        ),
        transaction,
        context,
    )
    if alerts:
        return RuleDecision(Label.RULE_ALERT, alerts)
>>>>>>> cb9cd5a8bd1209222dfe2d28609f9f202e9ac8b9

    approvals = _triggered((check_recurring_transaction,), transaction, context)
    if approvals:
        return RuleDecision(Label.RULE_APPROVAL, approvals)

<<<<<<< HEAD

def check_large_amount_to_new_payee(transaction, surrounding_info):
    """4. Transactions in excess of $10 000 to new payees -> unusual"""
    return surrounding_info["is_new_payee"] and transaction["amount"] > NEW_PAYEE_UNUSUAL_THRESHOLD


def check_merchant_type_unusual_range(transaction, surrounding_info):
    """5. Transactions outside of normal range for merchant type -> unusual"""
    # Note that lower and upper thresholds may be NULL
    return (
        surrounding_info["usual_threshold_lower"]
        and transaction["amount"] < surrounding_info["usual_threshold_lower"]
    ) or (
        surrounding_info["usual_threshold_upper"]
        and transaction["amount"] > surrounding_info["usual_threshold_upper"]
    )


def check_merchant_type_suspicious_range(transaction, surrounding_info):
    """6. Transactions far exceed normal range for merchant type -> suspicious"""
    # Note that lower and upper thresholds may be NULL
    return (
        surrounding_info["suspicious_threshold_lower"]
        and transaction["amount"] < surrounding_info["suspicious_threshold_lower"]
    ) or (
        surrounding_info["suspicious_threshold_upper"]
        and transaction["amount"] > surrounding_info["suspicious_threshold_upper"]
=======
    return RuleDecision(Label.LEGITIMATE, [])


def check_recurring_transaction(transaction, context):
    del transaction
    return (
        RuleEnum.RECURRING_TRANSACTION
        if int(context.get("num_recurring") or 0) >= RECURRING_TRANSACTION_MINIMUM
        else None
    )


def check_unseen_device(transaction, context):
    if is_fresh_account(transaction, context):
        return None
    return (
        RuleEnum.UNSEEN_DEVICE if not context.get("device_seen_before", False) else None
    )


def check_exceed_7d_total(transaction, context):
    if is_fresh_account(transaction, context):
        return None
    amount = float(transaction["amount"])
    return (
        RuleEnum.EXCEED_7D_TOTAL
        if amount + float(context.get("prior_24h_spend") or 0)
        > float(context.get("prior_7d_spend") or 0)
        else None
    )


def check_impossible_travel(transaction, context):
    previous_time = context.get("last_transaction_time")
    previous_coordinates = (
        context.get("last_transaction_latitude"),
        context.get("last_transaction_longitude"),
    )
    current_coordinates = (
        transaction.get("sender_latitude"),
        transaction.get("sender_longitude"),
    )
    coordinates = previous_coordinates + current_coordinates
    if previous_time is None or any(value is None for value in coordinates):
        return None

    elapsed_hours = (
        normalise_datetime(transaction["transaction_time"])
        - normalise_datetime(previous_time)
    ).total_seconds() / 3600
    if elapsed_hours <= 0:
        return None

    distance = geodesic(previous_coordinates, current_coordinates).km
    return (
        RuleEnum.IMPOSSIBLE_TRAVEL
        if distance / elapsed_hours > IMPOSSIBLE_TRAVEL_THRESHOLD_KMH
        else None
    )


def check_large_amount_to_new_payee(transaction, context):
    if is_fresh_account(transaction, context):
        return None
    return (
        RuleEnum.LARGE_AMOUNT_NEW_PAYEE
        if context.get("is_new_payee", True)
        and float(transaction["amount"]) > NEW_PAYEE_ALERT_THRESHOLD
        else None
    )


def _outside_range(amount, lower, upper):
    return (lower is not None and amount < float(lower)) or (
        upper is not None and amount > float(upper)
    )


def check_merchant_type_unusual_range(transaction, context):
    return (
        RuleEnum.MERCHANT_TYPE_UNUSUAL_RANGE
        if _outside_range(
            float(transaction["amount"]),
            context.get("usual_threshold_lower"),
            context.get("usual_threshold_upper"),
        )
        else None
    )


def check_merchant_type_suspicious_range(transaction, context):
    return (
        RuleEnum.MERCHANT_TYPE_SUSPICIOUS_RANGE
        if _outside_range(
            float(transaction["amount"]),
            context.get("suspicious_threshold_lower"),
            context.get("suspicious_threshold_upper"),
        )
        else None
    )


def is_fresh_account(transaction: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """Return whether history is too young or sparse for history-based rules."""
    first_transaction = context.get("first_transaction_time")
    if first_transaction is None:
        return True
    transaction_count = int(context.get("prior_transaction_count") or 0)
    transaction_time = normalise_datetime(transaction["transaction_time"])
    first_transaction_time = normalise_datetime(first_transaction)
    account_age = transaction_time - first_transaction_time
    return (
        transaction_count < FRESH_ACCOUNT_TRANSACTION_THRESHOLD
        or account_age < timedelta(days=FRESH_ACCOUNT_AGE_DAYS)
>>>>>>> cb9cd5a8bd1209222dfe2d28609f9f202e9ac8b9
    )
