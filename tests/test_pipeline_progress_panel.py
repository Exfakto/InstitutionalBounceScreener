from datetime import datetime

import pytest
from PySide6.QtWidgets import QApplication

from ui.widgets.pipeline_progress_panel import PipelineProgressPanel


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


def test_pipeline_progress_panel_creation(app):
    panel = PipelineProgressPanel()

    assert panel.title_label.text() == "Pipeline Progress"
    assert list(panel.step_widgets) == [
        "universe",
        "prices",
        "indicators",
        "support",
        "bounce_validation",
        "screener",
    ]
    assert panel.progress_bar.value() == 0


def test_pipeline_progress_panel_status_update(app):
    panel = PipelineProgressPanel()
    timestamp = datetime(2026, 7, 3, 9, 30, 0)

    panel.update_step("prices", "Complete", timestamp)

    assert panel.status_for("prices") == "Complete"
    assert panel.step_widgets["prices"]["status"].text() == "Complete"
    assert panel.timestamp_text_for("prices") == "Last: 2026-07-03 09:30:00"


def test_pipeline_progress_panel_progress_percentage(app):
    panel = PipelineProgressPanel()

    panel.update_step("universe", "Complete")
    panel.update_step("prices", "Complete")
    panel.update_step("indicators", "Running")

    assert panel.progress_percentage() == 33
    assert panel.progress_bar.value() == 33
    assert panel.progress_label.text() == "33% Complete"


def test_pipeline_progress_panel_missing_timestamps_are_safe(app):
    panel = PipelineProgressPanel()

    panel.update_step("support", "Pending", None)

    assert panel.status_for("support") == "Pending"
    assert panel.timestamp_text_for("support") == "Last: N/A"


def test_pipeline_progress_panel_unknown_step_is_ignored(app):
    panel = PipelineProgressPanel()

    panel.update_step("unknown", "Complete")

    assert panel.progress_percentage() == 0
