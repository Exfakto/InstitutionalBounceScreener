from PySide6.QtWidgets import QApplication

from services.provider_configuration_validation_service import (
    ProviderConfigurationIssue,
    ProviderConfigurationValidationResult,
)
from ui.widgets.provider_configuration_panel import ProviderConfigurationPanel


def app():
    return QApplication.instance() or QApplication([])


def result(status="Passed", issues=None):
    return ProviderConfigurationValidationResult(status=status, issues=issues or [])


def issue(status="Failed", setting="polygon_api_key"):
    return ProviderConfigurationIssue(
        status=status,
        message="Polygon API key is required",
        affected_setting=setting,
        recommended_fix="Enter valid provider credentials before running live screening.",
    )


def test_provider_configuration_panel_initial_state():
    app()
    panel = ProviderConfigurationPanel()

    assert panel.status_label.text() == "Status: N/A"
    assert panel.message_label.text() == "Run validation to check provider configuration"
    assert panel.validation_table.isHidden()


def test_provider_configuration_panel_renders_passed_result():
    app()
    panel = ProviderConfigurationPanel()

    panel.set_validation_result(result("Passed"))

    assert panel.status_label.text() == "Status: Passed"
    assert panel.message_label.text() == "Provider configuration passed validation"
    assert panel.validation_table.isHidden()


def test_provider_configuration_panel_renders_validation_issues():
    app()
    panel = ProviderConfigurationPanel()

    panel.set_validation_result(result("Failed", [issue()]))

    assert panel.status_label.text() == "Status: Failed"
    assert panel.message_label.isHidden()
    assert panel.validation_table.rowCount() == 1
    assert panel.validation_table.item(0, 0).text() == "Failed"
    assert panel.validation_table.item(0, 1).text() == "Polygon API key is required"
    assert panel.validation_table.item(0, 2).text() == "polygon_api_key"


def test_provider_configuration_panel_refresh_action_delegates_to_controller():
    app()

    class Controller:
        def __init__(self):
            self.called = False

        def validate_provider_configuration(self):
            self.called = True
            return result("Warning", [issue("Warning", "failover_provider")])

    controller = Controller()
    panel = ProviderConfigurationPanel(controller=controller)

    loaded = panel.refresh_validation()

    assert controller.called is True
    assert loaded.status == "Warning"
    assert panel.validation_table.item(0, 2).text() == "failover_provider"


def test_provider_configuration_panel_error_state():
    app()

    class Controller:
        def validate_provider_configuration(self):
            raise RuntimeError("validation unavailable")

    panel = ProviderConfigurationPanel(controller=Controller())

    assert panel.refresh_validation() is None
    assert panel.status_label.text() == "Status: Failed"
    assert panel.message_label.text() == "Unable to validate provider configuration"
    assert panel.message_label.property("state") == "error"
