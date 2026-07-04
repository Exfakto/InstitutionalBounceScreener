from PySide6.QtWidgets import QApplication, QMainWindow

from ui.algorithm_validation_worker import AlgorithmValidationWorker
from ui.main_window import MainWindow
from ui.widgets.screening_results_panel import ScreeningResultsPanel


def app():
    return QApplication.instance() or QApplication([])


def test_algorithm_validation_panel_controls_exist():
    app()
    panel = ScreeningResultsPanel()

    assert panel.run_algorithm_validation_button.text() == "Run Validation"
    assert panel.run_weight_optimization_button.text() == "Run Weight Optimization"
    assert panel.export_algorithm_validation_button.text() == "Export Report"
    assert panel.algorithm_validation_config_from_ui()["benchmark_ticker"] == "SPY"


def test_algorithm_validation_panel_report_updates_labels():
    app()
    panel = ScreeningResultsPanel()
    report = {
        "signal_count": 3,
        "outcome_count": 2,
        "summary_metrics": {"win_rate": 0.5, "expectancy": 1.25},
        "best_weight_configs": [
            {"weights": {"support": 0.4, "bounce": 0.2}, "score": 12.5}
        ],
        "warnings": [],
        "errors": [],
    }

    panel.set_algorithm_validation_report(report)

    assert "3 signals" in panel.algorithm_validation_summary_label.text()
    assert panel.export_algorithm_validation_button.isEnabled()


def test_algorithm_validation_worker_emits_completed_for_fake_service():
    app()

    class FakeService:
        def run_validation(self, **kwargs):
            assert callable(kwargs["progress_callback"])
            assert callable(kwargs["cancellation_callback"])
            return {"run_id": "fake", "signal_count": 1}

    completed = []
    worker = AlgorithmValidationWorker(repository=object(), service=FakeService())
    worker.completed_signal.connect(completed.append)

    worker.run()

    assert completed == [{"run_id": "fake", "signal_count": 1}]


def test_main_window_starts_algorithm_validation_worker_with_config():
    app()
    window = MainWindow.__new__(MainWindow)
    QMainWindow.__init__(window)
    window.screening_results_panel = ScreeningResultsPanel()
    window._screening_repository = object()
    window._algorithm_validation_service = object()

    worker = MainWindow.start_algorithm_validation_worker(
        window,
        {"start_date": "2024-01-01", "end_date": "2024-02-01"},
    )

    assert worker is not None
    assert window.screening_results_panel.cancel_algorithm_validation_button.isEnabled()
    worker.request_cancel()
    worker.quit()
    worker.wait(100)
