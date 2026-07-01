import pytest
from PySide6.QtWidgets import QApplication

from ui.widgets.watchlist_panel import WatchlistPanel


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance()

    if application is None:
        application = QApplication([])

    return application


def sample_items():
    return [
        {
            "id": 1,
            "ticker": "AAPL",
            "company_name": "Apple Inc.",
            "status": "Watching",
            "notes": "Near support",
            "added_at": "2026-07-01 10:00:00",
        },
        {
            "id": 2,
            "ticker": "MSFT",
            "company_name": "Microsoft Corporation",
            "status": "Ready",
            "notes": None,
            "added_at": "2026-07-01 11:00:00",
        },
    ]


def test_watchlist_panel_displays_items(app):
    panel = WatchlistPanel()

    panel.refresh_items(sample_items())

    assert panel.table.rowCount() == 2
    assert panel.table.item(0, 0).text() == "AAPL"
    assert panel.table.item(0, 1).text() == "Apple Inc."
    assert panel.table.item(0, 2).text() == "Watching"
    assert panel.table.item(0, 3).text() == "Near support"
    assert panel.table.item(1, 0).text() == "MSFT"
    assert panel.table.item(1, 3).text() == ""


def test_watchlist_panel_selection_returns_item_id(app):
    panel = WatchlistPanel()
    panel.refresh_items(sample_items())

    panel.table.selectRow(1)

    assert panel.selected_item_id() == 2


def test_watchlist_panel_missing_selection_returns_none(app):
    panel = WatchlistPanel()
    panel.refresh_items(sample_items())

    assert panel.selected_item_id() is None


def test_watchlist_panel_clear(app):
    panel = WatchlistPanel()
    panel.refresh_items(sample_items())

    panel.clear()

    assert panel.table.rowCount() == 0
    assert panel.selected_item_id() is None


def test_watchlist_panel_missing_items_handled_safely(app):
    panel = WatchlistPanel()

    panel.refresh_items(None)

    assert panel.table.rowCount() == 0


def test_watchlist_panel_buttons_emit_signals(app):
    panel = WatchlistPanel()
    emitted = []

    panel.add_selected_candidate_requested.connect(lambda: emitted.append("add"))
    panel.remove_selected_requested.connect(lambda: emitted.append("remove"))
    panel.refresh_requested.connect(lambda: emitted.append("refresh"))

    panel.add_button.click()
    panel.remove_button.click()
    panel.refresh_button.click()

    assert emitted == ["add", "remove", "refresh"]
