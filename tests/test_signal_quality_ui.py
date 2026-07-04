from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QMainWindow

from database.manager import DatabaseManager
from services.algorithm_validation_service import AlgorithmValidationReport, metrics_for_outcomes
from tests.test_signal_quality_analysis_service import enriched_outcome
from ui.main_window import MainWindow
from ui.widgets.screening_results_panel import ScreeningResultsPanel


def app():
    return QApplication.instance() or QApplication([])


def validation_report():
    outcomes = [enriched_outcome("A", -5, 62)]
    return AlgorithmValidationReport(
        run_id="validation-run",
        started_at="2026-01-01T00:00:00+00:00",
        completed_at="2026-01-01T00:01:00+00:00",
        start_date="2026-01-01",
        end_date="2026-02-01",
        replay_frequency="weekly",
        signal_count=1,
        outcome_count=1,
        summary_metrics=metrics_for_outcomes(outcomes),
        outcomes=outcomes,
    )


def test_signal_quality_ui_construction_and_report_display():
    app()
    panel = ScreeningResultsPanel()
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window.screening_results_panel = panel
    window._screening_repository = None
    window.controller = SimpleNamespace(market=None)

    quality_report = MainWindow.update_signal_quality_recommendations(
        window,
        validation_report(),
    )

    assert quality_report.recommendations
    assert "Weak groups:" in panel.signal_quality_weak_groups_label.text()
    assert "Recommended thresholds:" in panel.signal_quality_recommendations_label.text()
    assert panel.export_signal_quality_recommendations_button.isEnabled() is True


def test_signal_quality_ui_persists_recommendation_report(tmp_path):
    app()
    panel = ScreeningResultsPanel()
    db = DatabaseManager(tmp_path / "quality.db")
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window.screening_results_panel = panel
    window._screening_repository = db

    quality_report = MainWindow.update_signal_quality_recommendations(
        window,
        validation_report(),
    )

    fetched = db.fetch_latest_signal_quality_recommendation_report("validation-run")
    assert fetched["report_id"] == quality_report.report_id
