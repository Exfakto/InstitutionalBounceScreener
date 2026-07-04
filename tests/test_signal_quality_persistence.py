from database.manager import DatabaseManager
from services.algorithm_validation_service import (
    SignalQualityAnalysisService,
    SignalQualityRecommendationPersistenceService,
)
from tests.test_signal_quality_analysis_service import enriched_outcome


def test_signal_quality_recommendation_persistence_save_fetch_latest_history(tmp_path):
    db = DatabaseManager(tmp_path / "quality.db")
    report = SignalQualityAnalysisService().analyze(
        [enriched_outcome("A", -5, 62)],
        validation_run_id="validation-run",
    )
    service = SignalQualityRecommendationPersistenceService(db)

    saved = service.save_report(report)
    fetched = db.fetch_signal_quality_recommendation_report(report.report_id)
    latest = service.fetch_latest("validation-run")
    history = service.fetch_history()

    assert saved["report_id"] == report.report_id
    assert fetched["recommendations"]
    assert latest["validation_run_id"] == "validation-run"
    assert history[0]["weak_groups"]


def test_signal_quality_recommendation_persistence_without_repository_is_safe():
    service = SignalQualityRecommendationPersistenceService(None)

    assert service.save_report(object()) is None
    assert service.fetch_latest() is None
    assert service.fetch_history() == []
