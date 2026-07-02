from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from controllers.diagnostics_controller import DiagnosticsController


class AboutDialog(QDialog):
    """
    Modal About and Diagnostics dialog.
    """

    DESCRIPTION = (
        "Local-first institutional bounce research workstation for screening, "
        "trade planning, portfolio diagnostics, and provider-backed market data."
    )

    def __init__(
        self,
        controller: DiagnosticsController | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.controller = controller or DiagnosticsController()

        self.setWindowTitle("About & Diagnostics")
        self.setModal(True)
        self.resize(620, 520)

        self.app_name_label = QLabel("--")
        self.app_name_label.setObjectName("AboutDialogTitle")
        self.version_label = QLabel("--")
        self.description_label = QLabel(self.DESCRIPTION)
        self.description_label.setWordWrap(True)

        self.diagnostics_group = QGroupBox("Diagnostics")
        self.diagnostics_layout = QFormLayout(self.diagnostics_group)
        self.diagnostic_labels: dict[str, QLabel] = {}

        self.diagnostics_text = QTextEdit()
        self.diagnostics_text.setReadOnly(True)
        self.diagnostics_text.setMinimumHeight(150)

        self.copy_button = QPushButton("Copy Diagnostics")
        self.copy_button.clicked.connect(self.copy_diagnostics)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(self.app_name_label)
        layout.addWidget(self.version_label)
        layout.addWidget(self.description_label)
        layout.addWidget(self.diagnostics_group)
        layout.addWidget(self.diagnostics_text)
        layout.addWidget(self.copy_button)
        layout.addWidget(self.button_box)

        self.load_diagnostics()

    def load_diagnostics(self) -> None:
        diagnostics = self.controller.get_diagnostics()
        self.app_name_label.setText(str(diagnostics.get("app_name") or "--"))
        self.version_label.setText(f"Version: {diagnostics.get('version') or '--'}")
        self._render_diagnostics(diagnostics)
        self.diagnostics_text.setPlainText(self.controller.diagnostics_text())

    def copy_diagnostics(self) -> None:
        QApplication.clipboard().setText(self.diagnostics_text.toPlainText())

    def _render_diagnostics(self, diagnostics: dict[str, Any]) -> None:
        labels = [
            ("python_version", "Python"),
            ("operating_system", "Operating System"),
            ("active_provider", "Active Provider"),
            ("provider_config_path", "Provider Config"),
            ("database_path", "Database Path"),
            ("working_directory", "Working Directory"),
            ("log_path", "Log Path"),
            ("test_build_mode", "Test/Build Mode"),
        ]

        for key, label_text in labels:
            label = self.diagnostic_labels.get(key)

            if label is None:
                label = QLabel("--")
                label.setTextInteractionFlags(label.textInteractionFlags())
                self.diagnostics_layout.addRow(label_text, label)
                self.diagnostic_labels[key] = label

            label.setText(str(diagnostics.get(key) or "--"))
