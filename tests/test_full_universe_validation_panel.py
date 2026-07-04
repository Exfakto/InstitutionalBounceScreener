from PySide6.QtWidgets import QApplication

from services.full_universe_validation_service import (
    FullUniverseValidationIssue,
    FullUniverseValidationResult,
)
from ui.widgets.full_universe_validation_panel import FullUniverseValidationPanel


def app():
    return QApplication.instance() or QApplication([])


def result_with_issue():
    return FullUniverseValidationResult(
        status="warning",
        total_symbols=3,
        processed_symbols=2,
        skipped_symbols=1,
        failed_symbols=0,
        completion_rate=66.6667,
        issues=[
            FullUniverseValidationIssue(
                category="data missing",
                ticker="MSFT",
                severity="warning",
                message="MSFT: missing OHLCV coverage",
            )
        ],
    )


def test_full_universe_validation_panel_renders_result():
    app()
    panel = FullUniverseValidationPanel()

    panel.set_result(result_with_issue())

    assert "Status: warning" in panel.summary_label.text()
    assert "Total: 3" in panel.summary_label.text()
    assert panel.progress_bar.value() == 66
    assert panel.issue_table.rowCount() == 1
    assert panel.issue_table.item(0, 0).text() == "data missing"
    assert panel.issue_table.item(0, 1).text() == "MSFT"


def test_full_universe_validation_panel_empty_state():
    app()
    panel = FullUniverseValidationPanel()

    panel.set_result(None)

    assert panel.message_label.text() == "No full universe validation has been run"
    assert panel.issue_table.isHidden()
    assert panel.progress_bar.value() == 0


def test_full_universe_validation_panel_progress_update():
    app()
    panel = FullUniverseValidationPanel()

    panel.update_progress(
        {
            "total_symbols": 10,
            "processed_symbols": 5,
            "completion_rate": 50,
            "status_message": "Half complete",
        }
    )

    assert panel.progress_bar.value() == 50
    assert panel.message_label.text() == "Half complete"


def test_full_universe_validation_panel_run_uses_controller():
    app()

    class Controller:
        def __init__(self):
            self.callback = None

        def validate_full_universe(self, progress_callback=None):
            self.callback = progress_callback
            progress_callback({"completion_rate": 100, "status_message": "done"})
            return FullUniverseValidationResult(
                status="passed",
                total_symbols=1,
                processed_symbols=1,
                completion_rate=100,
            )

    controller = Controller()
    panel = FullUniverseValidationPanel(controller=controller)

    loaded = panel.run_validation()

    assert controller.callback is not None
    assert loaded.status == "passed"
    assert panel.progress_bar.value() == 100
    assert "Status: passed" in panel.summary_label.text()


def test_full_universe_validation_panel_error_state():
    app()

    class Controller:
        def validate_full_universe(self, progress_callback=None):
            raise RuntimeError("validation unavailable")

    panel = FullUniverseValidationPanel(controller=Controller())

    assert panel.run_validation() is None
    assert panel.message_label.text() == "Unable to run full universe validation"
    assert panel.message_label.property("state") == "error"
