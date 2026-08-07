"""Chronological behavioural features with one training/serving implementation."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from typing import Any, Deque, Dict, Optional, Tuple

import numpy as np
import pandas as pd
from geopy.distance import geodesic

from src.label import Label

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
CATEGORICAL_FEATURES = ["merchant_tag"]
MODEL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

RULE_BYPASS_LABELS = {
    Label.RULE_APPROVAL.value,
    Label.RULE_ALERT.value,
    Label.RULE_VIOLATION.value,
}


def normalise_timestamp(value: Any) -> pd.Timestamp:
    """Return a timezone-aware UTC timestamp from DB or JSON input."""
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert PostgreSQL money/numeric, strings, and nulls safely."""
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
        cleaned = value.replace("$", "").replace(",", "").strip()
        return float(cleaned) if cleaned else default
    return float(value)


def calculate_distance(previous_latitude, previous_longitude, latitude, longitude):
    coordinates = (previous_latitude, previous_longitude, latitude, longitude)
    if any(value is None or pd.isna(value) for value in coordinates):
        return 0.0
    return geodesic(
        (float(previous_latitude), float(previous_longitude)),
        (float(latitude), float(longitude)),
    ).km


def build_feature_values(
    transaction: Dict[str, Any], context: Dict[str, Any]
) -> Dict[str, Any]:
    """Build model features from a transaction and strictly prior context."""
    current_time = normalise_timestamp(transaction["transaction_time"])
    amount = safe_float(transaction["amount"])
    first_time_value = context.get("first_transaction_time")
    first_time = (
        normalise_timestamp(first_time_value) if first_time_value is not None else None
    )
    previous_time_value = context.get("last_transaction_time")
    previous_time = (
        normalise_timestamp(previous_time_value)
        if previous_time_value is not None
        else None
    )

    account_age_days = (
        max((current_time - first_time).total_seconds() / 86_400, 0.0)
        if first_time is not None
        else 0.0
    )
    hours_since_previous = (
        max((current_time - previous_time).total_seconds() / 3_600, 0.0)
        if previous_time is not None
        else 0.0
    )
    distance = calculate_distance(
        context.get("last_transaction_latitude"),
        context.get("last_transaction_longitude"),
        transaction.get("sender_latitude"),
        transaction.get("sender_longitude"),
    )
    prior_mean = safe_float(context.get("prior_mean_amount"))
    prior_std = safe_float(context.get("prior_std_amount"))
    prior_24h_spend = safe_float(context.get("prior_24h_spend"))
    prior_7d_spend = safe_float(context.get("prior_7d_spend"))
    hour_angle = 2 * np.pi * current_time.hour / 24
    day_angle = 2 * np.pi * current_time.dayofweek / 7
    merchant_tag = context.get(
        "merchant_category",
        transaction.get("merchant_tag", transaction.get("merchant_tags")),
    )

    return {
        "amount": amount,
        "log_amount": np.log1p(max(amount, 0.0)),
        "hour_sin": np.sin(hour_angle),
        "hour_cos": np.cos(hour_angle),
        "day_of_week_sin": np.sin(day_angle),
        "day_of_week_cos": np.cos(day_angle),
        "is_weekend": int(current_time.dayofweek >= 5),
        "sender_latitude": safe_float(transaction.get("sender_latitude")),
        "sender_longitude": safe_float(transaction.get("sender_longitude")),
        "account_age_days": account_age_days,
        "prior_transaction_count": safe_float(context.get("prior_transaction_count")),
        "prior_payee_transaction_count": safe_float(
            context.get("prior_payee_transaction_count")
        ),
        "prior_device_transaction_count": safe_float(
            context.get("prior_device_transaction_count")
        ),
        "prior_24h_transaction_count": safe_float(
            context.get("prior_24h_transaction_count")
        ),
        "prior_7d_transaction_count": safe_float(
            context.get("prior_7d_transaction_count")
        ),
        "prior_24h_spend": prior_24h_spend,
        "prior_7d_spend": prior_7d_spend,
        "log_prior_24h_spend": np.log1p(max(prior_24h_spend, 0.0)),
        "log_prior_7d_spend": np.log1p(max(prior_7d_spend, 0.0)),
        "prior_mean_amount": prior_mean,
        "prior_std_amount": prior_std,
        "amount_to_prior_mean_ratio": amount / prior_mean if prior_mean > 0 else 0.0,
        "hours_since_previous_transaction": hours_since_previous,
        "log_hours_since_previous_transaction": np.log1p(hours_since_previous),
        "distance_from_previous_transaction_km": distance,
        "log_distance_from_previous_transaction_km": np.log1p(max(distance, 0.0)),
        "merchant_tag": str(merchant_tag) if merchant_tag is not None else "unknown",
    }


@dataclass
class AccountHistory:
    first_transaction_time: Optional[pd.Timestamp] = None
    count: int = 0
    amount_sum: float = 0.0
    amount_sum_squares: float = 0.0
    payee_counts: Dict[Tuple[int, int], int] = field(default_factory=dict)
    device_counts: Dict[str, int] = field(default_factory=dict)
    recent: Deque[Dict[str, Any]] = field(default_factory=deque)
    last_transaction: Optional[Dict[str, Any]] = None

    def purge(self, current_time: pd.Timestamp) -> None:
        cutoff = current_time - timedelta(days=7)
        while self.recent and self.recent[0]["time"] < cutoff:
            self.recent.popleft()

    def context(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        current_time = normalise_timestamp(transaction["transaction_time"])
        one_day_ago = current_time - timedelta(hours=24)
        recent_24h = [item for item in self.recent if item["time"] >= one_day_ago]
        mean = self.amount_sum / self.count if self.count else 0.0
        variance = (
            max(self.amount_sum_squares / self.count - mean**2, 0.0)
            if self.count
            else 0.0
        )
        payee = (
            int(transaction["receiver_bsb"]),
            int(transaction["receiver_account_number"]),
        )
        device = str(transaction["device_id"]).strip()
        previous = self.last_transaction or {}
        return {
            "first_transaction_time": self.first_transaction_time,
            "prior_transaction_count": self.count,
            "prior_payee_transaction_count": self.payee_counts.get(payee, 0),
            "prior_device_transaction_count": self.device_counts.get(device, 0),
            "prior_24h_transaction_count": len(recent_24h),
            "prior_7d_transaction_count": len(self.recent),
            "prior_24h_spend": sum(item["amount"] for item in recent_24h),
            "prior_7d_spend": sum(item["amount"] for item in self.recent),
            "prior_mean_amount": mean,
            "prior_std_amount": variance**0.5,
            "last_transaction_time": previous.get("time"),
            "last_transaction_latitude": previous.get("latitude"),
            "last_transaction_longitude": previous.get("longitude"),
        }

    def update(self, transaction: Dict[str, Any]) -> None:
        current_time = normalise_timestamp(transaction["transaction_time"])
        amount = safe_float(transaction["amount"])
        payee = (
            int(transaction["receiver_bsb"]),
            int(transaction["receiver_account_number"]),
        )
        device = str(transaction["device_id"]).strip()
        if self.first_transaction_time is None:
            self.first_transaction_time = current_time
        self.count += 1
        self.amount_sum += amount
        self.amount_sum_squares += amount**2
        self.payee_counts[payee] = self.payee_counts.get(payee, 0) + 1
        self.device_counts[device] = self.device_counts.get(device, 0) + 1
        self.recent.append({"time": current_time, "amount": amount})
        self.last_transaction = {
            "time": current_time,
            "latitude": transaction.get("sender_latitude"),
            "longitude": transaction.get("sender_longitude"),
        }


def build_live_features(
    transaction: Dict[str, Any], context: Dict[str, Any]
) -> pd.DataFrame:
    """Build one serving row through the canonical feature function."""
    return pd.DataFrame(
        [build_feature_values(transaction, context)], columns=MODEL_FEATURES
    )


def build_historical_features(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Build each row before updating history, including equal-time isolation."""
    metadata_columns = [
        "transaction_id",
        "transaction_time",
        "original_label",
        "observed_label",
        "rules_label",
        "action",
    ]
    if dataframe.empty:
        return pd.DataFrame(columns=metadata_columns + MODEL_FEATURES)

    required = {
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
        "observed_label",
        "merchant_tag",
        "device_id",
        "rules_label",
    }
    missing = required - set(dataframe.columns)
    if missing:
        raise ValueError(
            f"Historical transactions are missing columns: {sorted(missing)}"
        )

    ordered = dataframe.copy()
    ordered["transaction_time"] = pd.to_datetime(ordered["transaction_time"], utc=True)
    ordered = ordered.sort_values(["transaction_time", "transaction_id"])
    histories: Dict[Tuple[int, int], AccountHistory] = {}
    output = []

    for timestamp, group in ordered.groupby("transaction_time", sort=True):
        rows = group.to_dict(orient="records")
        for row in rows:
            key = (int(row["sender_bsb"]), int(row["sender_account_number"]))
            history = histories.setdefault(key, AccountHistory())
            history.purge(normalise_timestamp(timestamp))
            features = build_feature_values(row, history.context(row))
            output.append(
                {
                    "transaction_id": int(row["transaction_id"]),
                    "transaction_time": normalise_timestamp(timestamp),
                    "original_label": row["label"],
                    "observed_label": row["observed_label"],
                    "rules_label": row.get("rules_label"),
                    "action": row.get("action"),
                    **features,
                }
            )
        for row in rows:
            key = (int(row["sender_bsb"]), int(row["sender_account_number"]))
            is_blocked = row.get("action") == "block" or (
                row.get("action") is None
                and row.get("label") == Label.RULE_VIOLATION.value
            )
            if not is_blocked:
                histories[key].update(row)

    result = pd.DataFrame(output)
    result[NUMERIC_FEATURES] = (
        result[NUMERIC_FEATURES].replace([np.inf, -np.inf], np.nan).astype(float)
    )
    return result.reset_index(drop=True)


def is_model_eligible(dataframe: pd.DataFrame) -> pd.Series:
    """Select transactions that reached the models, including legacy rows safely."""
    rules = dataframe["rules_label"]
    explicit = rules.notna()
    explicit_eligible = explicit & (rules == Label.LEGITIMATE.value)
    legacy_eligible = ~explicit & ~dataframe["original_label"].isin(RULE_BYPASS_LABELS)
    return explicit_eligible | legacy_eligible
