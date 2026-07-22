"""Predict big-model fraud risk for incoming transactions."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .handle_data import (
    MODEL_FEATURES,
    calculate_distance,
    normalise_utc,
    read_incoming_context,
    safe_float,
)

from .train import (
    load_model_bundle,
)


def build_incoming_features(
    transaction: dict[str, Any],
    context: dict[str, Any],
) -> pd.DataFrame:
    """Create the same features used during training."""

    transaction_time = normalise_utc(
        transaction[
            "transaction_time"
        ]
    )

    amount = safe_float(
        transaction["amount"]
    )

    first_transaction_value = (
        context.get(
            "first_transaction_time"
        )
    )

    if first_transaction_value is None:
        account_age_days = 0.0
    else:
        first_transaction_time = (
            normalise_utc(
                first_transaction_value
            )
        )

        account_age_days = max(
            (
                transaction_time
                - first_transaction_time
            ).total_seconds()
            / 86_400,
            0.0,
        )

    previous_time_value = (
        context.get(
            "last_transaction_time"
        )
    )

    if previous_time_value is None:
        hours_since_previous = 0.0
    else:
        previous_time = normalise_utc(
            previous_time_value
        )

        hours_since_previous = max(
            (
                transaction_time
                - previous_time
            ).total_seconds()
            / 3_600,
            0.0,
        )

    distance_from_previous = (
        calculate_distance(
            context.get(
                "last_transaction_latitude"
            ),
            context.get(
                "last_transaction_longitude"
            ),
            transaction.get(
                "sender_latitude"
            ),
            transaction.get(
                "sender_longitude"
            ),
        )
    )

    prior_mean_amount = safe_float(
        context.get(
            "prior_mean_amount"
        )
    )

    prior_24h_spend = safe_float(
        context.get(
            "prior_24h_spend"
        )
    )

    prior_7d_spend = safe_float(
        context.get(
            "prior_7d_spend"
        )
    )

    if prior_mean_amount > 0:
        amount_to_prior_mean_ratio = (
            amount
            / prior_mean_amount
        )
    else:
        amount_to_prior_mean_ratio = 0.0

    hour_angle = (
        2
        * np.pi
        * transaction_time.hour
        / 24
    )

    day_angle = (
        2
        * np.pi
        * transaction_time.dayofweek
        / 7
    )

    merchant_tag = transaction.get(
        "merchant_tags"
    )

    feature_row = {
        "amount":
            amount,

        "log_amount":
            np.log1p(
                max(amount, 0.0)
            ),

        "hour_sin":
            np.sin(hour_angle),

        "hour_cos":
            np.cos(hour_angle),

        "day_of_week_sin":
            np.sin(day_angle),

        "day_of_week_cos":
            np.cos(day_angle),

        "is_weekend":
            int(
                transaction_time.dayofweek
                >= 5
            ),

        "sender_latitude":
            safe_float(
                transaction.get(
                    "sender_latitude"
                )
            ),

        "sender_longitude":
            safe_float(
                transaction.get(
                    "sender_longitude"
                )
            ),

        "account_age_days":
            account_age_days,

        "prior_transaction_count":
            safe_float(
                context.get(
                    "prior_transaction_count"
                )
            ),

        "prior_payee_transaction_count":
            safe_float(
                context.get(
                    "prior_payee_transaction_count"
                )
            ),

        "prior_device_transaction_count":
            safe_float(
                context.get(
                    "prior_device_transaction_count"
                )
            ),

        "prior_24h_transaction_count":
            safe_float(
                context.get(
                    "prior_24h_transaction_count"
                )
            ),

        "prior_7d_transaction_count":
            safe_float(
                context.get(
                    "prior_7d_transaction_count"
                )
            ),

        "prior_24h_spend":
            prior_24h_spend,

        "prior_7d_spend":
            prior_7d_spend,

        "log_prior_24h_spend":
            np.log1p(
                max(
                    prior_24h_spend,
                    0.0,
                )
            ),

        "log_prior_7d_spend":
            np.log1p(
                max(
                    prior_7d_spend,
                    0.0,
                )
            ),

        "prior_mean_amount":
            prior_mean_amount,

        "prior_std_amount":
            safe_float(
                context.get(
                    "prior_std_amount"
                )
            ),

        "amount_to_prior_mean_ratio":
            amount_to_prior_mean_ratio,

        "hours_since_previous_transaction":
            hours_since_previous,

        "log_hours_since_previous_transaction":
            np.log1p(
                hours_since_previous
            ),

        "distance_from_previous_transaction_km":
            distance_from_previous,

        "log_distance_from_previous_transaction_km":
            np.log1p(
                max(
                    distance_from_previous,
                    0.0,
                )
            ),

        "merchant_tag":
            (
                str(merchant_tag)
                if merchant_tag is not None
                else "unknown"
            ),
    }

    return pd.DataFrame(
        [feature_row],
        columns=MODEL_FEATURES,
    )


def probability_to_label(
    fraud_probability: float,
    unusual_threshold: float = 0.70,
    suspicious_threshold: float = 0.90,
) -> str:
    """Convert a fraud probability to an operational label."""

    if (
        fraud_probability
        >= suspicious_threshold
    ):
        return "suspicious"

    if (
        fraud_probability
        >= unusual_threshold
    ):
        return "unusual"

    return "legitimate"


def predict_transaction(
    transaction: dict[str, Any],
    context: dict[str, Any] | None = None,
    unusual_threshold: float = 0.70,
    suspicious_threshold: float = 0.90,
) -> dict[str, Any]:
    """
    Predict mature-pattern fraud risk.

    The function only reads database context when context
    is not already supplied.
    """

    if not (
        0
        <= unusual_threshold
        < suspicious_threshold
        <= 1
    ):
        raise ValueError(
            "Thresholds must satisfy "
            "0 <= unusual < suspicious <= 1."
        )

    bundle = load_model_bundle()

    if context is None:
        context = read_incoming_context(
            transaction
        )

    features = (
        build_incoming_features(
            transaction,
            context,
        )
    )

    fraud_probability = float(
        bundle["model"]
        .predict_proba(
            features
        )[0, 1]
    )

    predicted_label = (
        probability_to_label(
            fraud_probability,
            unusual_threshold,
            suspicious_threshold,
        )
    )

    return {
        "predicted_label":
            predicted_label,

        "fraud_probability":
            round(
                fraud_probability,
                6,
            ),

        "risk_score":
            round(
                fraud_probability
                * 100,
                2,
            ),

        "unusual_threshold":
            unusual_threshold,

        "suspicious_threshold":
            suspicious_threshold,

        "model_version":
            bundle[
                "metadata"
            ].get(
                "version"
            ),

        "maturity_cutoff":
            bundle[
                "metadata"
            ].get(
                "maturity_cutoff"
            ),
    }