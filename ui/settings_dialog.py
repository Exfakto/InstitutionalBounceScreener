from __future__ import annotations

from typing import Any

from dataclasses import asdict

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from controllers.settings_controller import SettingsController


class SettingsDialog(QDialog):
    """
    Modal application settings dialog.
    """

    def __init__(
        self,
        controller: SettingsController | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller or SettingsController()

        self.setWindowTitle("Settings")
        self.setModal(True)
        self.resize(640, 520)
        self.setMinimumSize(480, 360)

        self.tabs = QTabWidget()
        self._build_general_tab()
        self._build_providers_tab()
        self._build_refresh_tab()
        self._build_appearance_tab()
        self._build_paths_tab()
        self._build_app_preferences_tab()

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.save_settings)
        self.button_box.rejected.connect(self.reject)
        self.reset_preferences_button = QPushButton("Reset Preferences")
        self.reset_preferences_button.clicked.connect(self.reset_app_preferences)
        self.button_box.addButton(
            self.reset_preferences_button,
            QDialogButtonBox.ButtonRole.ResetRole,
        )

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addWidget(self.button_box)

        self.load_settings()

    def load_settings(self) -> None:
        settings = self.controller.load_settings()
        self._apply_settings(settings)
        self._apply_app_preferences(self.controller.load_app_preferences())
        self.update_provider_status(self.controller.provider_status())

    def save_settings(self) -> None:
        validation_message = self.validate_provider_credentials()
        if validation_message:
            QMessageBox.warning(self, "Provider Credentials", validation_message)
            return
        self.controller.save_settings(self.settings_from_ui())
        self.controller.save_app_preferences(self.app_preferences_from_ui())
        self.accept()

    def reset_app_preferences(self) -> None:
        self._apply_app_preferences(self.controller.reset_app_preferences())

    def settings_from_ui(self) -> dict[str, Any]:
        return {
            "general": {
                "default_workspace": self.default_workspace_input.text().strip(),
                "auto_save_layout": self.auto_save_layout_checkbox.isChecked(),
                "remember_last_ticker": self.remember_last_ticker_checkbox.isChecked(),
            },
            "refresh": {
                "enabled": self.auto_refresh_checkbox.isChecked(),
                "interval": self.refresh_interval_spin.value(),
                "market_aware": self.market_aware_refresh_checkbox.isChecked(),
            },
            "appearance": {
                "theme": self.theme_combo.currentText(),
                "font_scaling": self.font_scaling_combo.currentText(),
            },
            "paths": {
                "database_path": self.database_path_input.text().strip(),
                "export_path": self.export_path_input.text().strip(),
                "log_path": self.log_path_input.text().strip(),
            },
        }

    def app_preferences_from_ui(self) -> dict[str, Any]:
        return {
            "default_scan_mode": self.default_scan_mode_combo.currentText(),
            "default_scan_preset": self.default_scan_preset_input.text().strip(),
            "max_scan_size": self.max_scan_size_spin.value(),
            "large_scan_warning_threshold": self.large_scan_warning_threshold_spin.value(),
            "default_export_directory": self.default_export_directory_input.text().strip(),
            "ui_density": self.ui_density_combo.currentText(),
            "auto_refresh_results": self.auto_refresh_results_checkbox.isChecked(),
            "show_rejected_candidates": self.show_rejected_candidates_checkbox.isChecked(),
            "selected_market_data_provider": self.market_data_provider_combo.currentText(),
            "polygon_api_key": self.polygon_api_key_input.text().strip(),
            "fmp_api_key": self.fmp_api_key_input.text().strip(),
            "alpaca_api_key": self.alpaca_api_key_input.text().strip(),
            "alpaca_api_secret": self.alpaca_api_secret_input.text().strip(),
            "request_timeout_seconds": self.request_timeout_spin.value(),
            "max_retries": self.max_retries_spin.value(),
            "rate_limit_sleep_seconds": self.rate_limit_sleep_spin.value(),
            "historical_ohlcv_lookback_years": self.historical_ohlcv_lookback_years_spin.value(),
        }

    def validate_provider_credentials(self) -> str:
        provider = self.market_data_provider_combo.currentText()
        if provider == "local_csv":
            return ""
        if provider == "polygon" and not self.polygon_api_key_input.text().strip():
            return "Polygon requires an API key."
        if provider == "fmp" and not self.fmp_api_key_input.text().strip():
            return "Financial Modeling Prep requires an API key."
        if provider == "alpaca":
            if not self.alpaca_api_key_input.text().strip():
                return "Alpaca requires an API key."
            if not self.alpaca_api_secret_input.text().strip():
                return "Alpaca requires an API secret."
        return ""

    def update_provider_status(self, status: dict[str, Any] | None) -> None:
        status = status if isinstance(status, dict) else {}
        api_key_status = status.get("api_key_status")

        if not isinstance(api_key_status, dict):
            api_key_status = {}

        enabled_providers = status.get("enabled_providers", [])

        if not isinstance(enabled_providers, list):
            enabled_providers = []

        self.current_provider_value.setText(
            str(status.get("current_provider") or "--")
        )
        self.enabled_providers_value.setText(
            ", ".join(str(provider) for provider in enabled_providers) or "--"
        )
        self.polygon_status_value.setText(
            str(api_key_status.get("Polygon") or "Not Configured")
        )
        self.fmp_status_value.setText(
            str(api_key_status.get("FMP") or "Not Configured")
        )
        self.finnhub_status_value.setText(
            str(api_key_status.get("Finnhub") or "Not Configured")
        )
        self.sec_edgar_status_value.setText(
            str(api_key_status.get("SEC EDGAR") or "Configured")
        )

    def browse_export_path(self) -> None:
        selected_directory = QFileDialog.getExistingDirectory(
            self,
            "Select Export Directory",
            self.export_path_input.text(),
        )

        if selected_directory:
            self.export_path_input.setText(selected_directory)

    def _apply_settings(self, settings: dict[str, Any]) -> None:
        general = self._section(settings, "general")
        refresh = self._section(settings, "refresh")
        appearance = self._section(settings, "appearance")
        paths = self._section(settings, "paths")

        self.default_workspace_input.setText(
            str(general.get("default_workspace") or "")
        )
        self.auto_save_layout_checkbox.setChecked(
            bool(general.get("auto_save_layout", True))
        )
        self.remember_last_ticker_checkbox.setChecked(
            bool(general.get("remember_last_ticker", True))
        )

        self.auto_refresh_checkbox.setChecked(bool(refresh.get("enabled", True)))
        self.refresh_interval_spin.setValue(int(refresh.get("interval") or 300))
        self.market_aware_refresh_checkbox.setChecked(
            bool(refresh.get("market_aware", True))
        )

        self._set_combo_text(self.theme_combo, str(appearance.get("theme") or "Dark"))
        self._set_combo_text(
            self.font_scaling_combo,
            str(appearance.get("font_scaling") or "100%"),
        )

        self.database_path_input.setText(str(paths.get("database_path") or ""))
        self.export_path_input.setText(str(paths.get("export_path") or ""))
        self.log_path_input.setText(str(paths.get("log_path") or ""))

    def _apply_app_preferences(self, preferences) -> None:
        if hasattr(preferences, "__dataclass_fields__"):
            preferences = asdict(preferences)
        preferences = preferences if isinstance(preferences, dict) else {}

        self._set_combo_text(
            self.default_scan_mode_combo,
            str(preferences.get("default_scan_mode") or "Manual ticker input"),
        )
        self.default_scan_preset_input.setText(
            str(preferences.get("default_scan_preset") or "Institutional Quality")
        )
        self.max_scan_size_spin.setValue(int(preferences.get("max_scan_size") or 250))
        self.large_scan_warning_threshold_spin.setValue(
            int(preferences.get("large_scan_warning_threshold") or 100)
        )
        self.default_export_directory_input.setText(
            str(preferences.get("default_export_directory") or "exports/results")
        )
        self._set_combo_text(
            self.ui_density_combo,
            str(preferences.get("ui_density") or "NORMAL"),
        )
        self.auto_refresh_results_checkbox.setChecked(
            bool(preferences.get("auto_refresh_results", True))
        )
        self.show_rejected_candidates_checkbox.setChecked(
            bool(preferences.get("show_rejected_candidates", True))
        )
        self._set_combo_text(
            self.market_data_provider_combo,
            str(preferences.get("selected_market_data_provider") or "local_csv"),
        )
        self.polygon_api_key_input.setText(str(preferences.get("polygon_api_key") or ""))
        self.fmp_api_key_input.setText(str(preferences.get("fmp_api_key") or ""))
        self.alpaca_api_key_input.setText(str(preferences.get("alpaca_api_key") or ""))
        self.alpaca_api_secret_input.setText(str(preferences.get("alpaca_api_secret") or ""))
        self.request_timeout_spin.setValue(
            int(preferences.get("request_timeout_seconds") or 10)
        )
        self.max_retries_spin.setValue(int(preferences.get("max_retries") or 3))
        self.rate_limit_sleep_spin.setValue(
            int(preferences.get("rate_limit_sleep_seconds") or 1)
        )
        self.historical_ohlcv_lookback_years_spin.setValue(
            int(preferences.get("historical_ohlcv_lookback_years") or 5)
        )

    def _build_general_tab(self) -> None:
        tab, layout = self._scrollable_form_tab()

        self.default_workspace_input = QLineEdit()
        self.auto_save_layout_checkbox = QCheckBox("Auto-save layout")
        self.remember_last_ticker_checkbox = QCheckBox("Remember last ticker")

        layout.addRow("Default workspace", self.default_workspace_input)
        layout.addRow("", self.auto_save_layout_checkbox)
        layout.addRow("", self.remember_last_ticker_checkbox)

        self.tabs.addTab(tab, "General")

    def _build_providers_tab(self) -> None:
        tab, layout = self._scrollable_form_tab()

        self.current_provider_value = QLabel("--")
        self.enabled_providers_value = QLabel("--")
        self.polygon_status_value = QLabel("Not Configured")
        self.fmp_status_value = QLabel("Not Configured")
        self.finnhub_status_value = QLabel("Not Configured")
        self.sec_edgar_status_value = QLabel("Configured")

        layout.addRow("Current provider", self.current_provider_value)
        layout.addRow("Enabled providers", self.enabled_providers_value)
        layout.addRow("Polygon", self.polygon_status_value)
        layout.addRow("FMP", self.fmp_status_value)
        layout.addRow("Finnhub", self.finnhub_status_value)
        layout.addRow("SEC EDGAR", self.sec_edgar_status_value)

        self.tabs.addTab(tab, "Providers")

    def _build_refresh_tab(self) -> None:
        tab, layout = self._scrollable_form_tab()

        self.auto_refresh_checkbox = QCheckBox("Enabled")
        self.refresh_interval_spin = QSpinBox()
        self.refresh_interval_spin.setRange(30, 86400)
        self.refresh_interval_spin.setSuffix(" sec")
        self.market_aware_refresh_checkbox = QCheckBox("Market-aware refresh")

        layout.addRow("Auto refresh", self.auto_refresh_checkbox)
        layout.addRow("Interval", self.refresh_interval_spin)
        layout.addRow("", self.market_aware_refresh_checkbox)

        self.tabs.addTab(tab, "Refresh")

    def _build_appearance_tab(self) -> None:
        tab, layout = self._scrollable_form_tab()

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light (placeholder)"])
        self.font_scaling_combo = QComboBox()
        self.font_scaling_combo.addItems(["100%", "110% (placeholder)", "125% (placeholder)"])

        layout.addRow("Theme", self.theme_combo)
        layout.addRow("Font scaling", self.font_scaling_combo)

        self.tabs.addTab(tab, "Appearance")

    def _build_paths_tab(self) -> None:
        tab, layout = self._scrollable_form_tab()

        self.database_path_input = QLineEdit()
        self.database_path_input.setReadOnly(True)
        self.export_path_input = QLineEdit()
        self.log_path_input = QLineEdit()
        self.log_path_input.setReadOnly(True)

        export_layout = QHBoxLayout()
        export_layout.addWidget(self.export_path_input)
        self.export_browse_button = QPushButton("Browse")
        self.export_browse_button.clicked.connect(self.browse_export_path)
        export_layout.addWidget(self.export_browse_button)

        layout.addRow("Database path", self.database_path_input)
        layout.addRow("Export path", export_layout)
        layout.addRow("Log path", self.log_path_input)

        self.tabs.addTab(tab, "Paths")

    def _build_app_preferences_tab(self) -> None:
        tab, layout = self._scrollable_form_tab()

        self.default_scan_mode_combo = QComboBox()
        self.default_scan_mode_combo.addItems(["Manual ticker input", "Universe scan mode"])
        self.default_scan_preset_input = QLineEdit()
        self.max_scan_size_spin = QSpinBox()
        self.max_scan_size_spin.setRange(1, 10000)
        self.large_scan_warning_threshold_spin = QSpinBox()
        self.large_scan_warning_threshold_spin.setRange(1, 10000)
        self.default_export_directory_input = QLineEdit()
        self.ui_density_combo = QComboBox()
        self.ui_density_combo.addItems(["COMPACT", "NORMAL", "COMFORTABLE"])
        self.auto_refresh_results_checkbox = QCheckBox("Refresh results after screening")
        self.show_rejected_candidates_checkbox = QCheckBox("Show rejected candidates")
        self.market_data_provider_combo = QComboBox()
        self.market_data_provider_combo.addItems(["local_csv", "polygon", "fmp", "alpaca"])
        self.polygon_api_key_input = QLineEdit()
        self.polygon_api_key_input.setEchoMode(QLineEdit.Password)
        self.fmp_api_key_input = QLineEdit()
        self.fmp_api_key_input.setEchoMode(QLineEdit.Password)
        self.alpaca_api_key_input = QLineEdit()
        self.alpaca_api_key_input.setEchoMode(QLineEdit.Password)
        self.alpaca_api_secret_input = QLineEdit()
        self.alpaca_api_secret_input.setEchoMode(QLineEdit.Password)
        self.request_timeout_spin = QSpinBox()
        self.request_timeout_spin.setRange(1, 120)
        self.request_timeout_spin.setSuffix(" sec")
        self.max_retries_spin = QSpinBox()
        self.max_retries_spin.setRange(0, 10)
        self.rate_limit_sleep_spin = QSpinBox()
        self.rate_limit_sleep_spin.setRange(0, 120)
        self.rate_limit_sleep_spin.setSuffix(" sec")
        self.historical_ohlcv_lookback_years_spin = QSpinBox()
        self.historical_ohlcv_lookback_years_spin.setRange(1, 30)
        self.historical_ohlcv_lookback_years_spin.setSuffix(" years")

        layout.addRow("Default scan mode", self.default_scan_mode_combo)
        layout.addRow("Default scan preset", self.default_scan_preset_input)
        layout.addRow("Max scan size", self.max_scan_size_spin)
        layout.addRow("Large scan warning", self.large_scan_warning_threshold_spin)
        layout.addRow("Default export directory", self.default_export_directory_input)
        layout.addRow("UI density", self.ui_density_combo)
        layout.addRow("", self.auto_refresh_results_checkbox)
        layout.addRow("", self.show_rejected_candidates_checkbox)
        layout.addRow("Market data provider", self.market_data_provider_combo)
        layout.addRow("Polygon API key", self.polygon_api_key_input)
        layout.addRow("FMP API key", self.fmp_api_key_input)
        layout.addRow("Alpaca API key", self.alpaca_api_key_input)
        layout.addRow("Alpaca API secret", self.alpaca_api_secret_input)
        layout.addRow("Request timeout", self.request_timeout_spin)
        layout.addRow("Max retries", self.max_retries_spin)
        layout.addRow("Rate limit sleep", self.rate_limit_sleep_spin)
        layout.addRow("Historical OHLCV lookback", self.historical_ohlcv_lookback_years_spin)

        self.tabs.addTab(tab, "App Preferences")

    @staticmethod
    def _scrollable_form_tab():
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        content = QWidget()
        layout = QFormLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        scroll.setWidget(content)
        return scroll, layout

    @staticmethod
    def _section(settings: dict[str, Any], name: str) -> dict[str, Any]:
        section = settings.get(name)

        if isinstance(section, dict):
            return section

        return {}

    @staticmethod
    def _set_combo_text(combo: QComboBox, value: str) -> None:
        index = combo.findText(value)

        if index >= 0:
            combo.setCurrentIndex(index)
