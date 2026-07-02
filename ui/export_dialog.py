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
    ]
    EXPORT_FORMATS = ["CSV", "JSON"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

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

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.button_box)

        self.object_combo.currentTextChanged.connect(self.update_destination_preview)
        self.format_combo.currentTextChanged.connect(self.update_destination_preview)
        self.destination_folder_input.textChanged.connect(self.update_destination_preview)
        self.filename_input.textChanged.connect(self.update_destination_preview)
        self.update_destination_preview()

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
        suffix = f".{self.format_combo.currentText().lower()}"

        return (folder / filename).with_suffix(suffix)

    def browse_destination_folder(self) -> None:
        selected_directory = QFileDialog.getExistingDirectory(
            self,
            "Select Export Directory",
            self.destination_folder_input.text(),
        )

        if selected_directory:
            self.destination_folder_input.setText(selected_directory)

    def update_destination_preview(self) -> None:
        self.destination_preview_label.setText(str(self.destination_path()))
