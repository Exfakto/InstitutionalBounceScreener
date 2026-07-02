import pytest
from PySide6.QtWidgets import QApplication

from ui import export_dialog as export_dialog_module
from ui.export_dialog import ExportDialog


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


def test_export_dialog_initialization(app):
    dialog = ExportDialog()

    assert dialog.isModal()
    assert dialog.object_combo.currentText() == "Watchlist"
    assert dialog.format_combo.currentText() == "CSV"
    assert dialog.destination_folder_input.text() == "exports"
    assert dialog.filename_input.text() == "export"


def test_export_dialog_returns_options(app):
    dialog = ExportDialog()

    dialog.object_combo.setCurrentText("Trade Journal")
    dialog.format_combo.setCurrentText("JSON")
    dialog.destination_folder_input.setText("D:/Exports")
    dialog.filename_input.setText("trades")
    dialog.allow_overwrite_checkbox.setChecked(True)

    options = dialog.export_options()

    assert options["object_name"] == "Trade Journal"
    assert options["format"] == "json"
    assert options["destination_path"].endswith("trades.json")
    assert options["allow_overwrite"] is True


def test_export_dialog_browse_updates_destination(app, monkeypatch):
    dialog = ExportDialog()

    monkeypatch.setattr(
        export_dialog_module.QFileDialog,
        "getExistingDirectory",
        lambda *args, **kwargs: "C:/Exports",
    )

    dialog.browse_destination_folder()

    assert dialog.destination_folder_input.text() == "C:/Exports"
    assert "Exports" in dialog.destination_preview_label.text()
    assert dialog.destination_preview_label.text().endswith("export.csv")
