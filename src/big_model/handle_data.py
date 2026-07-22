"""Read database data and create leakage-safe behavioural features."""

from __future__ import annotations

from collections import deque
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from dateutil.relativedelta import relativedelta
from geopy.distance import geodesic

from utils.db import NeonDB


BASE_DIR = Path(__file__).resolve().parent
SQL_DIR = BASE_DIR / "sql"

START_DATE = pd.Timestamp(
    "2000-01-01",
    tz="UTC",
)


# Underlying behavioural variables only.
#
# The following rule outputs are intentionally excluded:
# - impossible_travel_rule
# - spending_spike_rule
# - large_new_payee_rule
# - outside_merchant_usual_range
# - outside_merchant_suspicious_range
NUMERIC_FEATURES = [
    "amount",
    "log_amount",
    "hour_sin",
    "hour_cos",
    "day_of_week_sin",
    "day_of_week_cos",
    "is_weekend",
    "sender_latitude",
    "sender_longitude",
    "account_age_days",
    "prior_transaction_count",
    "prior_payee_transaction_count",
    "prior_device_transaction_count",
    "prior_24h_transaction_count",
    "prior_7d_transaction_count",
    "prior_24h_spend",
    "prior_7d_spend",
    "log_prior_24h_spend",
    "log_prior_7d_spend",
    "prior_mean_amount",
    "prior_std_amount",
    "amount_to_prior_mean_ratio",
    "hours_since_previous_transaction",
    "log_hours_since_previous_transaction",
    "distance_from_previous_transaction_km",
    "log_distance_from_previous_transaction_km",
]

CATEGORICAL_FEATURES = [
    "merchant_tag",
]

MODEL_FEATURES = (
    NUMERIC_FEATURES
    + CATEGORICAL_FEATURES
)


# Applied only to transactions older than two months.
#
# This creates a temporary target column in Python.
# It does not update labels stored in PostgreSQL.
MATURE_LABEL_MAPPING = {
    "confirmed_legitimate": 0,
    "legitimate": 0,
    "unusual": 0,
    "suspicious": 1,
    "confirmed_fraudulent": 1,
    "rule_violation": 1,
}


def normalise_utc(
    value: Any,
) -> pd.Timestamp:
    """Return a timezone-aware UTC timestamp."""

    timestamp = pd.Timestamp(value)

    if timestamp.tzinfo is None:
        return timestamp.tz_localize(
            "UTC"
        )

    return timestamp.tz_convert(
        "UTC"
    )


def get_maturity_cutoff(
    as_of_date: pd.Timestamp | None = None,
) -> pd.Timestamp:
    """
    Return the timestamp before which labels are mature.

    Transactions from the most recent two months are
    excluded from big-model training.
    """

    if as_of_date is None:
        current_time = pd.Timestamp.now(
            tz="UTC"
        )
    else:
        current_time = normalise_utc(
            as_of_date
        )

    return (
        current_time
        - relativedelta(months=2)
    )


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """Convert database numeric values safely to float."""

    if value is None:
        return default

    try:
        if pd.isna(value):
            return default
    except TypeError:
        pass

    if isinstance(value, Decimal):
        return float(value)

    if isinstance(value, str):
        cleaned = (
            value
            .replace("$", "")
            .replace(",", "")
            .strip()
        )

        if not cleaned:
            return default

        return float(cleaned)

    return float(value)


def calculate_distance(
    previous_latitude: Any,
    previous_longitude: Any,
    current_latitude: Any,
    current_longitude: Any,
) -> float:
    """Calculate geodesic distance between coordinates."""

    coordinates = [
        previous_latitude,
        previous_longitude,
        current_latitude,
        current_longitude,
    ]

    if any(
        value is None
        or pd.isna(value)
        for value in coordinates
    ):
        return 0.0

    return geodesic(
        (
            float(previous_latitude),
            float(previous_longitude),
        ),
        (
            float(current_latitude),
            float(current_longitude),
        ),
    ).km


def read_transactions(
    start_time: pd.Timestamp,
    end_time: pd.Timestamp,
) -> pd.DataFrame:
    """
    Read transactions in the interval:

    start_time <= transaction_time < end_time
    """

    db = NeonDB()

    rows = db.query(
        db.read_sql_file(
            SQL_DIR
            / "get_transactions.sql"
        ),
        {
            "start_time": (
                normalise_utc(start_time)
                .to_pydatetime()
            ),
            "end_time": (
                normalise_utc(end_time)
                .to_pydatetime()
            ),
        },
    )

    return pd.DataFrame(rows)


def read_all_mature_transactions(
    as_of_date: pd.Timestamp | None = None,
) -> tuple[pd.DataFrame, pd.Timestamp]:
    """Read all history before the maturity cutoff."""

    cutoff = get_maturity_cutoff(
        as_of_date
    )

    transactions = read_transactions(
        START_DATE,
        cutoff,
    )

    return transactions, cutoff


def read_incoming_context(
    transaction: dict[str, Any],
) -> dict[str, Any]:
    """Read historical context for an incoming transaction."""

    db = NeonDB()

    rows = db.query(
        db.read_sql_file(
            SQL_DIR
            / "get_incoming_context.sql"
        ),
        transaction,
    )

    if not rows:
        raise RuntimeError(
            "No incoming transaction "
            "context was returned."
        )

    return rows[0]["context"]


def create_empty_history() -> dict[str, Any]:
    """Create empty history for one sender account."""

    return {
        "first_time": None,
        "count": 0,
        "amount_sum": 0.0,
        "amount_sum_squares": 0.0,
        "payee_counts": {},
        "device_counts": {},
        "recent_transactions": deque(),
        "last_transaction": None,
    }


def build_feature_row(
    row: Any,
    history: dict[str, Any],
) -> dict[str, Any]:
    """
    Build one feature row.

    The account history is not modified in this function.
    """

    current_time = normalise_utc(
        row.transaction_time
    )

    current_amount = safe_float(
        row.amount
    )

    payee_key = (
        int(row.receiver_bsb),
        int(row.receiver_account_number),
    )

    device_key = str(
        row.device_id
    ).strip()

    recent_transactions = history[
        "recent_transactions"
    ]

    one_day_ago = (
        current_time
        - timedelta(hours=24)
    )

    prior_24h_transactions = [
        transaction
        for transaction
        in recent_transactions
        if transaction["time"]
        >= one_day_ago
    ]

    prior_24h_spend = sum(
        transaction["amount"]
        for transaction
        in prior_24h_transactions
    )

    prior_7d_spend = sum(
        transaction["amount"]
        for transaction
        in recent_transactions
    )

    prior_count = history["count"]

    if prior_count > 0:
        prior_mean_amount = (
            history["amount_sum"]
            / prior_count
        )

        prior_variance = max(
            (
                history[
                    "amount_sum_squares"
                ]
                / prior_count
            )
            - prior_mean_amount**2,
            0.0,
        )

        prior_std_amount = (
            prior_variance**0.5
        )
    else:
        prior_mean_amount = 0.0
        prior_std_amount = 0.0

    if prior_mean_amount > 0:
        amount_to_prior_mean_ratio = (
            current_amount
            / prior_mean_amount
        )
    else:
        amount_to_prior_mean_ratio = 0.0

    first_time = history[
        "first_time"
    ]

    if first_time is None:
        account_age_days = 0.0
    else:
        account_age_days = max(
            (
                current_time
                - first_time
            ).total_seconds()
            / 86_400,
            0.0,
        )

    last_transaction = history[
        "last_transaction"
    ]

    hours_since_previous = 0.0
    distance_from_previous = 0.0

    if last_transaction is not None:
        hours_since_previous = max(
            (
                current_time
                - last_transaction["time"]
            ).total_seconds()
            / 3_600,
            0.0,
        )

        distance_from_previous = (
            calculate_distance(
                last_transaction[
                    "latitude"
                ],
                last_transaction[
                    "longitude"
                ],
                row.sender_latitude,
                row.sender_longitude,
            )
        )

    hour_angle = (
        2
        * np.pi
        * current_time.hour
        / 24
    )

    day_angle = (
        2
        * np.pi
        * current_time.dayofweek
        / 7
    )

    merchant_tag = (
        str(row.merchant_tag)
        if row.merchant_tag is not None
        else "unknown"
    )

    return {
        "transaction_id":
            int(row.transaction_id),

        "transaction_time":
            current_time,

        "original_label":
            row.label,

        "target":
            MATURE_LABEL_MAPPING.get(
                row.label
            ),

        "amount":
            current_amount,

        "log_amount":
            np.log1p(
                max(current_amount, 0.0)
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
                current_time.dayofweek
                >= 5
            ),

        "sender_latitude":
            safe_float(
                row.sender_latitude
            ),

        "sender_longitude":
            safe_float(
                row.sender_longitude
            ),

        "account_age_days":
            account_age_days,

        "prior_transaction_count":
            prior_count,

        "prior_payee_transaction_count":
            history[
                "payee_counts"
            ].get(
                payee_key,
                0,
            ),

        "prior_device_transaction_count":
            history[
                "device_counts"
            ].get(
                device_key,
                0,
            ),

        "prior_24h_transaction_count":
            len(
                prior_24h_transactions
            ),

        "prior_7d_transaction_count":
            len(
                recent_transactions
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
            prior_std_amount,

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
            merchant_tag,
    }


def update_history(
    row: Any,
    history: dict[str, Any],
) -> None:
    """Update history after creating the feature row."""

    current_time = normalise_utc(
        row.transaction_time
    )

    current_amount = safe_float(
        row.amount
    )

    payee_key = (
        int(row.receiver_bsb),
        int(row.receiver_account_number),
    )

    device_key = str(
        row.device_id
    ).strip()

    if history["first_time"] is None:
        history["first_time"] = (
            current_time
        )

    history["count"] += 1

    history["amount_sum"] += (
        current_amount
    )

    history["amount_sum_squares"] += (
        current_amount**2
    )

    history["payee_counts"][payee_key] = (
        history[
            "payee_counts"
        ].get(
            payee_key,
            0,
        )
        + 1
    )

    history["device_counts"][device_key] = (
        history[
            "device_counts"
        ].get(
            device_key,
            0,
        )
        + 1
    )

    history[
        "recent_transactions"
    ].append(
        {
            "time":
                current_time,
            "amount":
                current_amount,
        }
    )

    history["last_transaction"] = {
        "time":
            current_time,

        "latitude":
            row.sender_latitude,

        "longitude":
            row.sender_longitude,
    }


def create_features(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Create chronological behavioural features.

    Each feature only uses transactions with a timestamp
    strictly earlier than the current transaction.

    Transactions sharing the same timestamp do not see each
    other. This matches the incoming prediction SQL query.
    """

    output_columns = [
        "transaction_id",
        "transaction_time",
        "original_label",
        "target",
        *MODEL_FEATURES,
    ]

    if dataframe.empty:
        return pd.DataFrame(
            columns=output_columns
        )

    required_columns = {
        "transaction_id",
        "sender_bsb",
        "sender_account_number",
        "receiver_bsb",
        "receiver_account_number",
        "amount",
        "transaction_time",
        "sender_latitude",
        "sender_longitude",
        "label",
        "merchant_tag",
        "device_id",
    }

    missing_columns = (
        required_columns
        - set(dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            "Transaction data is missing: "
            f"{sorted(missing_columns)}"
        )

    ordered = dataframe.copy()

    ordered["transaction_time"] = (
        pd.to_datetime(
            ordered["transaction_time"],
            utc=True,
        )
    )

    ordered = ordered.sort_values(
        [
            "transaction_time",
            "transaction_id",
        ]
    ).reset_index(drop=True)

    account_histories: dict[
        tuple[int, int],
        dict[str, Any],
    ] = {}

    feature_rows: list[
        dict[str, Any]
    ] = []

    grouped_transactions = ordered.groupby(
        "transaction_time",
        sort=True,
    )

    for (
        current_timestamp,
        timestamp_group,
    ) in grouped_transactions:

        seven_days_ago = (
            normalise_utc(
                current_timestamp
            )
            - timedelta(days=7)
        )

        for history in (
            account_histories.values()
        ):
            recent_transactions = history[
                "recent_transactions"
            ]

            while (
                recent_transactions
                and recent_transactions[
                    0
                ]["time"]
                < seven_days_ago
            ):
                recent_transactions.popleft()

        current_rows = list(
            timestamp_group.itertuples(
                index=False
            )
        )

        # Build all rows before updating history.
        for row in current_rows:
            account_key = (
                int(row.sender_bsb),
                int(
                    row.sender_account_number
                ),
            )

            history = (
                account_histories.setdefault(
                    account_key,
                    create_empty_history(),
                )
            )

            feature_rows.append(
                build_feature_row(
                    row,
                    history,
                )
            )

        # Equal-timestamp transactions are added only
        # after every feature row in the batch is built.
        for row in current_rows:
            account_key = (
                int(row.sender_bsb),
                int(
                    row.sender_account_number
                ),
            )

            update_history(
                row,
                account_histories[
                    account_key
                ],
            )

    features = pd.DataFrame(
        feature_rows
    )

    features[
        NUMERIC_FEATURES
    ] = (
        features[
            NUMERIC_FEATURES
        ]
        .replace(
            [np.inf, -np.inf],
            np.nan,
        )
        .astype(float)
    )

    # Null or unknown labels cannot become binary targets.
    features = features.dropna(
        subset=["target"]
    ).copy()

    features["target"] = (
        features["target"]
        .astype(int)
    )

    return features.reset_index(
        drop=True
    )


def chronological_split(
    dataframe: pd.DataFrame,
    train_fraction: float = 0.80,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Use the oldest transactions for training and
    the newest transactions for evaluation.
    """

    if not 0 < train_fraction < 1:
        raise ValueError(
            "train_fraction must be "
            "between 0 and 1."
        )

    ordered = dataframe.sort_values(
        [
            "transaction_time",
            "transaction_id",
        ]
    ).reset_index(drop=True)

    split_index = int(
        len(ordered)
        * train_fraction
    )

    if (
        split_index <= 0
        or split_index >= len(ordered)
    ):
        raise ValueError(
            "Not enough mature transactions "
            "for a chronological split."
        )

    train_data = ordered.iloc[
        :split_index
    ].copy()

    test_data = ordered.iloc[
        split_index:
    ].copy()

    return train_data, test_data