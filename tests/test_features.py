import numpy as np
import pandas as pd

from src.features import (
    MODEL_FEATURES,
    build_historical_features,
    build_live_features,
    is_model_eligible,
)


def _raw_rows():
    return pd.DataFrame(
        [
            {
                "transaction_id": 1,
                "sender_bsb": 100001,
                "sender_account_number": 1,
                "receiver_bsb": 100002,
                "receiver_account_number": 2,
                "amount": 100,
                "transaction_time": "2025-01-01T10:00:00Z",
                "sender_latitude": -33.8,
                "sender_longitude": 151.2,
                "label": "legitimate",
                "merchant_tag": "5411",
                "device_id": "device",
                "rules_label": "legitimate",
                "action": "approve",
            },
            {
                "transaction_id": 2,
                "sender_bsb": 100001,
                "sender_account_number": 1,
                "receiver_bsb": 100002,
                "receiver_account_number": 2,
                "amount": 120,
                "transaction_time": "2025-01-02T10:00:00Z",
                "sender_latitude": -33.9,
                "sender_longitude": 151.1,
                "label": "confirmed_fraudulent",
                "merchant_tag": "5411",
                "device_id": "device",
                "rules_label": "legitimate",
                "action": "approve_and_investigate",
            },
        ]
    )


def test_historical_and_live_features_have_parity():
    historical = build_historical_features(_raw_rows())
    transaction = _raw_rows().iloc[1].to_dict()
    live = build_live_features(
        transaction,
        {
            "first_transaction_time": "2025-01-01T10:00:00Z",
            "prior_transaction_count": 1,
            "prior_payee_transaction_count": 1,
            "prior_device_transaction_count": 1,
            "prior_24h_transaction_count": 1,
            "prior_7d_transaction_count": 1,
            "prior_24h_spend": 100,
            "prior_7d_spend": 100,
            "prior_mean_amount": 100,
            "prior_std_amount": 0,
            "last_transaction_time": "2025-01-01T10:00:00Z",
            "last_transaction_latitude": -33.8,
            "last_transaction_longitude": 151.2,
        },
    )
    for feature in MODEL_FEATURES:
        if feature == "merchant_tag":
            assert historical.loc[1, feature] == live.loc[0, feature]
        else:
            assert np.isclose(historical.loc[1, feature], live.loc[0, feature])


def test_blocked_attempt_does_not_update_later_history():
    rows = _raw_rows()
    rows.loc[0, "label"] = "rule_violation"
    rows.loc[0, "rules_label"] = "rule_violation"
    rows.loc[0, "action"] = "block"
    features = build_historical_features(rows)
    assert features.loc[1, "prior_transaction_count"] == 0
    assert is_model_eligible(features).tolist() == [False, True]
