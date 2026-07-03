import sqlite3
from types import SimpleNamespace

from database.manager import DatabaseManager
from database.schema import MARKET_UNIVERSE_INDEXES, MARKET_UNIVERSE_TABLE


def build_manager():
    manager = DatabaseManager.__new__(DatabaseManager)
    manager.connection = sqlite3.connect(":memory:")
    manager.connection.row_factory = sqlite3.Row
    manager.cursor = manager.connection.cursor()
    manager.cursor.execute(MARKET_UNIVERSE_TABLE)
    for index_statement in MARKET_UNIVERSE_INDEXES:
        manager.cursor.execute(index_statement)
    manager.connection.commit()
    return manager


def test_market_universe_table_initializes():
    manager = build_manager()

    manager.cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'market_universe'
        """
    )

    assert manager.cursor.fetchone()["name"] == "market_universe"
    manager.close()


def test_market_universe_indexes_initialize():
    manager = build_manager()

    manager.cursor.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'index'
          AND tbl_name = 'market_universe'
        """
    )
    index_names = {row["name"] for row in manager.cursor.fetchall()}

    assert "idx_market_universe_ticker" in index_names
    assert "idx_market_universe_exchange" in index_names
    assert "idx_market_universe_security_type" in index_names
    assert "idx_market_universe_market_cap" in index_names
    assert "idx_market_universe_average_dollar_volume" in index_names
    assert "idx_market_universe_is_active" in index_names
    manager.close()


def test_upsert_market_universe_records_normalizes_and_fetches_active():
    manager = build_manager()

    count = manager.upsert_market_universe_records(
        [
            {
                "ticker": " aapl ",
                "company_name": "Apple Inc.",
                "exchange": "NASDAQ",
                "security_type": "Common Stock",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "market_cap": 3_000_000_000_000,
                "price": 200.0,
                "average_volume": 50_000_000,
                "is_active": True,
                "last_updated": "2026-07-03",
            }
        ]
    )
    records = manager.get_active_market_universe_records()

    assert count == 1
    assert records[0]["ticker"] == "AAPL"
    assert records[0]["company_name"] == "Apple Inc."
    assert records[0]["average_dollar_volume"] == 10_000_000_000
    assert records[0]["is_active"] == 1
    assert records[0]["last_updated"] == "2026-07-03"
    manager.close()


def test_upsert_market_universe_records_updates_existing_record():
    manager = build_manager()
    manager.upsert_market_universe_records(
        [{"ticker": "MSFT", "company_name": "Old", "exchange": "NASDAQ"}]
    )

    manager.upsert_market_universe_records(
        [
            SimpleNamespace(
                ticker="msft",
                company_name="Microsoft",
                exchange="NASDAQ",
                security_type="Common Stock",
                market_cap=2_500_000_000_000,
                price=410.25,
                average_volume=20_000_000,
                average_dollar_volume=8_200_000_000,
                is_active=True,
            )
        ]
    )
    records = manager.get_active_market_universe_records()

    assert len(records) == 1
    assert records[0]["ticker"] == "MSFT"
    assert records[0]["company_name"] == "Microsoft"
    assert records[0]["market_cap"] == 2_500_000_000_000
    manager.close()


def test_get_market_universe_by_exchange():
    manager = build_manager()
    manager.upsert_market_universe_records(
        [
            {"ticker": "AAPL", "exchange": "NASDAQ", "is_active": True},
            {"ticker": "IBM", "exchange": "NYSE", "is_active": True},
            {"ticker": "OLD", "exchange": "NYSE", "is_active": False},
        ]
    )

    nyse_active = manager.get_market_universe_by_exchange("nyse")
    nyse_all = manager.get_market_universe_by_exchange("NYSE", active_only=False)

    assert [record["ticker"] for record in nyse_active] == ["IBM"]
    assert [record["ticker"] for record in nyse_all] == ["IBM", "OLD"]
    manager.close()


def test_deactivate_stale_market_universe_records():
    manager = build_manager()
    manager.upsert_market_universe_records(
        [
            {"ticker": "AAPL", "exchange": "NASDAQ"},
            {"ticker": "MSFT", "exchange": "NASDAQ"},
            {"ticker": "IBM", "exchange": "NYSE"},
        ]
    )

    changed = manager.deactivate_stale_market_universe_records(["aapl", "ibm"])
    active = manager.get_active_market_universe_records()

    assert changed == 1
    assert [record["ticker"] for record in active] == ["AAPL", "IBM"]
    manager.close()


def test_invalid_market_universe_records_are_skipped_safely():
    manager = build_manager()

    count = manager.upsert_market_universe_records(
        [None, {}, {"ticker": "   "}, {"ticker": "TSLA"}]
    )

    assert count == 1
    assert manager.get_active_market_universe_records()[0]["ticker"] == "TSLA"
    assert manager.get_market_universe_by_exchange(None) == []
    manager.close()
