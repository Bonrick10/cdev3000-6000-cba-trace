from contextlib import contextmanager

from src.contracts import Action, FinalDecision, PipelineResult, RuleDecision
from src.label import Label
from src.transactions.repository import persist_pipeline_result


class FakeDB:
    def __init__(self):
        self.calls = []

    @contextmanager
    def transaction(self):
        yield object()

    def execute_sql_file(self, path, params, connection):
        self.calls.append((path.name, params))
        return [{"id": 99}] if path.name == "insert_transaction.sql" else []


def test_pipeline_persistence_writes_attempt_evidence_and_new_device(transaction):
    db = FakeDB()
    result = PipelineResult(
        final=FinalDecision(
            Label.SUSPICIOUS,
            Action.APPROVE_AND_ALERT,
            "models",
            "test",
        ),
        rules=RuleDecision(Label.LEGITIMATE),
        big_model={
            "predicted_label": "suspicious",
            "fraud_probability": 0.95,
            "model_version": "big-1",
        },
        small_model={
            "predicted_label": "unusual",
            "cluster_id": 2,
            "model_version": "small-1",
        },
    )
    transaction_id = persist_pipeline_result(
        transaction, result, {"entity_id": 7, "device_seen_before": False}, db
    )
    assert transaction_id == 99
    assert [name for name, _ in db.calls] == [
        "insert_transaction.sql",
        "insert_decision.sql",
        "insert_device_session.sql",
    ]
    assert db.calls[1][1]["action"] == "approve_and_alert"
    assert db.calls[1][1]["decision_source"] == "models"
    assert db.calls[1][1]["big_model_evidence"] is not None


def test_blocked_attempt_does_not_register_unseen_device(transaction):
    db = FakeDB()
    result = PipelineResult(
        final=FinalDecision(
            Label.RULE_VIOLATION,
            Action.BLOCK,
            "rules",
            "blocking rule",
        ),
        rules=RuleDecision(Label.RULE_VIOLATION, ["impossible_travel"]),
    )
    persist_pipeline_result(
        transaction, result, {"entity_id": 7, "device_seen_before": False}, db
    )
    assert [name for name, _ in db.calls] == [
        "insert_transaction.sql",
        "insert_decision.sql",
    ]
