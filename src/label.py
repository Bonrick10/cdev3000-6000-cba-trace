"""Canonical transaction labels shared by Python and PostgreSQL."""

from enum import Enum


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
