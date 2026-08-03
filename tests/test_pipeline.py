from threading import Barrier

from src.new_transaction import process_transaction


def test_rule_alert_exits_without_calling_models(transaction, safe_context):
    safe_context["device_seen_before"] = False

    def must_not_run(_):
        raise AssertionError("Models must be bypassed for rule_alert")

    result = process_transaction(
        transaction,
        context=safe_context,
        persist=False,
        big_predictor=must_not_run,
        small_predictor=must_not_run,
    )
    assert result["final_label"] == "rule_alert"
    assert result["action"] == "approve_and_alert"
    assert result["big_model"] is None
    assert result["small_model"] is None


def test_both_models_run_and_worst_label_wins(transaction, safe_context):
    result = process_transaction(
        transaction,
        context=safe_context,
        persist=False,
        big_predictor=lambda _: {
            "predicted_label": "unusual",
            "fraud_probability": 0.8,
            "model_version": "big-1",
        },
        small_predictor=lambda _: {
            "predicted_label": "suspicious",
            "cluster_id": 3,
            "model_version": "small-1",
        },
    )
    assert result["final_label"] == "suspicious"
    assert result["action"] == "approve_and_alert"
    assert result["rules"]["label"] == "legitimate"
    assert result["model_versions"] == {
        "big_model": "big-1",
        "small_model": "small-1",
    }


def test_model_predictions_run_concurrently(transaction, safe_context):
    both_started = Barrier(2, timeout=2)

    def predictor(_):
        both_started.wait()
        return {"predicted_label": "legitimate"}

    result = process_transaction(
        transaction,
        context=safe_context,
        persist=False,
        big_predictor=predictor,
        small_predictor=predictor,
    )
    assert result["final_label"] == "legitimate"


def test_process_transaction_does_not_mutate_input(transaction, safe_context):
    original = dict(transaction)
    process_transaction(
        transaction,
        context=safe_context,
        persist=False,
        big_predictor=lambda _: {"predicted_label": "legitimate"},
        small_predictor=lambda _: {"predicted_label": "legitimate"},
    )
    assert transaction == original
