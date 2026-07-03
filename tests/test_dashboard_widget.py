from datetime import datetime

import pytest
from PySide6.QtWidgets import QApplication

from ui.widgets.dashboard import InstitutionalDashboard


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


def test_dashboard_activity_feed_exists(app):
    dashboard = InstitutionalDashboard()

    assert dashboard.activity_feed_table is not None
    assert dashboard.clear_activity_button.text() == "Clear Log"
    assert dashboard.activity_feed_empty.isHidden() is False


def test_dashboard_add_activity_appends_entries(app):
    dashboard = InstitutionalDashboard()
    timestamp = datetime(2026, 7, 3, 10, 15, 0)

    entry = dashboard.add_activity(
        "Universe update complete",
        status="success",
        timestamp=timestamp,
    )

    assert entry["timestamp"] == "2026-07-03 10:15:00"
    assert entry["status"] == "success"
    assert dashboard.activity_count() == 1
    assert dashboard.activity_feed_table.rowCount() == 1
    assert dashboard.activity_feed_table.item(0, 1).text() == "OK"
    assert dashboard.activity_feed_table.item(0, 2).text() == "Universe update complete"
    assert dashboard.activity_feed_empty.isHidden() is True


def test_dashboard_clear_activity_removes_entries(app):
    dashboard = InstitutionalDashboard()
    dashboard.add_activity("Screener run complete", status="success")

    dashboard.clear_activity()

    assert dashboard.activity_count() == 0
    assert dashboard.activity_feed_table.rowCount() == 0
    assert dashboard.activity_feed_empty.isHidden() is False


def test_dashboard_activity_normalizes_unknown_status(app):
    dashboard = InstitutionalDashboard()

    dashboard.add_activity("Unknown status", status="custom")

    assert dashboard.activity_entries[0]["status"] == "info"
    assert dashboard.activity_feed_table.item(0, 1).text() == "INFO"
