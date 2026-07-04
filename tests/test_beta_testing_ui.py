from types import SimpleNamespace

from PySide6.QtWidgets import QApplication, QMainWindow

from services.beta_testing_service import BetaTestRun, BetaWorkflowResult, CandidateReviewItem
from ui.main_window import MainWindow
from ui.widgets.screening_results_panel import ScreeningResultsPanel


def app():
    return QApplication.instance() or QApplication([])


def test_beta_testing_panel_construction_and_result_display():
    app()
    panel = ScreeningResultsPanel()

    assert panel.run_beta_workflow_button.text() == "Run Beta Workflow"
    assert panel.generate_beta_review_pack_button.text() == "Generate Review Pack"
    assert panel.export_beta_report_button.text() == "Export Beta Report"

    result = BetaWorkflowResult(
        run=BetaTestRun(
            run_id="beta-ui",
            started_at="2026-01-01T00:00:00+00:00",
            status="PASS",
            scanned_count=3,
            candidates_count=1,
        ),
        review_pack=[CandidateReviewItem("AAPL", "A", 90, "Elite")],
    )
    panel.set_beta_workflow_result(result)

    assert "PASS" in panel.beta_summary_label.text()
    assert panel.beta_review_table.rowCount() == 1
    assert panel.export_beta_report_button.isEnabled() is True


def test_main_window_generate_beta_review_pack_uses_current_candidates():
    app()
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window.screening_results_panel = ScreeningResultsPanel()
    window.screening_results_panel.current_candidates = [
        {"ticker": "AAPL", "rank": 1, "final_score": 90, "grade": "A", "setup_label": "Elite"}
    ]
    window._screening_repository = None
    window.controller = SimpleNamespace(market=None)
    window.chart_controller = SimpleNamespace(chart_data_service=None)

    pack = MainWindow.generate_beta_review_pack(window)

    assert len(pack) == 1
    assert "Generated review pack" in window.screening_results_panel.beta_status_label.text()


def test_main_window_beta_workflow_completed_updates_panel():
    app()
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window.screening_results_panel = ScreeningResultsPanel()
    result = BetaWorkflowResult(
        run=BetaTestRun("beta", "2026-01-01T00:00:00+00:00", status="PASS"),
        review_pack=[CandidateReviewItem("AAPL", "A", 90, "Elite")],
    )

    returned = MainWindow.handle_beta_workflow_completed(window, result)

    assert returned is result
    assert window.beta_testing_worker is None
    assert window.screening_results_panel.beta_review_table.rowCount() == 1
