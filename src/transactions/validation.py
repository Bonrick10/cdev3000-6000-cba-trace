"""Input normalization at the transaction-processing boundary."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from src.rules.rules import normalise_datetime

REQUIRED_FIELDS = (
    "sender_bsb",
    "sender_account_number",
    "receiver_bsb",
    "receiver_account_number",
    "amount",
    "transaction_time",
    "device_id",
)


def validate_transaction(transaction: Dict[str, Any]) -> Dict[str, Any]:
    """Return a normalized copy or raise a field-specific validation error."""
    if not isinstance(transaction, dict):
        raise TypeError("Transaction must be a dictionary.")
    missing = [
        field
        for field in REQUIRED_FIELDS
        if field not in transaction or transaction[field] is None
    ]
    if missing:
        raise ValueError(f"Transaction is missing required fields: {missing}")

    normalized = dict(transaction)
    for field in (
        "sender_bsb",
        "sender_account_number",
        "receiver_bsb",
        "receiver_account_number",
    ):
        try:
            normalized[field] = int(normalized[field])
        except (TypeError, ValueError) as error:
            raise ValueError(f"{field} must be an integer.") from error
    if not 100000 <= normalized["sender_bsb"] <= 999999:
        raise ValueError("sender_bsb must contain six digits.")
    if not 100000 <= normalized["receiver_bsb"] <= 999999:
        raise ValueError("receiver_bsb must contain six digits.")
    if normalized["sender_account_number"] <= 0:
        raise ValueError("sender_account_number must be positive.")
    if normalized["receiver_account_number"] <= 0:
        raise ValueError("receiver_account_number must be positive.")

    try:
        normalized["amount"] = float(normalized["amount"])
    except (TypeError, ValueError) as error:
        raise ValueError("amount must be numeric.") from error
    if normalized["amount"] < 0:
        raise ValueError("amount must not be negative.")

    timestamp: datetime = normalise_datetime(normalized["transaction_time"])
    if timestamp.tzinfo is None:
        raise ValueError("transaction_time must include a timezone.")
    normalized["transaction_time"] = timestamp

    device_id = str(normalized["device_id"]).strip()
    if not device_id or len(device_id) > 64:
        raise ValueError("device_id must contain between 1 and 64 characters.")
    normalized["device_id"] = device_id

    for field, lower, upper in (
        ("sender_latitude", -90.0, 90.0),
        ("sender_longitude", -180.0, 180.0),
    ):
        value = normalized.get(field)
        if value is None:
            continue
        try:
            value = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{field} must be numeric or null.") from error
        if not lower <= value <= upper:
            raise ValueError(f"{field} must be between {lower} and {upper}.")
        normalized[field] = value

    merchant_tag = normalized.get("merchant_tags", normalized.get("merchant_tag"))
    if merchant_tag is not None:
        try:
            merchant_tag = int(merchant_tag)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "merchant_tags must be a merchant-tag ID or null."
            ) from error
    normalized["merchant_tags"] = merchant_tag
    normalized.pop("merchant_tag", None)
    return normalized
