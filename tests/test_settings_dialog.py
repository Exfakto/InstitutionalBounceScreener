import pytest
from PySide6.QtWidgets import QApplication, QScrollArea

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
            "selected_market_data_provider": "local_csv",
            "polygon_api_key": "polygon-key",
            "fmp_api_key": "fmp-key",
            "alpaca_api_key": "alpaca-key",
            "alpaca_api_secret": "alpaca-secret",
            "request_timeout_seconds": 12,
            "max_retries": 3,
            "rate_limit_sleep_seconds": 4,
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
            "selected_market_data_provider": "local_csv",
            "polygon_api_key": "",
            "fmp_api_key": "",
            "alpaca_api_key": "",
            "alpaca_api_secret": "",
            "request_timeout_seconds": 10,
            "max_retries": 2,
            "rate_limit_sleep_seconds": 1,
        }


def test_settings_dialog_loads_current_settings(app):
    controller = FakeSettingsController()
    dialog = SettingsDialog(controller=controller)

    assert dialog.isModal()
    assert dialog.minimumWidth() <= 480
    assert dialog.default_workspace_input.text() == "Research"
    assert dialog.auto_save_layout_checkbox.isChecked() is False
    assert dialog.remember_last_ticker_checkbox.isChecked() is True
    assert dialog.refresh_interval_spin.value() == 600
    assert dialog.export_path_input.text() == "exports"
    assert dialog.default_scan_mode_combo.currentText() == "Universe scan mode"
    assert dialog.default_scan_preset_input.text() == "Liquid Large Cap"
    assert dialog.max_scan_size_spin.value() == 300
    assert dialog.ui_density_combo.currentText() == "COMPACT"
    assert dialog.market_data_provider_combo.currentText() == "local_csv"
    assert dialog.polygon_api_key_input.text() == "polygon-key"
    assert dialog.fmp_api_key_input.text() == "fmp-key"
    assert dialog.alpaca_api_key_input.text() == "alpaca-key"
    assert dialog.alpaca_api_secret_input.text() == "alpaca-secret"
    assert dialog.request_timeout_spin.value() == 12
    assert dialog.max_retries_spin.value() == 3
    assert dialog.rate_limit_sleep_spin.value() == 4


def test_settings_dialog_tabs_are_scrollable(app):
    dialog = SettingsDialog(controller=FakeSettingsController())

    for index in range(dialog.tabs.count()):
        assert isinstance(dialog.tabs.widget(index), QScrollArea)
        assert dialog.tabs.widget(index).widgetResizable() is True


def test_settings_dialog_save_updates_config(app):
    controller = FakeSettingsController()
    dialog = SettingsDialog(controller=controller)

    dialog.default_workspace_input.setText("Dashboard")
    dialog.auto_save_layout_checkbox.setChecked(True)
    dialog.refresh_interval_spin.setValue(900)
    dialog.export_path_input.setText("C:/Exports")
    dialog.max_scan_size_spin.setValue(500)
    dialog.show_rejected_candidates_checkbox.setChecked(True)
    dialog.market_data_provider_combo.setCurrentText("polygon")
    dialog.polygon_api_key_input.setText("new-polygon-key")
    dialog.request_timeout_spin.setValue(20)
    dialog.save_settings()

    assert controller.saved_settings["general"]["default_workspace"] == "Dashboard"
    assert controller.saved_settings["general"]["auto_save_layout"] is True
    assert controller.saved_settings["refresh"]["interval"] == 900
    assert controller.saved_settings["paths"]["export_path"] == "C:/Exports"
    assert controller.saved_preferences["max_scan_size"] == 500
    assert controller.saved_preferences["show_rejected_candidates"] is True
    assert controller.saved_preferences["selected_market_data_provider"] == "polygon"
    assert controller.saved_preferences["polygon_api_key"] == "new-polygon-key"
    assert controller.saved_preferences["request_timeout_seconds"] == 20


def test_settings_dialog_reset_preferences(app):
    controller = FakeSettingsController()
    dialog = SettingsDialog(controller=controller)

    dialog.reset_app_preferences()

    assert dialog.default_scan_mode_combo.currentText() == "Manual ticker input"
    assert dialog.max_scan_size_spin.value() == 250
    assert dialog.show_rejected_candidates_checkbox.isChecked() is True
    assert dialog.market_data_provider_combo.currentText() == "local_csv"


def test_settings_dialog_validates_selected_provider_credentials(app, monkeypatch):
    controller = FakeSettingsController()
    dialog = SettingsDialog(controller=controller)
    messages = []

    monkeypatch.setattr(
        settings_dialog_module.QMessageBox,
        "warning",
        lambda *args: messages.append(args),
    )

    dialog.market_data_provider_combo.setCurrentText("alpaca")
    dialog.alpaca_api_key_input.setText("")
    dialog.alpaca_api_secret_input.setText("")
    dialog.save_settings()

    assert controller.saved_preferences is None
    assert messages
    assert "Alpaca requires" in messages[0][2]


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
