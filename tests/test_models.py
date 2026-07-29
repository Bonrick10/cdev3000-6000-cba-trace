from conftest import canonical_rows

from src.big_model.predict import predict_transaction as predict_big
from src.big_model.train import fit_model
from src.features import MODEL_FEATURES
from src.small_model.predict import predict_transaction as predict_small
from src.small_model.statistics import risk_label, wilson_lower_bound
from src.small_model.train import fit_small_model


def test_big_model_fits_pipeline_and_returns_probability():
    data = canonical_rows(40)
    data["target"] = [1 if index < 12 else 0 for index in range(40)]
    model = fit_model(data)
    result = predict_big(
        data.iloc[[0]][MODEL_FEATURES],
        {"model": model, "metadata": {"version": "test-big"}},
    )
    assert 0 <= result["fraud_probability"] <= 1
    assert result["model_version"] == "test-big"
    assert result["predicted_label"] in {"legitimate", "unusual", "suspicious"}


def test_small_model_is_fraud_derived_and_returns_versioned_evidence():
    data = canonical_rows(40)
    bundle = fit_small_model(data)
    result = predict_small(data.iloc[[0]][MODEL_FEATURES], bundle)
    assert bundle["metadata"]["confirmed_fraud_training_rows"] == 12
    assert result["model_version"] == bundle["metadata"]["version"]
    assert result["predicted_label"] in {"legitimate", "unusual", "suspicious"}
    assert 0 <= result["membership_confidence"] <= 1


def test_supported_concentration_is_not_treated_as_certain_fraud():
    statistic = {
        "cluster_size": 30,
        "confirmed_fraud_count": 12,
        "smoothed_fraud_percentage": 40.625,
        "fraud_rate_lower_bound": wilson_lower_bound(12, 30) * 100,
    }
    assert risk_label(statistic) == "suspicious"


def test_model_features_do_not_contain_rule_outputs():
    assert not any("rule" in name or "label" in name for name in MODEL_FEATURES)
