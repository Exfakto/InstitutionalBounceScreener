import sqlite3

from database.manager import DatabaseManager
from database.schema import WATCHLIST_TABLE
from services.watchlist_service import WatchlistService


def build_service():
    manager = DatabaseManager.__new__(DatabaseManager)
    manager.connection = sqlite3.connect(":memory:")
    manager.connection.row_factory = sqlite3.Row
    manager.cursor = manager.connection.cursor()
    manager.cursor.execute(WATCHLIST_TABLE)
    manager.connection.commit()
    return WatchlistService(manager)


def test_service_add_item_returns_structured_result():
    service = build_service()

    result = service.add_item(
        " aapl ",
        company_name="Apple Inc.",
        notes="Watching support",
        source="Research Preview",
    )

    assert result["success"] is True
    assert result["message"] == "Watchlist item added."
    assert result["item"]["ticker"] == "AAPL"
    assert result["item"]["status"] == "Watching"
    assert result["count"] == 1
    service.database_manager.close()


def test_service_duplicate_ticker_returns_existing_item():
    service = build_service()
    first = service.add_item("MSFT", company_name="Microsoft")

    second = service.add_item(" msft ", company_name="Other")

    assert second["success"] is True
    assert second["message"] == "Watchlist item already exists."
    assert second["item"]["id"] == first["item"]["id"]
    assert second["item"]["company_name"] == "Microsoft"
    assert second["count"] == 1
    service.database_manager.close()


def test_service_update_status():
    service = build_service()
    item = service.add_item("NVDA")["item"]

    result = service.update_item(item["id"], status="Ready")

    assert result["success"] is True
    assert result["item"]["status"] == "Ready"
    service.database_manager.close()


def test_service_update_notes():
    service = build_service()
    item = service.add_item("AMZN")["item"]

    result = service.update_item(item["id"], notes="Wait for tighter stop")

    assert result["success"] is True
    assert result["item"]["notes"] == "Wait for tighter stop"
    service.database_manager.close()


def test_service_remove_item():
    service = build_service()
    item = service.add_item("META")["item"]

    result = service.remove_item(item["id"])

    assert result["success"] is True
    assert result["message"] == "Watchlist item removed."
    assert result["count"] == 0
    service.database_manager.close()


def test_service_get_all_and_by_status():
    service = build_service()
    service.add_item("AAPL")
    service.add_item("TSLA", status="Rejected")

    all_result = service.get_items()
    rejected_result = service.get_items(status="Rejected")

    assert all_result["success"] is True
    assert all_result["count"] == 2
    assert rejected_result["count"] == 1
    assert rejected_result["item"][0]["ticker"] == "TSLA"
    service.database_manager.close()


def test_service_get_by_ticker():
    service = build_service()
    service.add_item("goog", status="Ready")

    result = service.get_item_by_ticker("GOOG")

    assert result["success"] is True
    assert result["item"]["ticker"] == "GOOG"
    assert result["item"]["status"] == "Ready"
    service.database_manager.close()


def test_service_count_by_status():
    service = build_service()
    service.add_item("AAPL", status="Watching")
    service.add_item("MSFT", status="Watching")
    service.add_item("NFLX", status="Closed")

    result = service.count_items(status="Watching")

    assert result["success"] is True
    assert result["count"] == 2
    service.database_manager.close()


def test_service_missing_ticker_fails_safely():
    service = build_service()

    result = service.add_item(" ")

    assert result["success"] is False
    assert result["message"] == "Ticker is required."
    assert result["item"] is None
    service.database_manager.close()


def test_service_missing_item_update_and_remove():
    service = build_service()

    update_result = service.update_item(999, status="Ready")
    remove_result = service.remove_item(999)

    assert update_result["success"] is False
    assert update_result["message"] == "Watchlist item not found."
    assert remove_result["success"] is False
    assert remove_result["message"] == "Watchlist item not found."
    service.database_manager.close()


def test_service_rejects_invalid_status():
    service = build_service()

    result = service.add_item("AAPL", status="Invalid")

    assert result["success"] is False
    assert result["message"] == "Invalid watchlist status."
    service.database_manager.close()
