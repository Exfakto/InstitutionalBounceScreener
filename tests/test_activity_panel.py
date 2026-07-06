import pytest
from PySide6.QtWidgets import QApplication, QTextEdit

from ui.widgets.activity_panel import ActivityPanel


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


def test_activity_panel_updates_status_and_progress(app):
    panel = ActivityPanel()

    panel.set_status("Running")
    panel.set_progress(42)

    assert panel.status_text() == "Running"
    assert panel.progress_value() == 42


def test_activity_panel_appends_and_clears_log(app):
    panel = ActivityPanel()

    panel.append_log("First message")
    panel.append_log("Second message")

    assert "First message" in panel.log_text()
    assert "Second message" in panel.log_text()

    panel.clear_log()

    assert panel.log_text() == ""


def test_activity_panel_wraps_long_messages_and_exposes_tooltip(app):
    panel = ActivityPanel()
    message = "Provider polygon returned a long diagnostic message for AAPL with pagination and retry details"

    panel.append_log(message)

    assert panel.maximumHeight() > 260
    assert panel.activity_log.lineWrapMode() == QTextEdit.WidgetWidth
    assert panel.activity_log.toolTip() == message


def test_activity_panel_reset_restores_ready_state(app):
    panel = ActivityPanel()

    panel.set_status("Complete")
    panel.set_progress(100)
    panel.reset()

    assert panel.status_text() == "Ready"
    assert panel.progress_value() == 0
