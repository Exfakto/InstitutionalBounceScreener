from database.manager import DatabaseManager
from services.model_calibration_history_service import ModelCalibrationHistoryService
from services.model_calibration_service import CalibrationRun


def test_model_calibration_history_service_retrieves_and_sorts_newest_first():
    class Repository:
        def fetch_calibration_run_history(self, limit=25, offset=0):
            assert limit == 25
            assert offset == 0
            return [
                {
                    "run_id": "old",
                    "completed_at": "2026-01-01T00:00:00Z",
                    "status": "COMPLETED",
                    "summary_metrics": {"model_version": "v1", "sample_size": 10, "overall_score": 55},
                },
                {
                    "run_id": "new",
                    "completed_at": "2026-01-03T00:00:00Z",
                    "status": "COMPLETED",
                    "summary_metrics": {"model_version": "v2", "sample_size": 20, "overall_score": 75},
                },
            ]

    history = ModelCalibrationHistoryService(Repository()).get_history()

    assert [item.run_id for item in history] == ["new", "old"]
    assert history[0].model_version == "v2"
    assert history[0].sample_size == 20
    assert history[0].overall_score == 75.0


def test_model_calibration_history_service_empty_history_is_safe():
    class Repository:
        def fetch_calibration_run_history(self, limit=25, offset=0):
            return []

    assert ModelCalibrationHistoryService(Repository()).get_history() == []
    assert ModelCalibrationHistoryService(None).get_history() == []


def test_model_calibration_history_service_fetches_run_details():
    class Repository:
        def fetch_calibration_run(self, run_id):
            assert run_id == "cal-1"
            return {
                "run_id": "cal-1",
                "completed_at": "2026-01-02T00:00:00Z",
                "status": "NO_RECOMMENDATIONS",
                "summary": "No changes",
                "source_validation_run_id": "validation-1",
                "warnings": ["small sample"],
                "errors": [],
            }

    details = ModelCalibrationHistoryService(Repository()).get_run_details("cal-1")

    assert details.run_id == "cal-1"
    assert details.model_version == "validation-1"
    assert details.summary == "No changes"
    assert details.warnings == ["small sample"]


def test_model_calibration_history_service_uses_existing_persistence(tmp_path):
    db = DatabaseManager(tmp_path / "history.db")
    db.save_calibration_run(
        CalibrationRun(
            run_id="cal-1",
            started_at="2026-01-01T00:00:00Z",
            completed_at="2026-01-01T00:05:00Z",
            status="COMPLETED",
            source_validation_run_id="validation-1",
            summary="Generated 1 recommendation.",
        )
    )

    history = ModelCalibrationHistoryService(db).get_history()

    assert len(history) == 1
    assert history[0].run_id == "cal-1"
    assert history[0].model_version == "validation-1"
    assert history[0].status == "COMPLETED"
