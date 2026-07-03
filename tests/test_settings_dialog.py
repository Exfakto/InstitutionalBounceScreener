import pytest
from PySide6.QtWidgets import QApplication

from ui import settings_dialog as settings_dialog_module
from ui.settings_dialog import SettingsDialog


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


class FakeSettingsController:
    def __init__(self):
        self.saved_settings = None
        self.saved_preferences = None

    def load_settings(self):
        return {
            "general": {
                "default_workspace": "Research",
                "auto_save_layout": False,
                "remember_last_ticker": True,
            },
            "refresh": {
                "enabled": True,
                "interval": 600,
                "market_aware": False,
            },
            "appearance": {
                "theme": "Dark",
                "font_scaling": "100%",
            },
            "paths": {
                "database_path": "data/InstitutionalBounce.db",
                "export_path": "exports",
                "log_path": "logs",
            },
        }

    def save_settings(self, settings):
        self.saved_settings = settings
        return settings

    def provider_status(self):
        return {
            "current_provider": "local",
            "enabled_providers": ["local", "polygon"],
            "api_key_status": {
                "Polygon": "Configured",
                "FMP": "Not Configured",
                "Finnhub": "Not Configured",
                "SEC EDGAR": "Configured",
            },
        }

    def load_app_preferences(self):
        return {
            "default_scan_mode": "Universe scan mode",
            "default_scan_preset": "Liquid Large Cap",
            "max_scan_size": 300,
            "large_scan_warning_threshold": 150,
            "default_export_directory": "exports/results",
            "ui_density": "COMPACT",
            "auto_refresh_results": False,
            "show_rejected_candidates": False,
        }

    def save_app_preferences(self, preferences):
        self.saved_preferences = preferences
        return preferences

    def reset_app_preferences(self):
        return {
            "default_scan_mode": "Manual ticker input",
            "default_scan_preset": "Institutional Quality",
            "max_scan_size": 250,
            "large_scan_warning_threshold": 100,
            "default_export_directory": "exports/results",
            "ui_density": "NORMAL",
            "auto_refresh_results": True,
            "show_rejected_candidates": True,
        }


def test_settings_dialog_loads_current_settings(app):
    controller = FakeSettingsController()
    dialog = SettingsDialog(controller=controller)

    assert dialog.isModal()
    assert dialog.default_workspace_input.text() == "Research"
    assert dialog.auto_save_layout_checkbox.isChecked() is False
    assert dialog.remember_last_ticker_checkbox.isChecked() is True
    assert dialog.refresh_interval_spin.value() == 600
    assert dialog.export_path_input.text() == "exports"
    assert dialog.default_scan_mode_combo.currentText() == "Universe scan mode"
    assert dialog.default_scan_preset_input.text() == "Liquid Large Cap"
    assert dialog.max_scan_size_spin.value() == 300
    assert dialog.ui_density_combo.currentText() == "COMPACT"


def test_settings_dialog_save_updates_config(app):
    controller = FakeSettingsController()
    dialog = SettingsDialog(controller=controller)

    dialog.default_workspace_input.setText("Dashboard")
    dialog.auto_save_layout_checkbox.setChecked(True)
    dialog.refresh_interval_spin.setValue(900)
    dialog.export_path_input.setText("C:/Exports")
    dialog.max_scan_size_spin.setValue(500)
    dialog.show_rejected_candidates_checkbox.setChecked(True)
    dialog.save_settings()

    assert controller.saved_settings["general"]["default_workspace"] == "Dashboard"
    assert controller.saved_settings["general"]["auto_save_layout"] is True
    assert controller.saved_settings["refresh"]["interval"] == 900
    assert controller.saved_settings["paths"]["export_path"] == "C:/Exports"
    assert controller.saved_preferences["max_scan_size"] == 500
    assert controller.saved_preferences["show_rejected_candidates"] is True


def test_settings_dialog_reset_preferences(app):
    controller = FakeSettingsController()
    dialog = SettingsDialog(controller=controller)

    dialog.reset_app_preferences()

    assert dialog.default_scan_mode_combo.currentText() == "Manual ticker input"
    assert dialog.max_scan_size_spin.value() == 250
    assert dialog.show_rejected_candidates_checkbox.isChecked() is True


def test_settings_dialog_cancel_discards_changes(app):
    controller = FakeSettingsController()
    dialog = SettingsDialog(controller=controller)

    dialog.default_workspace_input.setText("Changed")
    dialog.reject()

    assert controller.saved_settings is None


def test_settings_dialog_displays_provider_status(app):
    dialog = SettingsDialog(controller=FakeSettingsController())

    assert dialog.current_provider_value.text() == "local"
    assert dialog.enabled_providers_value.text() == "local, polygon"
    assert dialog.polygon_status_value.text() == "Configured"
    assert dialog.fmp_status_value.text() == "Not Configured"
    assert dialog.sec_edgar_status_value.text() == "Configured"


def test_settings_dialog_browse_updates_export_path(app, monkeypatch):
    dialog = SettingsDialog(controller=FakeSettingsController())

    monkeypatch.setattr(
        settings_dialog_module.QFileDialog,
        "getExistingDirectory",
        lambda *args, **kwargs: "D:/Exports",
    )

    dialog.browse_export_path()

    assert dialog.export_path_input.text() == "D:/Exports"
