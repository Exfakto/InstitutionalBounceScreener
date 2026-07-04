from database.manager import DatabaseManager
from services.algorithm_validation_service import (
    AlgorithmValidationReport,
    ValidationPersistenceService,
    metrics_for_outcomes,
)
from tests.algorithm_validation_test_utils import sample_outcome


def report(run_id="validation-persist"):
    outcomes = [sample_outcome()]
    return AlgorithmValidationReport(
        run_id=run_id,
        started_at="2024-01-01T00:00:00+00:00",
        completed_at="2024-01-01T00:01:00+00:00",
        start_date="2024-01-01",
        end_date="2024-03-01",
        replay_frequency="monthly",
        signal_count=1,
        outcome_count=1,
        summary_metrics=metrics_for_outcomes(outcomes),
        warnings=["sample warning"],
        errors=[],
        outcomes=outcomes,
    )


def test_validation_persistence_save_fetch_latest_history_and_clear(tmp_path):
    db = DatabaseManager(tmp_path / "validation.db")
    service = ValidationPersistenceService(db)

    saved = service.save_report(report())
    fetched = db.fetch_validation_run("validation-persist")
    latest = service.fetch_latest()
    history = service.fetch_history()

    assert saved["run_id"] == "validation-persist"
    assert fetched["outcomes"][0]["ticker"] == "AAPL"
    assert latest["run_id"] == "validation-persist"
    assert history[0]["warnings"] == ["sample warning"]
    assert service.clear("validation-persist") >= 1
    assert db.fetch_validation_run("validation-persist") is None


def test_validation_persistence_without_repository_is_safe():
    service = ValidationPersistenceService(None)

    assert service.save_report(report()) is None
    assert service.fetch_latest() is None
    assert service.fetch_history() == []
    assert service.clear("missing") == 0
