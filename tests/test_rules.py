from copy import deepcopy
from datetime import timedelta

from src.label import Label
from src.rules.context import SQL_PATH
from src.rules.rule_enum import RuleEnum
from src.rules.rules import check_rules


def test_context_query_uses_split_prediction_and_truth_schema():
    sql = SQL_PATH.read_text(encoding="utf-8")
    assert "txn.predicted_label IS DISTINCT FROM 'rule_violation'" in sql
    assert "txn.label" not in sql


def test_safe_transaction_passes_to_models(transaction, safe_context):
    result = check_rules(transaction, safe_context)
    assert result.label is Label.LEGITIMATE
    assert result.reasons == []


def test_recurring_transaction_is_rule_approval(transaction, safe_context):
    safe_context["num_recurring"] = 5
    result = check_rules(transaction, safe_context)
    assert result.label is Label.RULE_APPROVAL
    assert RuleEnum.RECURRING_TRANSACTION.value in result.reasons


def test_unseen_device_is_rule_alert(transaction, safe_context):
    safe_context["device_seen_before"] = False
    result = check_rules(transaction, safe_context)
    assert result.label is Label.RULE_ALERT
    assert RuleEnum.UNSEEN_DEVICE.value in result.reasons


def test_24_hour_velocity_is_rule_alert(transaction, safe_context):
    safe_context["prior_24h_spend"] = 950
    result = check_rules(transaction, safe_context)
    assert result.label is Label.RULE_ALERT
    assert RuleEnum.EXCEED_7D_TOTAL.value in result.reasons


def test_large_new_payee_is_rule_alert(transaction, safe_context):
    transaction["amount"] = 10_001
    safe_context["is_new_payee"] = True
    safe_context["prior_7d_spend"] = 20_000
    safe_context["usual_threshold_upper"] = 20_000
    safe_context["suspicious_threshold_upper"] = 30_000
    result = check_rules(transaction, safe_context)
    assert result.label is Label.RULE_ALERT
    assert RuleEnum.LARGE_AMOUNT_NEW_PAYEE.value in result.reasons


def test_impossible_travel_is_blocking_rule_violation(transaction, safe_context):
    safe_context["last_transaction_time"] = transaction["transaction_time"] - timedelta(
        minutes=30
    )
    safe_context["last_transaction_latitude"] = -37.8136
    safe_context["last_transaction_longitude"] = 144.9631
    result = check_rules(transaction, safe_context)
    assert result.label is Label.RULE_VIOLATION
    assert RuleEnum.IMPOSSIBLE_TRAVEL.value in result.reasons


def test_far_merchant_amount_is_blocking_and_beats_alert(transaction, safe_context):
    changed = deepcopy(transaction)
    changed["amount"] = 3_000
    safe_context["device_seen_before"] = False
    safe_context["num_recurring"] = 5
    result = check_rules(changed, safe_context)
    assert result.label is Label.RULE_VIOLATION
    assert result.reasons == [RuleEnum.MERCHANT_TYPE_SUSPICIOUS_RANGE.value]


def test_alert_beats_rule_approval(transaction, safe_context):
    safe_context["num_recurring"] = 5
    safe_context["device_seen_before"] = False
    result = check_rules(transaction, safe_context)
    assert result.label is Label.RULE_ALERT
    assert RuleEnum.UNSEEN_DEVICE.value in result.reasons


def test_fresh_account_skips_history_dependent_alerts(transaction, safe_context):
    safe_context.update(
        {
            "first_transaction_time": None,
            "prior_transaction_count": 0,
            "device_seen_before": False,
            "is_new_payee": True,
            "prior_24h_spend": 0,
            "prior_7d_spend": 0,
        }
    )
    result = check_rules(transaction, safe_context)
    assert result.label is Label.LEGITIMATE


def test_normal_merchant_outlier_is_rule_alert(transaction, safe_context):
    transaction["amount"] = 750
    safe_context["prior_7d_spend"] = 2_000
    result = check_rules(transaction, safe_context)
    assert result.label is Label.RULE_ALERT
    assert RuleEnum.MERCHANT_TYPE_UNUSUAL_RANGE.value in result.reasons
