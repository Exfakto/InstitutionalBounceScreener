import pytest
from types import SimpleNamespace
from PySide6.QtWidgets import QApplication

from ui.about_dialog import AboutDialog


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


class FakeDiagnosticsController:
    def get_diagnostics(self):
        return {
            "app_name": "Institutional Bounce Screener",
            "version": "v3.0.0-beta",
            "build_date": "2026-07-03",
            "schema_version": "1",
            "python_version": "3.13.0",
            "qt_version": "6.0.0",
            "operating_system": "Windows",
            "active_provider": "local",
            "provider_config_path": "config/providers.json",
            "database_path": "data/InstitutionalBounce.db",
            "working_directory": "C:/Projects/InstitutionalBounceScreener",
            "log_path": "logs",
            "test_build_mode": "Unavailable",
            "warnings": [],
        }

    def diagnostics_text(self):
        return (
            "Application: Institutional Bounce Screener\n"
            "Version: v3.0.0-beta\n"
            "Active Provider: local"
        )

    def startup_report(self):
        return SimpleNamespace(
            status="PASS",
            checks=[SimpleNamespace(name="database", status="PASS", message="ok")],
            warnings=[],
            errors=[],
        )

    def health_report(self):
        return SimpleNamespace(
            status="PASS",
            checks=[SimpleNamespace(name="settings", status="PASS", message="ok")],
            warnings=[],
            errors=[],
        )


def test_about_dialog_renders_diagnostics(app):
    dialog = AboutDialog(controller=FakeDiagnosticsController())

    assert dialog.isModal()
    assert dialog.app_name_label.text() == "Institutional Bounce Screener"
    assert "Version: v3.0.0-beta" in dialog.version_label.text()
    assert "Build: 2026-07-03" in dialog.version_label.text()
    assert dialog.diagnostic_labels["schema_version"].text() == "1"
    assert dialog.diagnostic_labels["active_provider"].text() == "local"
    assert "Application: Institutional Bounce Screener" in dialog.diagnostics_text.toPlainText()
    assert "Startup Diagnostics: PASS" in dialog.diagnostics_text.toPlainText()


def test_about_dialog_copy_diagnostics(app):
    dialog = AboutDialog(controller=FakeDiagnosticsController())

    dialog.copy_diagnostics()

    assert QApplication.clipboard().text() == dialog.diagnostics_text.toPlainText()


def test_about_dialog_does_not_display_secrets(app):
    dialog = AboutDialog(controller=FakeDiagnosticsController())

    displayed_text = (
        dialog.app_name_label.text()
        + dialog.version_label.text()
        + dialog.diagnostics_text.toPlainText()
    )

    assert "API_KEY" not in displayed_text
    assert "secret" not in displayed_text.lower()


def test_about_dialog_refresh_diagnostics(app):
    dialog = AboutDialog(controller=FakeDiagnosticsController())

    dialog.refresh_button.click()

    assert "Health Check: PASS" in dialog.diagnostics_text.toPlainText()
