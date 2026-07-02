from __future__ import annotations

from typing import Any

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
    QPushButton,
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
        self.resize(560, 420)

        self.tabs = QTabWidget()
        self._build_general_tab()
        self._build_providers_tab()
        self._build_refresh_tab()
        self._build_appearance_tab()
        self._build_paths_tab()

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.save_settings)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addWidget(self.button_box)

        self.load_settings()

    def load_settings(self) -> None:
        settings = self.controller.load_settings()
        self._apply_settings(settings)
        self.update_provider_status(self.controller.provider_status())

    def save_settings(self) -> None:
        self.controller.save_settings(self.settings_from_ui())
        self.accept()

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

    def _build_general_tab(self) -> None:
        tab = QWidget()
        layout = QFormLayout(tab)

        self.default_workspace_input = QLineEdit()
        self.auto_save_layout_checkbox = QCheckBox("Auto-save layout")
        self.remember_last_ticker_checkbox = QCheckBox("Remember last ticker")

        layout.addRow("Default workspace", self.default_workspace_input)
        layout.addRow("", self.auto_save_layout_checkbox)
        layout.addRow("", self.remember_last_ticker_checkbox)

        self.tabs.addTab(tab, "General")

    def _build_providers_tab(self) -> None:
        tab = QWidget()
        layout = QFormLayout(tab)

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
        tab = QWidget()
        layout = QFormLayout(tab)

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
        tab = QWidget()
        layout = QFormLayout(tab)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light (placeholder)"])
        self.font_scaling_combo = QComboBox()
        self.font_scaling_combo.addItems(["100%", "110% (placeholder)", "125% (placeholder)"])

        layout.addRow("Theme", self.theme_combo)
        layout.addRow("Font scaling", self.font_scaling_combo)

        self.tabs.addTab(tab, "Appearance")

    def _build_paths_tab(self) -> None:
        tab = QWidget()
        layout = QFormLayout(tab)

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
