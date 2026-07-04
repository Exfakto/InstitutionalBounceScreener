from PySide6.QtWidgets import QApplication

from services.app_config_service import AppConfigService
from ui.about_dialog import AboutDialog
from tests.release_test_utils import app_config, create_sqlite


def app():
    return QApplication.instance() or QApplication([])


class FakeDiagnosticsController:
    def get_diagnostics(self):
        return {
            "app_name": "Institutional Bounce Screener",
            "version": "4.0.0",
            "build_date": "2026-07-03",
            "build_timestamp": "2026-07-03T00:00:00Z",
            "release_channel": "dev",
            "schema_version": "1",
            "python_version": "3.x",
        }

    def diagnostics_text(self):
        return "diagnostics text"

    def startup_report(self):
        return None

    def health_report(self):
        return None


class FailingBetaValidation:
    def run(self):
        raise RuntimeError("beta unavailable")


def test_diagnostics_release_ui_construction_and_labels(tmp_path):
    app()
    config = app_config(tmp_path)
    create_sqlite(config.database_path)

    dialog = AboutDialog(controller=FakeDiagnosticsController())
    dialog.config_service = AppConfigService(config)
    dialog.load_diagnostics()

    assert dialog.windowTitle() == "About & Diagnostics"
    assert dialog.release_group.title() == "Release Readiness"
    assert dialog.backup_database_button.text() == "Backup Database"
    assert dialog.restore_database_button.text() == "Restore Database"
    assert dialog.run_beta_validation_button.text() == "Run Beta Validation"
    assert dialog.scroll_area.widgetResizable() is True
    assert dialog.release_labels["release_channel"].text() == "dev"


def test_diagnostics_release_ui_backup_database_action(tmp_path):
    app()
    config = app_config(tmp_path)
    create_sqlite(config.database_path)

    dialog = AboutDialog(controller=FakeDiagnosticsController())
    dialog.config_service = AppConfigService(config)
    result = dialog.backup_database()

    assert result.success is True
    assert "Database backup created" in dialog.release_labels["checklist"].text()


def test_diagnostics_release_ui_beta_validation_failure_is_safe(tmp_path):
    app()
    config = app_config(tmp_path)
    create_sqlite(config.database_path)

    dialog = AboutDialog(controller=FakeDiagnosticsController())
    dialog.config_service = AppConfigService(config)
    dialog.beta_validation_service = FailingBetaValidation()

    result = dialog.run_beta_validation()

    assert result is None
    assert "Beta validation failed" in dialog.release_labels["beta_validation"].text()
    assert dialog.run_beta_validation_button.isEnabled() is True
