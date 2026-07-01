import sqlite3

from database.manager import DatabaseManager
from database.schema import PAPER_TRADES_TABLE


def build_manager():
    manager = DatabaseManager.__new__(DatabaseManager)
    manager.connection = sqlite3.connect(":memory:")
    manager.connection.row_factory = sqlite3.Row
    manager.cursor = manager.connection.cursor()
    manager.cursor.execute(PAPER_TRADES_TABLE)
    manager.connection.commit()
    return manager


def test_paper_trades_table_initializes():
    manager = build_manager()

    manager.cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'paper_trades'
        """
    )

    assert manager.cursor.fetchone()["name"] == "paper_trades"
    manager.close()


def test_create_trade_normalizes_ticker():
    manager = build_manager()

    trade = manager.create_trade(
        ticker=" aapl ",
        company_name="Apple Inc.",
        entry_date="2026-07-01",
        entry_price=100.0,
        stop_price=95.0,
        target_price=115.0,
        shares=10,
        risk_reward=3.0,
        opportunity_rating="Elite Bounce",
        confidence="High",
        notes="Paper setup",
    )

    assert trade["ticker"] == "AAPL"
    assert trade["company_name"] == "Apple Inc."
    assert trade["status"] == "Watching"
    assert trade["entry_price"] == 100.0
    assert trade["shares"] == 10
    assert manager.count_trades() == 1
    manager.close()


def test_update_trade_fields():
    manager = build_manager()
    trade = manager.create_trade("MSFT")

    updated = manager.update_trade(
        trade["id"],
        status="Entered",
        entry_price=410.25,
        notes="Entry triggered",
    )

    assert updated["status"] == "Entered"
    assert updated["entry_price"] == 410.25
    assert updated["notes"] == "Entry triggered"
    manager.close()


def test_close_trade_sets_exit_fields():
    manager = build_manager()
    trade = manager.create_trade("NVDA", status="Entered")

    closed = manager.close_trade(
        trade["id"],
        exit_date="2026-07-10",
        exit_price=125.50,
        status="Exited Win",
        notes="Target reached",
    )

    assert closed["status"] == "Exited Win"
    assert closed["exit_date"] == "2026-07-10"
    assert closed["exit_price"] == 125.50
    assert closed["notes"] == "Target reached"
    manager.close()


def test_delete_trade():
    manager = build_manager()
    trade = manager.create_trade("META")

    assert manager.delete_trade(trade["id"]) is True
    assert manager.get_trade(trade["id"]) is None
    assert manager.count_trades() == 0
    manager.close()


def test_get_trade_and_trades():
    manager = build_manager()
    first = manager.create_trade("AMZN", status="Watching")
    manager.create_trade("TSLA", status="Entered")

    stored = manager.get_trade(first["id"])
    entered = manager.get_trades(status="Entered")
    amzn = manager.get_trades(ticker="amzn")

    assert stored["ticker"] == "AMZN"
    assert len(entered) == 1
    assert entered[0]["ticker"] == "TSLA"
    assert len(amzn) == 1
    assert amzn[0]["ticker"] == "AMZN"
    manager.close()


def test_count_trades_by_status():
    manager = build_manager()
    manager.create_trade("AAPL", status="Watching")
    manager.create_trade("MSFT", status="Watching")
    manager.create_trade("NFLX", status="Cancelled")

    assert manager.count_trades() == 3
    assert manager.count_trades(status="Watching") == 2
    assert manager.count_trades(status="Cancelled") == 1
    manager.close()


def test_invalid_input_fails_safely():
    manager = build_manager()

    assert manager.create_trade(None) is None
    assert manager.create_trade("   ") is None
    assert manager.create_trade("AAPL", status="Invalid") is None
    assert manager.get_trade(None) is None
    assert manager.count_trades() == 0
    manager.close()


def test_missing_trade_update_close_and_delete_do_not_crash():
    manager = build_manager()
    trade = manager.create_trade("AAPL")

    assert manager.update_trade(trade["id"], ticker=" ") is None
    assert manager.update_trade(trade["id"], status="Invalid") is None
    assert manager.update_trade(999, status="Entered") is None
    assert manager.close_trade(999, status="Exited Loss") is None
    assert manager.delete_trade(999) is False
    manager.close()


def test_trade_ids_are_not_duplicated():
    manager = build_manager()
    first = manager.create_trade("AAPL")
    second = manager.create_trade("AAPL")

    assert first["id"] != second["id"]
    assert manager.count_trades() == 2
    manager.close()
