import csv
import sqlite3
from pathlib import Path

from database.manager import DatabaseManager
from database.schema import MARKET_UNIVERSE_INDEXES, MARKET_UNIVERSE_TABLE
from market.market_universe_importer import MarketUniverseImporter


REQUIRED_HEADERS = [
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


def test_market_universe_template_file_exists():
    assert Path("data/market_universe_template.csv").exists()


def test_market_universe_seed_file_exists():
    assert Path("data/market_universe_seed.csv").exists()


def test_market_universe_seed_has_required_headers():
    with Path("data/market_universe_seed.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        headers = next(reader)

    assert headers == REQUIRED_HEADERS


def test_market_universe_template_has_headers_only():
    with Path("data/market_universe_template.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    assert rows == [REQUIRED_HEADERS]


def test_market_universe_seed_imports_successfully():
    manager = build_manager()

    summary = MarketUniverseImporter(
        "data/market_universe_seed.csv",
        db=manager,
    ).import_csv()
    records = manager.get_active_market_universe_records()

    assert summary["total_rows_read"] == 25
    assert summary["records_imported"] == 25
    assert summary["records_skipped"] == 0
    assert summary["errors"] == []
    assert len(records) == 25
    assert {record["exchange"] for record in records} == {"NASDAQ", "NYSE"}
    assert all(record["security_type"] == "Common Stock" for record in records)
    manager.close()


def test_imported_seed_records_can_be_fetched_from_database():
    manager = build_manager()
    MarketUniverseImporter("data/market_universe_seed.csv", db=manager).import_csv()

    nasdaq = manager.get_market_universe_by_exchange("NASDAQ")
    nyse = manager.get_market_universe_by_exchange("NYSE")

    assert any(record["ticker"] == "AAPL" for record in nasdaq)
    assert any(record["ticker"] == "JPM" for record in nyse)
    assert len(nasdaq) >= 8
    assert len(nyse) >= 12
    manager.close()
