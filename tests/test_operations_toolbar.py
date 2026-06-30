import pytest
from PySide6.QtWidgets import QApplication

from ui.widgets.operations_toolbar import OperationsToolbar


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


def test_operations_toolbar_contains_expected_buttons(app):
    toolbar = OperationsToolbar()

    assert list(toolbar.buttons) == [
        "update_universe",
        "download_prices",
        "calculate_indicators",
        "detect_support",
        "validate_bounces",
        "run_screener",
        "open_detail",
    ]
    assert toolbar.buttons["update_universe"].text() == "Update Universe"
    assert toolbar.buttons["download_prices"].text() == "Download Prices"
    assert toolbar.buttons["calculate_indicators"].text() == "Calculate Indicators"
    assert toolbar.buttons["detect_support"].text() == "Detect Support"
    assert toolbar.buttons["validate_bounces"].text() == "Validate Bounces"
    assert toolbar.buttons["run_screener"].text() == "Run Screener"
    assert toolbar.buttons["open_detail"].text() == "Open Detail"


def test_operations_toolbar_open_detail_starts_disabled(app):
    toolbar = OperationsToolbar()

    assert toolbar.is_open_detail_enabled() is False

    toolbar.set_open_detail_enabled(True)

    assert toolbar.is_open_detail_enabled() is True


def test_operations_toolbar_emits_operation_signals(app):
    toolbar = OperationsToolbar()
    emitted = []

    toolbar.update_universe_requested.connect(lambda: emitted.append("update"))
    toolbar.download_prices_requested.connect(lambda: emitted.append("download"))
    toolbar.calculate_indicators_requested.connect(lambda: emitted.append("indicators"))
    toolbar.detect_support_requested.connect(lambda: emitted.append("support"))
    toolbar.validate_bounces_requested.connect(lambda: emitted.append("bounces"))
    toolbar.run_screener_requested.connect(lambda: emitted.append("screener"))

    toolbar.buttons["update_universe"].click()
    toolbar.buttons["download_prices"].click()
    toolbar.buttons["calculate_indicators"].click()
    toolbar.buttons["detect_support"].click()
    toolbar.buttons["validate_bounces"].click()
    toolbar.buttons["run_screener"].click()

    assert emitted == [
        "update",
        "download",
        "indicators",
        "support",
        "bounces",
        "screener",
    ]


def test_operations_toolbar_emits_open_detail_when_enabled(app):
    toolbar = OperationsToolbar()
    emitted = []

    toolbar.open_detail_requested.connect(lambda: emitted.append("detail"))
    toolbar.buttons["open_detail"].click()

    assert emitted == []

    toolbar.set_open_detail_enabled(True)
    toolbar.buttons["open_detail"].click()

    assert emitted == ["detail"]
