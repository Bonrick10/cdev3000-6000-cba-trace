import pytest

from src.contracts import Action
from src.decision import combine_model_labels, decision_for_rule_exit
from src.label import Label


def test_labels_match_database_strings():
    assert Label.parse("rule_alert") is Label.RULE_ALERT
    assert Label.parse("RULE_APPROVAL") is Label.RULE_APPROVAL
    assert Label.CONFIRMED_FRAUDULENT.value == "confirmed_fraudulent"


def test_rule_routes_are_source_aware():
    assert decision_for_rule_exit(Label.RULE_VIOLATION).action is Action.BLOCK
    assert decision_for_rule_exit(Label.RULE_ALERT).action is Action.APPROVE_AND_ALERT
    assert decision_for_rule_exit(Label.RULE_APPROVAL).action is Action.APPROVE


def test_models_take_worst_label_without_blocking():
    decision = combine_model_labels(Label.UNUSUAL, Label.SUSPICIOUS)
    assert decision.label is Label.SUSPICIOUS
    assert decision.action is Action.APPROVE_AND_INVESTIGATE


def test_models_cannot_return_rule_labels():
    with pytest.raises(ValueError):
        combine_model_labels(Label.RULE_ALERT, Label.LEGITIMATE)
