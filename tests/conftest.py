from datetime import datetime, timezone

import pandas as pd
import pytest

from src.features import MODEL_FEATURES


@pytest.fixture
def transaction():
    return {
        "sender_bsb": 100001,
        "sender_account_number": 1,
        "receiver_bsb": 100002,
        "receiver_account_number": 2,
        "amount": 100.0,
        "transaction_time": datetime(2025, 1, 10, 12, 0, tzinfo=timezone.utc),
        "sender_latitude": -33.8688,
        "sender_longitude": 151.2093,
        "merchant_tags": 5411,
        "device_id": "known-device",
    }


@pytest.fixture
def safe_context():
    return {
        "entity_id": 10,
        "device_seen_before": True,
        "is_new_payee": False,
        "prior_transaction_count": 10,
        "first_transaction_time": datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        "prior_mean_amount": 90.0,
        "prior_std_amount": 15.0,
        "prior_24h_transaction_count": 1,
        "prior_7d_transaction_count": 5,
        "prior_24h_spend": 100.0,
        "prior_7d_spend": 1_000.0,
        "prior_payee_transaction_count": 2,
        "prior_device_transaction_count": 5,
        "last_transaction_time": datetime(2025, 1, 9, 12, 0, tzinfo=timezone.utc),
        "last_transaction_latitude": -33.86,
        "last_transaction_longitude": 151.20,
        "num_recurring": 0,
        "suspicious_threshold_lower": 1.0,
        "usual_threshold_lower": 5.0,
        "usual_threshold_upper": 500.0,
        "suspicious_threshold_upper": 2_000.0,
    }


def canonical_rows(count=40):
    rows = []
    for index in range(count):
        row = {}
        for column in MODEL_FEATURES:
            row[column] = (
                "electronics" if column == "merchant_tag" else float(index + 1)
            )
        row["transaction_id"] = index + 1
        row["transaction_time"] = pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(
            days=index
        )
        row["rules_label"] = "legitimate"
        row["original_label"] = "confirmed_fraudulent" if index < 12 else "legitimate"
        rows.append(row)
    return pd.DataFrame(rows)
