import src.report_transaction as report_module


def test_report_records_correction_and_refreshes_statistics(monkeypatch):
    monkeypatch.setattr(
        report_module,
        "correct_transaction",
        lambda transaction_id, label, correction_time, db: {
            "transaction_id": transaction_id,
            "new_label": label.value,
        },
    )
    monkeypatch.setattr(
        report_module,
        "rebuild_from_database",
        lambda db: {
            "metadata": {"version": "small-1"},
            "cluster_statistics": [{"cluster_id": 0}],
        },
    )
    result = report_module.report_transaction(12, "confirmed_fraudulent")
    assert result["correction"]["new_label"] == "confirmed_fraudulent"
    assert result["small_model_statistics"]["status"] == "rebuilt"
    assert result["cluster_rebuild_completed"] is True


def test_committed_correction_is_returned_when_refresh_fails(monkeypatch):
    monkeypatch.setattr(
        report_module,
        "correct_transaction",
        lambda *args: {"transaction_id": 12},
    )

    def fail_refresh(db):
        raise ValueError("population unavailable")

    monkeypatch.setattr(report_module, "rebuild_from_database", fail_refresh)
    result = report_module.report_transaction(12, "confirmed_fraudulent")
    assert result["correction"]["transaction_id"] == 12
    assert result["small_model_statistics"] == {
        "status": "rebuild_failed",
        "message": "population unavailable",
    }
    assert result["cluster_rebuild_completed"] is False


def test_legitimate_confirmation_does_not_rebuild(monkeypatch):
    monkeypatch.setattr(
        report_module,
        "correct_transaction",
        lambda *args: {"transaction_id": 12},
    )
    monkeypatch.setattr(
        report_module,
        "rebuild_from_database",
        lambda db: (_ for _ in ()).throw(AssertionError("unexpected rebuild")),
    )
    result = report_module.report_transaction(12, "confirmed_legitimate")
    assert result["small_model_statistics"] == {"status": "not_requested"}
    assert result["cluster_rebuild_completed"] is False
