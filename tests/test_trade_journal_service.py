import sqlite3

from database.manager import DatabaseManager
from database.schema import PAPER_TRADES_TABLE
from services.trade_journal_service import TradeJournalService


def build_service():
    manager = DatabaseManager.__new__(DatabaseManager)
    manager.connection = sqlite3.connect(":memory:")
    manager.connection.row_factory = sqlite3.Row
    manager.cursor = manager.connection.cursor()
    manager.cursor.execute(PAPER_TRADES_TABLE)
    manager.connection.commit()
    return TradeJournalService(manager)


def test_service_create_trade_returns_structured_result():
    service = build_service()

    result = service.create_trade(
        ticker=" aapl ",
        company_name="Apple Inc.",
        entry_price=100.0,
        stop_price=95.0,
        target_price=115.0,
        status="watching",
    )

    assert result["success"] is True
    assert result["message"] == "Trade created."
    assert result["trade"]["ticker"] == "AAPL"
    assert result["trade"]["status"] == "Watching"
    assert result["count"] == 1
    service.database_manager.close()


def test_service_update_trade():
    service = build_service()
    trade = service.create_trade(ticker="MSFT")["trade"]

    result = service.update_trade(
        trade["id"],
        status="Entered",
        notes="Entry filled",
    )

    assert result["success"] is True
    assert result["message"] == "Trade updated."
    assert result["trade"]["status"] == "Entered"
    assert result["trade"]["notes"] == "Entry filled"
    service.database_manager.close()


def test_service_close_trade():
    service = build_service()
    trade = service.create_trade(ticker="NVDA", status="Entered")["trade"]

    result = service.close_trade(
        trade["id"],
        exit_date="2026-07-10",
        exit_price=128.0,
        status="Exited Win",
    )

    assert result["success"] is True
    assert result["message"] == "Trade closed."
    assert result["trade"]["status"] == "Exited Win"
    assert result["trade"]["exit_price"] == 128.0
    service.database_manager.close()


def test_service_delete_trade():
    service = build_service()
    trade = service.create_trade(ticker="META")["trade"]

    result = service.delete_trade(trade["id"])

    assert result["success"] is True
    assert result["message"] == "Trade deleted."
    assert result["count"] == 0
    service.database_manager.close()


def test_service_get_trade_and_trades():
    service = build_service()
    first = service.create_trade(ticker="AMZN", status="Watching")["trade"]
    service.create_trade(ticker="TSLA", status="Entered")

    stored = service.get_trade(first["id"])
    entered = service.get_trades(status="Entered")

    assert stored["success"] is True
    assert stored["trade"]["ticker"] == "AMZN"
    assert entered["success"] is True
    assert entered["count"] == 1
    assert entered["trades"][0]["ticker"] == "TSLA"
    service.database_manager.close()


def test_service_count_trades():
    service = build_service()
    service.create_trade(ticker="AAPL", status="Watching")
    service.create_trade(ticker="MSFT", status="Watching")
    service.create_trade(ticker="NFLX", status="Cancelled")

    result = service.count_trades(status="Watching")

    assert result["success"] is True
    assert result["count"] == 2
    service.database_manager.close()


def test_service_invalid_ticker_fails_safely():
    service = build_service()

    result = service.create_trade(ticker=" ")

    assert result["success"] is False
    assert result["message"] == "Ticker is required."
    assert result["trade"] is None
    service.database_manager.close()


def test_service_invalid_status_fails_safely():
    service = build_service()

    create_result = service.create_trade(ticker="AAPL", status="Invalid")
    update_result = service.update_trade(1, status="Invalid")
    list_result = service.get_trades(status="Invalid")

    assert create_result["success"] is False
    assert create_result["message"] == "Invalid trade status."
    assert update_result["success"] is False
    assert update_result["message"] == "Invalid trade status."
    assert list_result["success"] is False
    assert list_result["count"] == 0
    service.database_manager.close()


def test_service_missing_trade_operations_fail_safely():
    service = build_service()

    update_result = service.update_trade(999, status="Entered")
    close_result = service.close_trade(999, status="Exited Loss")
    delete_result = service.delete_trade(999)
    get_result = service.get_trade(999)

    assert update_result["success"] is False
    assert update_result["message"] == "Trade not found."
    assert close_result["success"] is False
    assert close_result["message"] == "Trade not found."
    assert delete_result["success"] is False
    assert delete_result["message"] == "Trade not found."
    assert get_result["success"] is False
    assert get_result["message"] == "Trade not found."
    service.database_manager.close()
