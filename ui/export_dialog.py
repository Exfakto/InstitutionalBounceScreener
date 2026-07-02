from __future__ import annotations

from pathlib import Path
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
    QVBoxLayout,
    QWidget,
)


class ExportDialog(QDialog):
    """
    Modal export options dialog.
    """

    EXPORT_OBJECTS = [
        "Watchlist",
        "Trade Journal",
        "Portfolio Statistics",
        "Strategy Analytics",
        "Research Preview",
        "Research Report",
    ]
    EXPORT_FORMATS = ["CSV", "JSON"]
    RESEARCH_REPORT_FORMATS = ["JSON", "TXT", "Markdown"]

    def __init__(
        self,
        parent: QWidget | None = None,
        research_report_available: bool = True,
    ) -> None:
        super().__init__(parent)
        self.research_report_available = research_report_available
        self._updating_formats = False

        self.setWindowTitle("Export Center")
        self.setModal(True)
        self.resize(520, 260)

        self.object_combo = QComboBox()
        self.object_combo.addItems(self.EXPORT_OBJECTS)
        self.format_combo = QComboBox()
        self.format_combo.addItems(self.EXPORT_FORMATS)
        self.destination_folder_input = QLineEdit()
        self.destination_folder_input.setText("exports")
        self.filename_input = QLineEdit()
        self.filename_input.setText("export")
        self.allow_overwrite_checkbox = QCheckBox("Allow overwrite")
        self.destination_preview_label = QLabel("--")
        self.availability_label = QLabel("")
        self.availability_label.setWordWrap(True)

        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_destination_folder)
        self.browse_button = browse_button

        folder_layout = QHBoxLayout()
        folder_layout.addWidget(self.destination_folder_input)
        folder_layout.addWidget(browse_button)

        form = QFormLayout()
        form.addRow("Object", self.object_combo)
        form.addRow("Format", self.format_combo)
        form.addRow("Destination folder", folder_layout)
        form.addRow("Filename", self.filename_input)
        form.addRow("", self.allow_overwrite_checkbox)
        form.addRow("Destination", self.destination_preview_label)
        form.addRow("Status", self.availability_label)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.button_box)

        self.object_combo.currentTextChanged.connect(self.update_object_state)
        self.format_combo.currentTextChanged.connect(self.update_destination_preview)
        self.destination_folder_input.textChanged.connect(self.update_destination_preview)
        self.filename_input.textChanged.connect(self.update_destination_preview)
        self.update_object_state()

    def export_options(self) -> dict[str, Any]:
        return {
            "object_name": self.object_combo.currentText(),
            "format": self.format_combo.currentText().lower(),
            "destination_folder": self.destination_folder_input.text().strip(),
            "filename": self.filename_input.text().strip(),
            "destination_path": str(self.destination_path()),
            "allow_overwrite": self.allow_overwrite_checkbox.isChecked(),
        }

    def destination_path(self) -> Path:
        folder = Path(self.destination_folder_input.text().strip() or ".")
        filename = self.filename_input.text().strip() or "export"
        selected_format = self.format_combo.currentText().lower()
        suffix = ".md" if selected_format == "markdown" else f".{selected_format}"

        return (folder / filename).with_suffix(suffix)

    def update_object_state(self) -> None:
        object_name = self.object_combo.currentText()
        selected_format = self.format_combo.currentText()
        formats = (
            self.RESEARCH_REPORT_FORMATS
            if object_name == "Research Report"
            else self.EXPORT_FORMATS
        )

        self._updating_formats = True
        self.format_combo.clear()
        self.format_combo.addItems(formats)
        if selected_format in formats:
            self.format_combo.setCurrentText(selected_format)
        self._updating_formats = False

        unavailable = (
            object_name == "Research Report"
            and not self.research_report_available
        )
        self.availability_label.setText(
            "Research report is unavailable for the current selection."
            if unavailable
            else ""
        )
        save_button = self.button_box.button(QDialogButtonBox.StandardButton.Save)
        if save_button is not None:
            save_button.setEnabled(not unavailable)

        self.update_destination_preview()

    def set_research_report_available(self, available: bool) -> None:
        self.research_report_available = available
        self.update_object_state()

    def browse_destination_folder(self) -> None:
        selected_directory = QFileDialog.getExistingDirectory(
            self,
            "Select Export Directory",
            self.destination_folder_input.text(),
        )

        if selected_directory:
            self.destination_folder_input.setText(selected_directory)

    def update_destination_preview(self) -> None:
        if self._updating_formats:
            return

        self.destination_preview_label.setText(str(self.destination_path()))
