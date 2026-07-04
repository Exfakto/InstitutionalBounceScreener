from PySide6.QtWidgets import QApplication

from services.screening_diagnostics_service import (
    ScreeningDiagnosticMessage,
    ScreeningDiagnosticsResult,
    ScreeningStageDiagnostic,
)
from ui.widgets.screening_diagnostics_panel import ScreeningDiagnosticsPanel


def app():
    return QApplication.instance() or QApplication([])


def diagnostics():
    return ScreeningDiagnosticsResult(
        run_id="run-1",
        overall_status="warning",
        symbol_count=10,
        total_time_seconds=12.5,
        warning_count=1,
        error_count=0,
        stages=[
            ScreeningStageDiagnostic(
                "universe_loading",
                "Universe loading",
                "passed",
                timing_seconds=1.0,
                cache_usage="80%",
                warning_count=1,
            ),
            ScreeningStageDiagnostic(
                "support_detection",
                "Support detection",
                "warning",
                timing_seconds=45.0,
                cache_usage="N/A",
                warning_count=1,
            ),
        ],
        messages=[
            ScreeningDiagnosticMessage(
                severity="warning",
                message="Support detection is unusually slow.",
                recommended_action="Review cache coverage.",
            )
        ],
    )


def test_screening_diagnostics_panel_renders_result():
    app()
    panel = ScreeningDiagnosticsPanel()

    panel.set_diagnostics(diagnostics())

    assert panel.message_label.isHidden()
    assert "Run: run-1" in panel.summary_label.text()
    assert "Status: warning" in panel.summary_label.text()
    assert panel.stage_table.rowCount() == 2
    assert panel.stage_table.item(0, 0).text() == "Universe loading"
    assert panel.stage_table.item(1, 1).text() == "warning"
    assert panel.message_table.rowCount() == 1
    assert panel.message_table.item(0, 2).text() == "Review cache coverage."


def test_screening_diagnostics_panel_empty_state():
    app()
    panel = ScreeningDiagnosticsPanel()

    panel.set_diagnostics(None)

    assert panel.message_label.text() == "No screening diagnostics available"
    assert panel.stage_table.isHidden()
    assert panel.message_table.isHidden()


def test_screening_diagnostics_panel_refresh_uses_controller():
    app()

    class Controller:
        def __init__(self):
            self.called = False

        def get_screening_diagnostics(self):
            self.called = True
            return diagnostics()

    controller = Controller()
    panel = ScreeningDiagnosticsPanel(controller=controller)

    loaded = panel.refresh_diagnostics()

    assert controller.called is True
    assert loaded.run_id == "run-1"
    assert panel.stage_table.rowCount() == 2


def test_screening_diagnostics_panel_error_state():
    app()

    class Controller:
        def get_screening_diagnostics(self):
            raise RuntimeError("diagnostics unavailable")

    panel = ScreeningDiagnosticsPanel(controller=Controller())

    assert panel.refresh_diagnostics() is None
    assert panel.message_label.text() == "Unable to load screening diagnostics"
    assert panel.message_label.property("state") == "error"
