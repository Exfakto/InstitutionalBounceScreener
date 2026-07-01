import sqlite3

from database.manager import DatabaseManager
from database.schema import WATCHLIST_TABLE


def build_manager():
    manager = DatabaseManager.__new__(DatabaseManager)
    manager.connection = sqlite3.connect(":memory:")
    manager.connection.row_factory = sqlite3.Row
    manager.cursor = manager.connection.cursor()
    manager.cursor.execute(WATCHLIST_TABLE)
    manager.connection.commit()
    return manager


def test_watchlist_table_initializes():
    manager = build_manager()

    manager.cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'watchlist'
        """
    )

    assert manager.cursor.fetchone()["name"] == "watchlist"
    manager.close()


def test_add_watchlist_item_normalizes_ticker():
    manager = build_manager()

    item = manager.add_watchlist_item(
        " aapl ",
        company_name="Apple Inc.",
        notes="Near support",
        source="Screener",
    )

    assert item["ticker"] == "AAPL"
    assert item["company_name"] == "Apple Inc."
    assert item["status"] == "Watching"
    assert item["notes"] == "Near support"
    assert item["source"] == "Screener"
    assert manager.count_watchlist_items() == 1
    manager.close()


def test_duplicate_ticker_does_not_create_duplicate():
    manager = build_manager()

    first = manager.add_watchlist_item("msft", company_name="Microsoft")
    second = manager.add_watchlist_item("MSFT", company_name="Other")

    assert second["id"] == first["id"]
    assert second["company_name"] == "Microsoft"
    assert manager.count_watchlist_items() == 1
    manager.close()


def test_update_watchlist_status_and_notes():
    manager = build_manager()
    item = manager.add_watchlist_item("NVDA")

    updated_status = manager.update_watchlist_item(item["id"], status="Ready")
    updated_notes = manager.update_watchlist_item(
        item["id"],
        notes="Wait for entry zone",
    )

    assert updated_status["status"] == "Ready"
    assert updated_notes["notes"] == "Wait for entry zone"
    assert updated_notes["status"] == "Ready"
    manager.close()


def test_remove_watchlist_item():
    manager = build_manager()
    item = manager.add_watchlist_item("META")

    assert manager.remove_watchlist_item(item["id"]) is True
    assert manager.count_watchlist_items() == 0
    manager.close()


def test_get_all_and_filter_by_status():
    manager = build_manager()
    manager.add_watchlist_item("AAPL", status="Watching")
    manager.add_watchlist_item("TSLA", status="Rejected")

    all_items = manager.get_watchlist_items()
    rejected_items = manager.get_watchlist_items(status="Rejected")

    assert len(all_items) == 2
    assert len(rejected_items) == 1
    assert rejected_items[0]["ticker"] == "TSLA"
    manager.close()


def test_get_by_ticker_and_count_by_status():
    manager = build_manager()
    manager.add_watchlist_item("amzn", status="Ready")
    manager.add_watchlist_item("goog", status="Ready")
    manager.add_watchlist_item("nflx", status="Closed")

    item = manager.get_watchlist_item_by_ticker("AMZN")

    assert item["ticker"] == "AMZN"
    assert manager.count_watchlist_items(status="Ready") == 2
    assert manager.count_watchlist_items(status="Closed") == 1
    manager.close()


def test_missing_ticker_fails_safely():
    manager = build_manager()

    assert manager.add_watchlist_item(None) is None
    assert manager.add_watchlist_item("   ") is None
    assert manager.get_watchlist_item_by_ticker(None) is None
    assert manager.count_watchlist_items() == 0
    manager.close()


def test_missing_item_update_and_remove_do_not_crash():
    manager = build_manager()

    assert manager.update_watchlist_item(999, status="Ready") is None
    assert manager.remove_watchlist_item(999) is False
    manager.close()
