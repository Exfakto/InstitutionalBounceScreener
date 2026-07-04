from PySide6.QtWidgets import QApplication

from services.model_calibration_recommendation_service import (
    CalibrationRecommendationView,
)
from services.model_calibration_validation_service import CalibrationValidationResult
from ui.widgets.model_calibration_panel import ModelCalibrationPanel


def app():
    return QApplication.instance() or QApplication([])


def test_model_calibration_panel_renders_recommendations():
    app()
    panel = ModelCalibrationPanel()

    panel.set_recommendations(
        [
            CalibrationRecommendationView(
                title="Minimum Final Score",
                severity="HIGH",
                recommended_action="75",
                reason="Low score buckets underperformed",
                related_metric="minimum_final_score",
                timestamp="2026-01-02T00:00:00Z",
            )
        ]
    )

    assert panel.message_label.isHidden()
    assert panel.recommendations_table.rowCount() == 1
    assert panel.recommendations_table.item(0, 0).text() == "Minimum Final Score"
    assert panel.recommendations_table.item(0, 1).text() == "HIGH"
    assert panel.recommendations_table.item(0, 2).text() == "75"
    assert panel.recommendations_table.item(0, 3).text() == "Low score buckets underperformed"
    assert panel.recommendations_table.item(0, 4).text() == "minimum_final_score"
    assert panel.recommendations_table.item(0, 5).text() == "2026-01-02T00:00:00Z"


def test_model_calibration_panel_empty_state():
    app()
    panel = ModelCalibrationPanel()

    panel.set_recommendations([])

    assert panel.message_label.text() == "No calibration recommendations available"
    assert panel.recommendations_table.isHidden()
    assert panel.recommendations_table.rowCount() == 0


def test_model_calibration_panel_error_state_clears_table():
    app()
    panel = ModelCalibrationPanel()
    panel.set_recommendations(
        [
            CalibrationRecommendationView(
                title="Minimum Support Score",
                severity="MEDIUM",
                recommended_action="70",
                reason="Support buckets lagged",
                related_metric="minimum_support_score",
            )
        ]
    )

    panel.set_error("Unable to load calibration recommendations")

    assert panel.message_label.text() == "Unable to load calibration recommendations"
    assert panel.message_label.property("state") == "error"
    assert panel.recommendations_table.isHidden()
    assert panel.recommendations_table.rowCount() == 0


def test_model_calibration_panel_refresh_uses_controller():
    app()

    class FakeController:
        def __init__(self):
            self.called = False

        def get_calibration_recommendations(self):
            self.called = True
            return [
                CalibrationRecommendationView(
                    title="Confidence Filtering Rules",
                    severity="HIGH",
                    recommended_action="Require MEDIUM or HIGH",
                    reason="Low confidence groups underperformed",
                    related_metric="confidence_filtering_rules",
                )
            ]

    controller = FakeController()
    panel = ModelCalibrationPanel(controller=controller)

    loaded = panel.refresh_recommendations()

    assert controller.called is True
    assert len(loaded) == 1
    assert panel.recommendations_table.item(0, 0).text() == "Confidence Filtering Rules"


def test_model_calibration_panel_refresh_error_state():
    app()

    class FailingController:
        def get_calibration_recommendations(self):
            raise RuntimeError("database unavailable")

    panel = ModelCalibrationPanel(controller=FailingController())

    assert panel.refresh_recommendations() == []
    assert panel.message_label.text() == "Unable to load calibration recommendations"


def test_model_calibration_panel_validate_changes_uses_controller():
    app()

    class Controller:
        def __init__(self):
            self.current_settings = None
            self.proposed_settings = None

        def validate_calibration_changes(self, current_settings=None, proposed_settings=None):
            self.current_settings = current_settings
            self.proposed_settings = proposed_settings
            return CalibrationValidationResult(
                status="passed",
                message="Calibration validation passed.",
            )

    controller = Controller()
    panel = ModelCalibrationPanel(controller=controller)
    panel.set_recommendations(
        [
            CalibrationRecommendationView(
                title="Minimum Final Score",
                severity="HIGH",
                recommended_action="75",
                reason="Low score buckets underperformed",
                related_metric="minimum_final_score",
            )
        ]
    )

    result = panel.validate_current_changes(current_settings={"current": 1})

    assert result.status == "passed"
    assert controller.current_settings == {"current": 1}
    assert controller.proposed_settings == {"minimum_final_score": "75"}
    assert panel.validation_result_label.text() == "Calibration validation passed."
