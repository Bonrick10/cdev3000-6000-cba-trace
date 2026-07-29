"""Stable identifiers for individual rules."""

from enum import Enum


class RuleEnum(str, Enum):
    """Rule identifiers persisted in decision evidence."""

    IMPOSSIBLE_TRAVEL = "impossible_travel"
    MERCHANT_TYPE_SUSPICIOUS_RANGE = "merchant_type_suspicious_range"
    UNSEEN_DEVICE = "unseen_device"
    EXCEED_7D_TOTAL = "exceed_7d_total"
    LARGE_AMOUNT_NEW_PAYEE = "large_amount_new_payee"
    MERCHANT_TYPE_UNUSUAL_RANGE = "merchant_type_unusual_range"
    RECURRING_TRANSACTION = "recurring_transaction"
