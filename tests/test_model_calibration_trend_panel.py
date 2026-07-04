from PySide6.QtWidgets import QApplication

from controllers.model_calibration_controller import ModelCalibrationController
from services.model_calibration_trend_service import (
    CalibrationTrendPoint,
    CalibrationTrendSeries,
)
from ui.widgets.model_calibration_trend_panel import ModelCalibrationTrendPanel


def app():
    return QApplication.instance() or QApplication([])


def trend():
    return CalibrationTrendSeries(
        points=[
            CalibrationTrendPoint(
                run_id="cal-1",
                timestamp="2026-01-01T00:00:00Z",
                overall_score=70,
                precision=0.6,
                recall=0.5,
                f1_score=0.55,
                confidence_calibration_error=0.1,
                sample_size=100,
            ),
            CalibrationTrendPoint(
                run_id="cal-2",
                timestamp="2026-01-02T00:00:00Z",
                overall_score=80,
                precision=0.7,
                recall=0.6,
                f1_score=0.65,
                confidence_calibration_error=0.08,
                sample_size=120,
            ),
        ],
        window="Last 25",
    )


def test_model_calibration_trend_panel_renders_trend_points():
    app()
    panel = ModelCalibrationTrendPanel()

    panel.set_trend(trend())

    assert panel.message_label.isHidden()
    assert panel.trend_table.rowCount() == 2
    assert panel.trend_table.item(0, 0).text() == "2026-01-01T00:00:00Z"
    assert panel.trend_table.item(0, 1).text() == "70"
    assert panel.trend_table.item(0, 2).text() == "0.6"
    assert panel.trend_table.item(0, 6).text() == "100"


def test_model_calibration_trend_panel_insufficient_history_state():
    app()
    panel = ModelCalibrationTrendPanel()

    panel.set_trend(
        CalibrationTrendSeries(
            points=[CalibrationTrendPoint("cal-1", "2026-01-01T00:00:00Z")],
            insufficient_data=True,
            message="Insufficient historical data",
        )
    )

    assert panel.message_label.text() == "Insufficient historical data"
    assert panel.trend_table.isHidden()
    assert panel.trend_table.rowCount() == 0


def test_model_calibration_trend_panel_refresh_uses_controller_window():
    app()

    class Controller:
        def __init__(self):
            self.window = None

        def get_calibration_trend(self, window="Last 25"):
            self.window = window
            return trend()

    controller = Controller()
    panel = ModelCalibrationTrendPanel(controller=controller)
    panel.window_combo.setCurrentText("Last 10")

    loaded = panel.refresh_trend()

    assert controller.window == "Last 10"
    assert loaded.points[0].run_id == "cal-1"
    assert panel.trend_table.rowCount() == 2


def test_model_calibration_trend_panel_error_state():
    app()

    class Controller:
        def get_calibration_trend(self, window="Last 25"):
            raise RuntimeError("database unavailable")

    panel = ModelCalibrationTrendPanel(controller=Controller())

    assert panel.refresh_trend() is None
    assert panel.message_label.text() == "Unable to load calibration trend"
    assert panel.message_label.property("state") == "error"


def test_model_calibration_controller_trend_delegation():
    class TrendService:
        def __init__(self):
            self.window = None

        def get_trend(self, window="Last 25"):
            self.window = window
            return trend()

    service = TrendService()
    controller = ModelCalibrationController(trend_service=service)

    result = controller.get_calibration_trend("All")

    assert service.window == "All"
    assert result.points[1].run_id == "cal-2"
