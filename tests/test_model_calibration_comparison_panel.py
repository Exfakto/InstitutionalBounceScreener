from PySide6.QtWidgets import QApplication

from controllers.model_calibration_controller import ModelCalibrationController
from services.model_calibration_comparison_service import (
    CalibrationMetricComparison,
    CalibrationRunComparison,
)
from ui.widgets.model_calibration_comparison_panel import (
    ModelCalibrationComparisonPanel,
)


def app():
    return QApplication.instance() or QApplication([])


def comparison():
    return CalibrationRunComparison(
        base_run_id="base",
        comparison_run_id="new",
        metrics=[
            CalibrationMetricComparison(
                metric="overall_score",
                label="Overall Score",
                base_value=70,
                comparison_value=80,
                delta=10,
                percent_delta=14.2857,
                classification="improved",
            ),
            CalibrationMetricComparison(
                metric="confidence_calibration_error",
                label="Confidence Calibration Error",
                base_value=0.1,
                comparison_value=0.1,
                delta=0,
                percent_delta=0,
                classification="unchanged",
            ),
        ],
    )


def test_model_calibration_comparison_panel_renders_comparison():
    app()
    panel = ModelCalibrationComparisonPanel()

    panel.set_comparison(comparison())

    assert panel.message_label.isHidden()
    assert panel.comparison_table.rowCount() == 2
    assert panel.comparison_table.item(0, 0).text() == "Overall Score"
    assert panel.comparison_table.item(0, 1).text() == "70"
    assert panel.comparison_table.item(0, 2).text() == "80"
    assert panel.comparison_table.item(0, 3).text() == "10"
    assert panel.comparison_table.item(0, 4).text() == "14.29%"
    assert panel.comparison_table.item(0, 5).text() == "improved"


def test_model_calibration_comparison_panel_missing_run_state():
    app()
    panel = ModelCalibrationComparisonPanel()

    panel.set_comparison(
        CalibrationRunComparison(
            base_run_id="base",
            comparison_run_id="missing",
            warnings=["Calibration run not found: missing"],
            missing_run=True,
        )
    )

    assert panel.message_label.text() == "Calibration run not found: missing"
    assert panel.comparison_table.isHidden()


def test_model_calibration_comparison_panel_compare_button_uses_controller():
    app()

    class Controller:
        def __init__(self):
            self.args = None

        def compare_calibration_runs(self, base_run_id, comparison_run_id):
            self.args = (base_run_id, comparison_run_id)
            return comparison()

    controller = Controller()
    panel = ModelCalibrationComparisonPanel(controller=controller)
    panel.base_run_input.setText("base")
    panel.comparison_run_input.setText("new")

    result = panel.compare_selected_runs()

    assert controller.args == ("base", "new")
    assert result.comparison_run_id == "new"
    assert panel.comparison_table.rowCount() == 2


def test_model_calibration_comparison_panel_error_state():
    app()

    class Controller:
        def compare_calibration_runs(self, base_run_id, comparison_run_id):
            raise RuntimeError("database unavailable")

    panel = ModelCalibrationComparisonPanel(controller=Controller())

    assert panel.compare_selected_runs() is None
    assert panel.message_label.text() == "Unable to compare calibration runs"
    assert panel.message_label.property("state") == "error"


def test_model_calibration_controller_comparison_delegation():
    class ComparisonService:
        def __init__(self):
            self.args = None

        def compare_runs(self, base_run_id, comparison_run_id):
            self.args = (base_run_id, comparison_run_id)
            return comparison()

    service = ComparisonService()
    controller = ModelCalibrationController(comparison_service=service)

    result = controller.compare_calibration_runs("base", "new")

    assert service.args == ("base", "new")
    assert result.metrics[0].classification == "improved"
