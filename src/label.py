<<<<<<< HEAD
"""Enum type for labels"""
=======
"""Canonical transaction labels shared by Python and PostgreSQL."""
>>>>>>> cb9cd5a8bd1209222dfe2d28609f9f202e9ac8b9

from enum import Enum


<<<<<<< HEAD
class Label(Enum):
    """Enum to label transactions following SQL enums"""

    CONFIRMED_LEGITIMATE = 1
    LEGITIMATE = 2
    UNUSUAL = 3
    SUSPICIOUS = 4
    CONFIRMED_FRAUDULENT = 5
    RULE_VIOLATION = 6
=======
class Label(str, Enum):
    """Transaction labels whose values exactly match ``transaction_label``."""

    CONFIRMED_LEGITIMATE = "confirmed_legitimate"
    LEGITIMATE = "legitimate"
    UNUSUAL = "unusual"
    SUSPICIOUS = "suspicious"
    CONFIRMED_FRAUDULENT = "confirmed_fraudulent"
    REPORTED_FRAUD = "reported_fraud"
    RULE_VIOLATION = "rule_violation"
    RULE_APPROVAL = "rule_approval"
    RULE_ALERT = "rule_alert"

    @classmethod
    def parse(cls, value):
        """Return a label from an enum instance, enum name, or database value."""
        if isinstance(value, cls):
            return value
        if not isinstance(value, str):
            raise TypeError(
                f"Label must be a string or Label, got {type(value).__name__}."
            )
        normalised = value.strip().lower()
        try:
            return cls(normalised)
        except ValueError:
            try:
                return cls[normalised.upper()]
            except KeyError as error:
                raise ValueError(f"Unknown transaction label: {value!r}.") from error
>>>>>>> cb9cd5a8bd1209222dfe2d28609f9f202e9ac8b9
