from database.manager import DatabaseManager
from services.model_calibration_service import (
    CalibrationRecommendation,
    CalibrationRepository,
    CalibrationRun,
)


def test_calibration_models_hold_required_fields():
    run = CalibrationRun(
        run_id="cal-1",
        started_at="2026-01-01T00:00:00Z",
        completed_at="2026-01-01T00:05:00Z",
        status="COMPLETED",
        source_validation_run_id="validation-1",
        source_signal_quality_run_id="quality-1",
        summary="Threshold review complete",
        warnings=["watch sample size"],
        errors=[],
    )
    recommendation = CalibrationRecommendation(
        recommendation_id="rec-1",
        run_id="cal-1",
        category="minimum_final_score",
        current_value=70,
        recommended_value=76,
        rationale="Weak expectancy below 75",
        expected_impact="Reduce low-quality signals",
        confidence="MEDIUM",
    )

    assert run.source_validation_run_id == "validation-1"
    assert run.warnings == ["watch sample size"]
    assert recommendation.current_value == 70
    assert recommendation.recommended_value == 76


def test_calibration_tables_are_created(tmp_path):
    db = DatabaseManager(tmp_path / "calibration.db")

    db.cursor.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        ("calibration_runs",),
    )
    assert db.cursor.fetchone()["name"] == "calibration_runs"

    db.cursor.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
        ("calibration_recommendations",),
    )
    assert db.cursor.fetchone()["name"] == "calibration_recommendations"


def test_calibration_repository_save_fetch_latest_history_and_clear(tmp_path):
    repository = CalibrationRepository(DatabaseManager(tmp_path / "calibration.db"))
    run = CalibrationRun(
        run_id="cal-1",
        started_at="2026-01-01T00:00:00Z",
        completed_at="2026-01-01T00:05:00Z",
        status="COMPLETED",
        source_validation_run_id="validation-1",
        source_signal_quality_run_id="quality-1",
        summary="Calibration report",
        warnings=["small sample"],
    )
    recommendations = [
        CalibrationRecommendation(
            recommendation_id="rec-1",
            run_id="cal-1",
            category="minimum_final_score",
            current_value=70,
            recommended_value=75,
            rationale="Low score bucket underperformed",
            expected_impact="Improve expectancy",
            confidence="HIGH",
        ),
        CalibrationRecommendation(
            recommendation_id="rec-2",
            run_id="cal-1",
            category="confidence_requirement",
            current_value="LOW_ALLOWED",
            recommended_value="MEDIUM_REQUIRED",
            rationale="Low confidence signals had negative expectancy",
            expected_impact="Reduce drawdown",
            confidence="MEDIUM",
        ),
    ]

    saved_run = repository.save_run(run)
    saved_recommendations = repository.save_recommendations("cal-1", recommendations)

    assert saved_run["run_id"] == "cal-1"
    assert saved_run["warnings"] == ["small sample"]
    assert len(saved_recommendations) == 2
    assert saved_recommendations[0]["current_value"] == 70
    assert saved_recommendations[1]["recommended_value"] == "MEDIUM_REQUIRED"

    latest = repository.fetch_latest_run()
    assert latest["run_id"] == "cal-1"
    assert len(latest["recommendations"]) == 2

    history = repository.fetch_run_history()
    assert [item["run_id"] for item in history] == ["cal-1"]

    assert repository.clear_run("cal-1") == 1
    assert repository.fetch_latest_run() is None
    assert repository.fetch_recommendations("cal-1") == []


def test_calibration_recommendations_replace_existing_for_run(tmp_path):
    repository = CalibrationRepository(DatabaseManager(tmp_path / "calibration.db"))
    repository.save_run(
        CalibrationRun(run_id="cal-1", started_at="2026-01-01T00:00:00Z")
    )
    repository.save_recommendations(
        "cal-1",
        [
            CalibrationRecommendation(
                recommendation_id="rec-old",
                run_id="cal-1",
                category="minimum_final_score",
                current_value=65,
                recommended_value=70,
            )
        ],
    )

    refreshed = repository.save_recommendations(
        "cal-1",
        [
            CalibrationRecommendation(
                recommendation_id="rec-new",
                run_id="cal-1",
                category="minimum_component_score",
                current_value={"technical": 40},
                recommended_value={"technical": 55},
                confidence="LOW",
            )
        ],
    )

    assert len(refreshed) == 1
    assert refreshed[0]["recommendation_id"] == "rec-new"
    assert refreshed[0]["current_value"] == {"technical": 40}
    assert refreshed[0]["recommended_value"] == {"technical": 55}


def test_calibration_repository_without_database_is_safe():
    repository = CalibrationRepository(None)

    assert repository.save_run(CalibrationRun("cal-1", "2026-01-01T00:00:00Z")) is None
    assert repository.save_recommendations("cal-1", []) == []
    assert repository.fetch_latest_run() is None
    assert repository.fetch_recommendations("cal-1") == []
    assert repository.fetch_run_history() == []
    assert repository.clear_run("cal-1") == 0
