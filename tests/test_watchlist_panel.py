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
    panel.refresh_intelligence(
        {
            "total_items": 2,
            "ready_count": 1,
            "watching_count": 1,
            "high_conviction_count": 1,
            "average_opportunity_score": 88.5,
            "warning_count": 0,
            "top_candidates": [{"ticker": "AAPL", "opportunity_score": 91}],
        }
    )

    panel.clear()

    assert panel.table.rowCount() == 0
    assert panel.selected_item_id() is None
    assert panel.intelligence_labels["total_items"].text() == "--"
    assert panel.top_candidates_table.rowCount() == 0
    assert panel.intelligence_empty_label.text() == "No watchlist intelligence available."


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


def test_watchlist_panel_empty_intelligence(app):
    panel = WatchlistPanel()

    panel.refresh_intelligence(
        {
            "total_items": 0,
            "ready_count": 0,
            "watching_count": 0,
            "high_conviction_count": 0,
            "average_opportunity_score": None,
            "warning_count": 0,
            "top_candidates": [],
            "weak_candidates": [],
            "stale_items": [],
        }
    )

    assert panel.intelligence_empty_label.text() == "No watchlist intelligence available."
    assert panel.intelligence_labels["total_items"].text() == "--"
    assert panel.top_candidates_table.rowCount() == 0


def test_watchlist_panel_populated_intelligence(app):
    panel = WatchlistPanel()

    panel.refresh_intelligence(
        {
            "total_items": 3,
            "ready_count": 1,
            "watching_count": 2,
            "high_conviction_count": 1,
            "average_opportunity_score": 82.4,
            "warning_count": 2,
            "top_candidates": [
                {
                    "ticker": "AAPL",
                    "company_name": "Apple Inc.",
                    "status": "Ready",
                    "opportunity_score": 91.0,
                }
            ],
            "weak_candidates": [
                {"ticker": "TSLA", "status": "Watching", "opportunity_score": 42.0}
            ],
            "stale_items": [
                {"ticker": "MSFT", "status": "Watching", "updated_at": "2026-06-20"}
            ],
        }
    )

    assert panel.intelligence_empty_label.text() == ""
    assert panel.intelligence_labels["total_items"].text() == "3"
    assert panel.intelligence_labels["ready_count"].text() == "1"
    assert panel.intelligence_labels["watching_count"].text() == "2"
    assert panel.intelligence_labels["high_conviction_count"].text() == "1"
    assert panel.intelligence_labels["average_opportunity_score"].text() == "82.4"
    assert panel.intelligence_labels["warning_count"].text() == "2"
    assert panel.top_candidates_table.item(0, 0).text() == "AAPL"
    assert panel.top_candidates_table.item(0, 3).text() == "91.0"
    assert panel.weak_candidates_table.item(0, 0).text() == "TSLA"
    assert panel.stale_items_table.item(0, 0).text() == "MSFT"


def test_watchlist_panel_partial_intelligence_uses_placeholders(app):
    panel = WatchlistPanel()

    panel.refresh_intelligence(
        {
            "total_items": 1,
            "ready_count": 0,
            "watching_count": 1,
            "high_conviction_count": 0,
            "average_opportunity_score": None,
            "warning_count": 0,
            "top_candidates": [{"ticker": "AAPL"}],
            "weak_candidates": [],
            "stale_items": [],
        }
    )

    assert panel.intelligence_labels["average_opportunity_score"].text() == "--"
    assert panel.top_candidates_table.item(0, 0).text() == "AAPL"
    assert panel.top_candidates_table.item(0, 1).text() == "--"
    assert panel.top_candidates_table.item(0, 3).text() == "--"


def test_watchlist_panel_repeated_intelligence_refresh_does_not_duplicate_rows(app):
    panel = WatchlistPanel()
    intelligence = {
        "total_items": 1,
        "ready_count": 1,
        "watching_count": 0,
        "high_conviction_count": 1,
        "average_opportunity_score": 91.0,
        "warning_count": 0,
        "top_candidates": [{"ticker": "AAPL", "opportunity_score": 91.0}],
        "weak_candidates": [],
        "stale_items": [],
    }

    panel.refresh_intelligence(intelligence)
    panel.refresh_intelligence(intelligence)

    assert panel.top_candidates_table.rowCount() == 1
    assert panel.top_candidates_table.item(0, 0).text() == "AAPL"
