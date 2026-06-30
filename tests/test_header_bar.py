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


def test_header_bar_setters_update_displayed_text(app):
    header = HeaderBar()

    header.set_title("Research Console")
    header.set_version("v2.1")
    header.set_status("Running")

    assert header.title_text() == "Research Console"
    assert header.version_text() == "v2.1"
    assert header.status_text() == "Running"
