from datetime import datetime

import pytest
from PySide6.QtWidgets import QApplication

from ui.widgets.header_bar import HeaderBar


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


def test_header_bar_defaults(app):
    header = HeaderBar()

    assert header.title_text() == "Institutional Bounce Platform"
    assert header.version_text() == "v2.0"
    assert header.status_text() == "Ready"
    assert header.subtitle_text() == "Institutional Research Workstation"
    assert header.market_status_text() == "Market: --"
    assert header.auto_refresh_text_value() == "Auto-refresh: --"
    assert header.refresh_interval_text() == "Interval: --"
    assert header.last_refresh_text() == "Last refresh: --"
    assert header.next_refresh_text() == "Next refresh: --"


def test_header_bar_setters_update_displayed_text(app):
    header = HeaderBar()

    header.set_title("Research Console")
    header.set_version("v2.1")
    header.set_status("Running")

    assert header.title_text() == "Research Console"
    assert header.version_text() == "v2.1"
    assert header.status_text() == "Running"


def test_header_bar_displays_refresh_status(app):
    header = HeaderBar()

    header.set_refresh_status(
        market_status="Open",
        auto_refresh=True,
        refresh_interval=300,
        last_refresh=datetime(2026, 7, 1, 10, 42),
        next_refresh=datetime(2026, 7, 1, 10, 47),
    )

    assert header.market_status_text() == "Market: Open"
    assert header.auto_refresh_text_value() == "Auto-refresh: On"
    assert header.refresh_interval_text() == "Interval: 5 min"
    assert header.last_refresh_text() == "Last refresh: 10:42"
    assert header.next_refresh_text() == "Next refresh: 10:47"


def test_header_bar_displays_refresh_off(app):
    header = HeaderBar()

    header.set_refresh_status(
        market_status="Weekend",
        auto_refresh=False,
        refresh_interval=None,
    )

    assert header.market_status_text() == "Market: Weekend"
    assert header.auto_refresh_text_value() == "Auto-refresh: Off"
    assert header.refresh_interval_text() == "Interval: --"


def test_header_bar_safe_missing_values(app):
    header = HeaderBar()

    header.set_refresh_status()

    assert header.market_status_text() == "Market: --"
    assert header.auto_refresh_text_value() == "Auto-refresh: --"
    assert header.refresh_interval_text() == "Interval: --"
    assert header.last_refresh_text() == "Last refresh: --"
    assert header.next_refresh_text() == "Next refresh: --"
