"""Read database data and produce model-ready behavioural features."""

from __future__ import annotations

import os
from collections import deque
from datetime import timedelta
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
import psycopg2
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from geopy.distance import geodesic


load_dotenv()

START_DATE = pd.Timestamp("2000-01-01", tz="UTC")

MODEL_FEATURES = [
    "amount",
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "is_new_device",
    "is_new_payee",
    "spend_24h_including_current",
    "spend_previous_7d",
    "spend_24h_to_previous_7d_ratio",
    "spending_spike_rule",
    "distance_from_previous_transaction_km",
    "hours_since_previous_transaction",
    "travel_speed_kmh",
    "impossible_travel_rule",
    "merchant_usual_lower",
    "merchant_usual_upper",
    "merchant_suspicious_lower",
    "merchant_suspicious_upper",
    "amount_to_merchant_upper_ratio",
    "outside_merchant_usual_range",
    "outside_merchant_suspicious_range",
    "large_new_payee_rule",
]


LABEL_MAPPING = {
    "confirmed_legitimate": "legitimate",
    "legitimate": "legitimate",
    "unusual": "unusual",
    "suspicious": "suspicious",
    "confirmed_fraudulent": "suspicious",
}


def get_database_connection():
    """Create and return a PostgreSQL database connection."""

    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is missing. Add it to your .env file."
        )

    return psycopg2.connect(database_url)


def get_maturity_cutoff(
    as_of_date: pd.Timestamp | None = None,
) -> pd.Timestamp:
    """
    Return the date before which labels are considered mature.

    Transactions from the latest two months are excluded.
    """

    if as_of_date is None:
        as_of_date = pd.Timestamp.now(tz="UTC")

    if as_of_date.tzinfo is None:
        as_of_date = as_of_date.tz_localize("UTC")
    else:
        as_of_date = as_of_date.tz_convert("UTC")

    return as_of_date - relativedelta(months=2)


def read_transactions(
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> pd.DataFrame:
    """
    Read transactions within [start_date, end_date).

    Rule violations are excluded because they do not reach the big model.
    """

    query = """
        SELECT
            t.id AS transaction_id,
            t.sender_bsb,
            t.sender_account_number,
            t.receiver_bsb,
            t.receiver_account_number,
            t.amount::numeric AS amount,
            t.transaction_time,
            t.sender_latitude::double precision
                AS sender_latitude,
            t.sender_longitude::double precision
                AS sender_longitude,
            t.label::text AS label,
            t.merchant_tags,
            t.device_id,

            mt.merchant_category,
            mt.suspicious_threshold_lower::numeric
                AS merchant_suspicious_lower,
            mt.usual_threshold_lower::numeric
                AS merchant_usual_lower,
            mt.usual_threshold_upper::numeric
                AS merchant_usual_upper,
            mt.suspicious_threshold_upper::numeric
                AS merchant_suspicious_upper

        FROM transactions AS t

        LEFT JOIN merchant_tags AS mt
            ON mt.id = t.merchant_tags

        WHERE t.transaction_time >= %s
          AND t.transaction_time < %s
          AND t.label IS NOT NULL
          AND t.label <> 'rule_violation'

        ORDER BY
            t.transaction_time,
            t.id;
    """

    connection = get_database_connection()

    try:
        dataframe = pd.read_sql_query(
            query,
            connection,
            params=[start_date.to_pydatetime(), end_date.to_pydatetime()],
        )
    finally:
        connection.close()

    return dataframe


def read_all_mature_transactions(
    as_of_date: pd.Timestamp | None = None,
) -> tuple[pd.DataFrame, pd.Timestamp]:
    """Read data from 2000 until two months before as_of_date."""

    cutoff = get_maturity_cutoff(as_of_date)

    dataframe = read_transactions(
        start_date=START_DATE,
        end_date=cutoff,
    )

    return dataframe, cutoff


def canonicalise_labels(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Convert confirmed labels to their corrected final model class.

    confirmed_legitimate -> legitimate
    confirmed_fraudulent -> suspicious
    """

    result = dataframe.copy()

    result["model_label"] = result["label"].map(LABEL_MAPPING)

    result = result.dropna(subset=["model_label"])

    return result


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert Decimal, money or nullable values to float."""

    if value is None or pd.isna(value):
        return default

    if isinstance(value, Decimal):
        return float(value)

    return float(value)


def calculate_distance(
    previous_latitude: float | None,
    previous_longitude: float | None,
    current_latitude: float | None,
    current_longitude: float | None,
) -> float:
    """Calculate distance between two valid coordinates."""

    coordinates = [
        previous_latitude,
        previous_longitude,
        current_latitude,
        current_longitude,
    ]

    if any(value is None or pd.isna(value) for value in coordinates):
        return 0.0

    return geodesic(
        (previous_latitude, previous_longitude),
        (current_latitude, current_longitude),
    ).km


def create_features(dataframe: pd.DataFrame) -> pd.DataFrame:
    """
    Create chronological behavioural features.

    Every feature only uses transactions that occurred before the current
    transaction, preventing future information from leaking into training.
    """

    if dataframe.empty:
        return dataframe.copy()

    result = canonicalise_labels(dataframe)

    result["transaction_time"] = pd.to_datetime(
        result["transaction_time"],
        utc=True,
    )

    money_columns = [
        "amount",
        "merchant_suspicious_lower",
        "merchant_usual_lower",
        "merchant_usual_upper",
        "merchant_suspicious_upper",
    ]

    for column in money_columns:
        result[column] = pd.to_numeric(
            result[column],
            errors="coerce",
        )

    result = result.sort_values(
        ["transaction_time", "transaction_id"]
    ).reset_index(drop=True)

    feature_rows: list[dict[str, Any]] = []

    account_histories: dict[
        tuple[int, int],
        dict[str, Any],
    ] = {}

    for row in result.itertuples(index=False):
        account_key = (
            int(row.sender_bsb),
            int(row.sender_account_number),
        )

        payee_key = (
            int(row.receiver_bsb),
            int(row.receiver_account_number),
        )

        if account_key not in account_histories:
            account_histories[account_key] = {
                "devices": set(),
                "payees": set(),
                "transactions": deque(),
                "last_transaction": None,
            }

        history = account_histories[account_key]
        current_time = row.transaction_time
        current_amount = safe_float(row.amount)

        # Keep up to eight days because we use:
        # current 24h + preceding seven-day comparison period.
        history_start = current_time - timedelta(days=8)

        while (
            history["transactions"]
            and history["transactions"][0]["time"] < history_start
        ):
            history["transactions"].popleft()

        current_24h_start = current_time - timedelta(hours=24)
        previous_7d_start = current_time - timedelta(days=8)
        previous_7d_end = current_time - timedelta(hours=24)

        spend_previous_24h = sum(
            transaction["amount"]
            for transaction in history["transactions"]
            if transaction["time"] >= current_24h_start
        )

        spend_previous_7d = sum(
            transaction["amount"]
            for transaction in history["transactions"]
            if (
                transaction["time"] >= previous_7d_start
                and transaction["time"] < previous_7d_end
            )
        )

        spend_24h_including_current = (
            spend_previous_24h + current_amount
        )

        spending_ratio = (
            spend_24h_including_current / spend_previous_7d
            if spend_previous_7d > 0
            else spend_24h_including_current
        )

        is_new_device = int(row.device_id not in history["devices"])
        is_new_payee = int(payee_key not in history["payees"])

        last_transaction = history["last_transaction"]

        distance_km = 0.0
        hours_since_previous = 0.0
        travel_speed_kmh = 0.0

        if last_transaction is not None:
            time_difference = (
                current_time - last_transaction["time"]
            ).total_seconds() / 3600

            hours_since_previous = max(time_difference, 0.0)

            distance_km = calculate_distance(
                last_transaction["latitude"],
                last_transaction["longitude"],
                row.sender_latitude,
                row.sender_longitude,
            )

            if hours_since_previous > 0:
                travel_speed_kmh = distance_km / hours_since_previous

        merchant_usual_lower = safe_float(
            row.merchant_usual_lower
        )
        merchant_usual_upper = safe_float(
            row.merchant_usual_upper
        )
        merchant_suspicious_lower = safe_float(
            row.merchant_suspicious_lower
        )
        merchant_suspicious_upper = safe_float(
            row.merchant_suspicious_upper
        )

        outside_usual = int(
            (
                merchant_usual_lower > 0
                and current_amount < merchant_usual_lower
            )
            or (
                merchant_usual_upper > 0
                and current_amount > merchant_usual_upper
            )
        )

        outside_suspicious = int(
            (
                merchant_suspicious_lower > 0
                and current_amount < merchant_suspicious_lower
            )
            or (
                merchant_suspicious_upper > 0
                and current_amount > merchant_suspicious_upper
            )
        )

        merchant_ratio = (
            current_amount / merchant_usual_upper
            if merchant_usual_upper > 0
            else 0.0
        )

        feature_rows.append(
            {
                "transaction_id": row.transaction_id,
                "transaction_time": current_time,
                "model_label": row.model_label,
                "amount": current_amount,
                "hour_of_day": current_time.hour,
                "day_of_week": current_time.dayofweek,
                "is_weekend": int(
                    current_time.dayofweek in [5, 6]
                ),
                "is_new_device": is_new_device,
                "is_new_payee": is_new_payee,
                "spend_24h_including_current":
                    spend_24h_including_current,
                "spend_previous_7d": spend_previous_7d,
                "spend_24h_to_previous_7d_ratio":
                    spending_ratio,
                "spending_spike_rule": int(
                    spend_previous_7d > 0
                    and spend_24h_including_current
                    > spend_previous_7d
                ),
                "distance_from_previous_transaction_km":
                    distance_km,
                "hours_since_previous_transaction":
                    hours_since_previous,
                "travel_speed_kmh": travel_speed_kmh,
                "impossible_travel_rule": int(
                    travel_speed_kmh > 500
                ),
                "merchant_usual_lower":
                    merchant_usual_lower,
                "merchant_usual_upper":
                    merchant_usual_upper,
                "merchant_suspicious_lower":
                    merchant_suspicious_lower,
                "merchant_suspicious_upper":
                    merchant_suspicious_upper,
                "amount_to_merchant_upper_ratio":
                    merchant_ratio,
                "outside_merchant_usual_range":
                    outside_usual,
                "outside_merchant_suspicious_range":
                    outside_suspicious,
                "large_new_payee_rule": int(
                    current_amount > 10_000
                    and is_new_payee == 1
                ),
            }
        )

        history["devices"].add(row.device_id)
        history["payees"].add(payee_key)

        history["transactions"].append(
            {
                "time": current_time,
                "amount": current_amount,
            }
        )

        history["last_transaction"] = {
            "time": current_time,
            "latitude": row.sender_latitude,
            "longitude": row.sender_longitude,
        }

    features = pd.DataFrame(feature_rows)

    numeric_columns = MODEL_FEATURES

    features[numeric_columns] = (
        features[numeric_columns]
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0.0)
    )

    return features


def chronological_split(
    dataframe: pd.DataFrame,
    train_fraction: float = 0.80,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split earliest 80% for training and latest 20% for testing."""

    if not 0 < train_fraction < 1:
        raise ValueError("train_fraction must be between 0 and 1.")

    ordered = dataframe.sort_values(
        ["transaction_time", "transaction_id"]
    ).reset_index(drop=True)

    split_index = int(len(ordered) * train_fraction)

    if split_index == 0 or split_index == len(ordered):
        raise ValueError(
            "Not enough transactions for an 80/20 split."
        )

    return (
        ordered.iloc[:split_index].copy(),
        ordered.iloc[split_index:].copy(),
    )