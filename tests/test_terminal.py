from src.terminal import format_pipeline_result


def test_formats_model_routed_pipeline_result():
    result = {
        "transaction_id": None,
        "final_label": "suspicious",
        "action": "approve_and_alert",
        "decision_source": "models",
        "decision_reason": "maximum severity of big=legitimate and small=suspicious",
        "rules": {"label": "legitimate", "reasons": []},
        "big_model": {
            "predicted_label": "legitimate",
            "risk_score": 34.45,
            "unusual_threshold": 0.7,
            "suspicious_threshold": 0.9,
        },
        "small_model": {
            "predicted_label": "suspicious",
            "cluster_id": 0,
            "cluster_size": 590,
            "reported_fraud_count": 74,
            "reported_fraud_percentage": 12.5424,
            "fraud_rate_lower_bound": 10.1098,
            "assignment_distance": 7.602094,
            "membership_confidence": 0.23027,
        },
    }

    output = format_pipeline_result(result, persisted=False)

    assert "FRAUD DETECTION PIPELINE RESULT" in output
    assert "SUSPICIOUS  →  APPROVE AND ALERT" in output
    assert "Fraud risk     34.45%" in output
    assert "74/590 reported fraud" in output
    assert "DRY RUN" in output
    assert "\033[" not in output


def test_formats_rule_exit_without_models():
    result = {
        "transaction_id": 42,
        "final_label": "rule_violation",
        "action": "block",
        "decision_source": "rules",
        "decision_reason": "rules engine blocked transaction",
        "rules": {
            "label": "rule_violation",
            "reasons": ["merchant_type_suspicious_range"],
        },
        "big_model": None,
        "small_model": None,
    }

    output = format_pipeline_result(result, persisted=True)

    assert "Triggered      merchant_type_suspicious_range" in output
    assert output.count("NOT RUN (rules exit)") == 2
    assert "transaction #42" in output
