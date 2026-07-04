from PySide6.QtWidgets import QApplication

from controllers.model_calibration_controller import ModelCalibrationController
from services.model_calibration_history_service import CalibrationHistoryItem
from ui.widgets.model_calibration_history_panel import ModelCalibrationHistoryPanel


def app():
    return QApplication.instance() or QApplication([])


def item(run_id="cal-1"):
    return CalibrationHistoryItem(
        run_id=run_id,
        timestamp="2026-01-02T00:00:00Z",
        model_version="v1",
        sample_size=42,
        overall_score=81.5,
        status="COMPLETED",
        summary="Generated recommendations",
        warnings=[],
        errors=[],
    )


def test_model_calibration_history_panel_renders_history_rows():
    app()
    panel = ModelCalibrationHistoryPanel()

    panel.set_history([item()])

    assert panel.message_label.isHidden()
    assert panel.history_table.rowCount() == 1
    assert panel.history_table.item(0, 0).text() == "2026-01-02T00:00:00Z"
    assert panel.history_table.item(0, 1).text() == "v1"
    assert panel.history_table.item(0, 2).text() == "42"
    assert panel.history_table.item(0, 3).text() == "81.5"
    assert panel.history_table.item(0, 4).text() == "COMPLETED"


def test_model_calibration_history_panel_empty_state():
    app()
    panel = ModelCalibrationHistoryPanel()

    panel.set_history([])

    assert panel.message_label.text() == "No calibration history available"
    assert panel.history_table.isHidden()
    assert panel.history_table.rowCount() == 0


def test_model_calibration_history_panel_selection_updates_details():
    app()
    selected = item("cal-2")

    class Controller:
        def get_calibration_run_details(self, run_id):
            assert run_id == "cal-2"
            return selected

    panel = ModelCalibrationHistoryPanel(controller=Controller())
    panel.set_history([selected])

    panel.history_table.selectRow(0)
    panel.handle_selection_changed()

    assert panel.selected_run == selected
    assert "Run: cal-2" in panel.details_label.text()
    assert "Summary: Generated recommendations" in panel.details_label.text()


def test_model_calibration_history_panel_refresh_uses_controller():
    app()

    class Controller:
        def __init__(self):
            self.called = False

        def get_calibration_history(self):
            self.called = True
            return [item("cal-refresh")]

        def get_calibration_run_details(self, run_id):
            return item(run_id)

    controller = Controller()
    panel = ModelCalibrationHistoryPanel(controller=controller)

    loaded = panel.refresh_history()

    assert controller.called is True
    assert loaded[0].run_id == "cal-refresh"
    assert panel.history_table.item(0, 0).text() == "2026-01-02T00:00:00Z"


def test_model_calibration_history_panel_error_state():
    app()

    class Controller:
        def get_calibration_history(self):
            raise RuntimeError("database unavailable")

    panel = ModelCalibrationHistoryPanel(controller=Controller())

    assert panel.refresh_history() == []
    assert panel.message_label.text() == "Unable to load calibration history"
    assert panel.message_label.property("state") == "error"


def test_model_calibration_controller_history_delegation():
    class HistoryService:
        def __init__(self):
            self.history_called = False
            self.details_run_id = None

        def get_history(self, limit=25, offset=0):
            self.history_called = True
            return [item("cal-history")]

        def get_run_details(self, run_id):
            self.details_run_id = run_id
            return item(run_id)

    history_service = HistoryService()
    controller = ModelCalibrationController(history_service=history_service)

    history = controller.get_calibration_history()
    details = controller.get_calibration_run_details("cal-history")

    assert history_service.history_called is True
    assert history[0].run_id == "cal-history"
    assert history_service.details_run_id == "cal-history"
    assert details.run_id == "cal-history"
