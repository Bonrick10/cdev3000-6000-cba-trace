"""Predict labels and fraud-risk scores for incoming transactions."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
from geopy.distance import geodesic

from Handle_data import MODEL_FEATURES
from train import load_model_bundle


def to_float(value: Any, default: float = 0.0) -> float:
    """Convert PostgreSQL money/decimal/null values to float."""

    if value is None:
        return default

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, str):
        cleaned = (
            value.replace("$", "")
            .replace(",", "")
            .strip()
        )

        if cleaned == "":
            return default

        return float(cleaned)

    return float(value)


def parse_timestamp(value: Any) -> pd.Timestamp | None:
    """Convert a timestamp-like value to a UTC pandas timestamp."""

    if value is None:
        return None

    timestamp = pd.Timestamp(value)

    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")

    return timestamp.tz_convert("UTC")


def build_incoming_features(
    transaction: dict[str, Any],
    surrounding_info: dict[str, Any],
) -> pd.DataFrame:
    """
    Create the same features used during model training.

    surrounding_info must be generated using only transactions that
    occurred before the incoming transaction.
    """

    transaction_time = parse_timestamp(
        transaction["transaction_time"]
    )

    if transaction_time is None:
        raise ValueError("transaction_time is required.")

    amount = to_float(transaction["amount"])

    device_seen_before = bool(
        surrounding_info.get("device_seen_before", False)
    )

    is_new_payee = bool(
        surrounding_info.get("is_new_payee", True)
    )

    prior_24h_spend = to_float(
        surrounding_info.get("24_hour_spending", 0)
    )

    previous_7d_spend = to_float(
        surrounding_info.get("previous_7_day_spending", 0)
    )

    spend_24h_including_current = (
        prior_24h_spend + amount
    )

    spending_ratio = (
        spend_24h_including_current / previous_7d_spend
        if previous_7d_spend > 0
        else spend_24h_including_current
    )

    previous_time = parse_timestamp(
        surrounding_info.get("last_transaction_time")
    )

    previous_latitude = surrounding_info.get(
        "last_transaction_latitude"
    )

    # Temporary compatibility with the current misspelled DB key.
    if previous_latitude is None:
        previous_latitude = surrounding_info.get(
            "last_transaction_lattitude"
        )

    previous_longitude = surrounding_info.get(
        "last_transaction_longitude"
    )

    distance_km = 0.0
    hours_since_previous = 0.0
    travel_speed_kmh = 0.0

    if (
        previous_time is not None
        and previous_latitude is not None
        and previous_longitude is not None
        and transaction.get("sender_latitude") is not None
        and transaction.get("sender_longitude") is not None
    ):
        hours_since_previous = max(
            (
                transaction_time - previous_time
            ).total_seconds() / 3600,
            0.0,
        )

        distance_km = geodesic(
            (
                float(previous_latitude),
                float(previous_longitude),
            ),
            (
                float(transaction["sender_latitude"]),
                float(transaction["sender_longitude"]),
            ),
        ).km

        if hours_since_previous > 0:
            travel_speed_kmh = (
                distance_km / hours_since_previous
            )

    merchant_usual_lower = to_float(
        surrounding_info.get("usual_threshold_lower", 0)
    )

    merchant_usual_upper = to_float(
        surrounding_info.get("usual_threshold_upper", 0)
    )

    merchant_suspicious_lower = to_float(
        surrounding_info.get(
            "suspicious_threshold_lower",
            0,
        )
    )

    merchant_suspicious_upper = to_float(
        surrounding_info.get(
            "suspicious_threshold_upper",
            0,
        )
    )

    outside_usual = int(
        (
            merchant_usual_lower > 0
            and amount < merchant_usual_lower
        )
        or (
            merchant_usual_upper > 0
            and amount > merchant_usual_upper
        )
    )

    outside_suspicious = int(
        (
            merchant_suspicious_lower > 0
            and amount < merchant_suspicious_lower
        )
        or (
            merchant_suspicious_upper > 0
            and amount > merchant_suspicious_upper
        )
    )

    feature_row = {
        "amount": amount,
        "hour_of_day": transaction_time.hour,
        "day_of_week": transaction_time.dayofweek,
        "is_weekend": int(
            transaction_time.dayofweek in [5, 6]
        ),
        "is_new_device": int(not device_seen_before),
        "is_new_payee": int(is_new_payee),
        "spend_24h_including_current":
            spend_24h_including_current,
        "spend_previous_7d": previous_7d_spend,
        "spend_24h_to_previous_7d_ratio":
            spending_ratio,
        "spending_spike_rule": int(
            previous_7d_spend > 0
            and spend_24h_including_current
            > previous_7d_spend
        ),
        "distance_from_previous_transaction_km":
            distance_km,
        "hours_since_previous_transaction":
            hours_since_previous,
        "travel_speed_kmh": travel_speed_kmh,
        "impossible_travel_rule": int(
            travel_speed_kmh > 500
        ),
        "merchant_usual_lower": merchant_usual_lower,
        "merchant_usual_upper": merchant_usual_upper,
        "merchant_suspicious_lower":
            merchant_suspicious_lower,
        "merchant_suspicious_upper":
            merchant_suspicious_upper,
        "amount_to_merchant_upper_ratio": (
            amount / merchant_usual_upper
            if merchant_usual_upper > 0
            else 0.0
        ),
        "outside_merchant_usual_range":
            outside_usual,
        "outside_merchant_suspicious_range":
            outside_suspicious,
        "large_new_payee_rule": int(
            amount > 10_000 and is_new_payee
        ),
    }

    return pd.DataFrame(
        [feature_row],
        columns=MODEL_FEATURES,
    )


def predict_transaction(
    transaction: dict[str, Any],
    surrounding_info: dict[str, Any],
) -> dict[str, Any]:
    """Return model probabilities, predicted class and risk score."""

    bundle = load_model_bundle()
    model = bundle["model"]

    features = build_incoming_features(
        transaction,
        surrounding_info,
    )

    probabilities = model.predict_proba(features)[0]

    classes = list(
        model.named_steps["classifier"].classes_
    )

    probability_by_class = {
        class_name: float(probability)
        for class_name, probability in zip(
            classes,
            probabilities,
        )
    }

    legitimate_probability = probability_by_class.get(
        "legitimate",
        0.0,
    )

    unusual_probability = probability_by_class.get(
        "unusual",
        0.0,
    )

    suspicious_probability = probability_by_class.get(
        "suspicious",
        0.0,
    )

    risk_score = 100 * (
        0.50 * unusual_probability
        + suspicious_probability
    )

    predicted_label = max(
        probability_by_class,
        key=probability_by_class.get,
    )

    return {
        "predicted_label": predicted_label,
        "risk_score": round(risk_score, 2),
        "legitimate_probability": round(
            legitimate_probability,
            4,
        ),
        "unusual_probability": round(
            unusual_probability,
            4,
        ),
        "suspicious_probability": round(
            suspicious_probability,
            4,
        ),
        "model_cutoff": bundle["metadata"].get(
            "maturity_cutoff"
        ),
    }