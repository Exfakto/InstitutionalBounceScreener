import sqlite3

from database.manager import DatabaseManager
from database.schema import MARKET_UNIVERSE_INDEXES, MARKET_UNIVERSE_TABLE
from market.market_universe_importer import MarketUniverseImporter


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


def write_csv(path, rows):
    headers = [
        "ticker",
        "company_name",
        "exchange",
        "security_type",
        "sector",
        "industry",
        "market_cap",
        "price",
        "average_volume",
        "average_dollar_volume",
        "is_active",
        "last_updated",
    ]
    lines = [",".join(headers)]
    lines.extend(",".join(str(row.get(header, "")) for header in headers) for row in rows)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def test_import_market_universe_valid_rows(tmp_path):
    manager = build_manager()
    csv_path = write_csv(
        tmp_path / "universe.csv",
        [
            {
                "ticker": "AAPL",
                "company_name": "Apple Inc.",
                "exchange": "NASDAQ",
                "security_type": "Common Stock",
                "sector": "Technology",
                "industry": "Consumer Electronics",
                "market_cap": 3000000000000,
                "price": 200,
                "average_volume": 50000000,
                "average_dollar_volume": 10000000000,
                "is_active": "true",
                "last_updated": "2026-07-03",
            }
        ],
    )

    summary = MarketUniverseImporter(csv_path, db=manager).import_csv()
    records = manager.get_active_market_universe_records()

    assert summary == {
        "total_rows_read": 1,
        "records_imported": 1,
        "records_skipped": 0,
        "errors": [],
    }
    assert records[0]["ticker"] == "AAPL"
    assert records[0]["company_name"] == "Apple Inc."
    assert records[0]["exchange"] == "NASDAQ"
    manager.close()


def test_import_market_universe_skips_invalid_rows(tmp_path):
    manager = build_manager()
    csv_path = write_csv(
        tmp_path / "universe.csv",
        [
            {"ticker": "", "company_name": "Missing Ticker", "exchange": "NYSE"},
            {"ticker": "MSFT", "company_name": "Missing Exchange", "exchange": ""},
            {"ticker": "IBM", "company_name": "IBM", "exchange": "NYSE"},
        ],
    )

    summary = MarketUniverseImporter(csv_path, db=manager).import_csv()
    records = manager.get_active_market_universe_records()

    assert summary["total_rows_read"] == 3
    assert summary["records_imported"] == 1
    assert summary["records_skipped"] == 2
    assert summary["errors"] == []
    assert [record["ticker"] for record in records] == ["IBM"]
    manager.close()


def test_import_market_universe_normalizes_tickers_and_exchanges(tmp_path):
    manager = build_manager()
    csv_path = write_csv(
        tmp_path / "universe.csv",
        [
            {
                "ticker": " msft ",
                "company_name": " Microsoft ",
                "exchange": "nasdaq global select",
                "price": "410.25",
                "average_volume": "20000000",
            },
            {"ticker": " ibm ", "company_name": " IBM ", "exchange": "New York Stock Exchange"},
        ],
    )

    summary = MarketUniverseImporter(csv_path, db=manager).import_csv()
    records = manager.get_active_market_universe_records()

    assert summary["records_imported"] == 2
    assert records[0]["ticker"] == "IBM"
    assert records[0]["company_name"] == "IBM"
    assert records[0]["exchange"] == "NYSE"
    assert records[1]["ticker"] == "MSFT"
    assert records[1]["exchange"] == "NASDAQ"
    assert records[1]["average_dollar_volume"] == 8205000000.0
    manager.close()


def test_import_market_universe_duplicate_tickers_upsert(tmp_path):
    manager = build_manager()
    csv_path = write_csv(
        tmp_path / "universe.csv",
        [
            {"ticker": "AAPL", "company_name": "Old Apple", "exchange": "NASDAQ"},
            {"ticker": "aapl", "company_name": "Apple Inc.", "exchange": "NASDAQ"},
        ],
    )

    summary = MarketUniverseImporter(csv_path, db=manager).import_csv()
    records = manager.get_active_market_universe_records()

    assert summary["total_rows_read"] == 2
    assert summary["records_imported"] == 2
    assert len(records) == 1
    assert records[0]["ticker"] == "AAPL"
    assert records[0]["company_name"] == "Apple Inc."
    manager.close()


def test_import_market_universe_summary_for_missing_file(tmp_path):
    manager = build_manager()
    summary = MarketUniverseImporter(tmp_path / "missing.csv", db=manager).import_csv()

    assert summary["total_rows_read"] == 0
    assert summary["records_imported"] == 0
    assert summary["records_skipped"] == 0
    assert summary["errors"]
    manager.close()


def test_import_market_universe_bad_numeric_values_do_not_crash(tmp_path):
    manager = build_manager()
    csv_path = write_csv(
        tmp_path / "universe.csv",
        [
            {
                "ticker": "TSLA",
                "company_name": "Tesla",
                "exchange": "NASDAQ",
                "market_cap": "not-a-number",
                "price": "bad",
                "average_volume": "",
            }
        ],
    )

    summary = MarketUniverseImporter(csv_path, db=manager).import_csv()
    records = manager.get_active_market_universe_records()

    assert summary["records_imported"] == 1
    assert summary["records_skipped"] == 0
    assert records[0]["market_cap"] is None
    assert records[0]["price"] is None
    assert records[0]["average_volume"] is None
    manager.close()
