from database.manager import DatabaseManager
from scripts import load_market_universe


def collect_output():
    lines = []
    return lines, lines.append


def test_load_market_universe_cli_successful_import(tmp_path):
    db_path = tmp_path / "universe.db"
    lines, output = collect_output()

    code = load_market_universe.run(
        csv_path="data/market_universe_seed.csv",
        database_path=db_path,
        output=output,
    )

    manager = DatabaseManager(database_path=db_path)
    try:
        records = manager.get_active_market_universe_records()
    finally:
        manager.close()

    assert code == 0
    assert len(records) == 25
    assert "Market Universe Import Summary" in lines[0]
    assert "Total rows read: 25" in lines[0]
    assert "Records imported: 25" in lines[0]
    assert "Records skipped: 0" in lines[0]
    assert "Errors encountered: 0" in lines[0]


def test_load_market_universe_cli_missing_file_path():
    lines, output = collect_output()

    code = load_market_universe.run(output=output)

    assert code == 2
    assert lines == ["CSV path is required."]


def test_load_market_universe_cli_invalid_csv_path(tmp_path):
    lines, output = collect_output()

    code = load_market_universe.run(
        csv_path=tmp_path / "missing.csv",
        output=output,
    )

    assert code == 2
    assert "CSV file not found:" in lines[0]


def test_load_market_universe_cli_summary_output(tmp_path):
    csv_path = tmp_path / "small.csv"
    csv_path.write_text(
        "\n".join(
            [
                "ticker,company_name,exchange,security_type,sector,industry,market_cap,price,average_volume,average_dollar_volume,is_active,last_updated",
                "AAPL,Apple Inc.,NASDAQ,Common Stock,Technology,Consumer Electronics,3000000000000,200,50000000,10000000000,1,2026-07-03",
                ",Missing Ticker,NYSE,Common Stock,Financial Services,Banks,,,,,1,2026-07-03",
            ]
        ),
        encoding="utf-8",
    )
    lines, output = collect_output()

    code = load_market_universe.run(
        csv_path=csv_path,
        database_path=tmp_path / "summary.db",
        output=output,
    )

    assert code == 0
    assert "Total rows read: 2" in lines[0]
    assert "Records imported: 1" in lines[0]
    assert "Records skipped: 1" in lines[0]
    assert "Errors encountered: 0" in lines[0]


def test_load_market_universe_cli_returns_nonzero_on_fatal_import_failure(tmp_path):
    class FailingImporter:
        def __init__(self, path):
            self.path = path

        def import_csv(self):
            return {
                "total_rows_read": 0,
                "records_imported": 0,
                "records_skipped": 0,
                "errors": ["fatal"],
            }

    csv_path = tmp_path / "exists.csv"
    csv_path.write_text("ticker,exchange\nAAPL,NASDAQ\n", encoding="utf-8")
    lines, output = collect_output()

    code = load_market_universe.run(
        csv_path=csv_path,
        importer_factory=FailingImporter,
        output=output,
    )

    assert code == 1
    assert "Errors encountered: 1" in lines[0]
    assert "- fatal" in lines[0]


def test_database_manager_accepts_custom_database_path(tmp_path):
    db_path = tmp_path / "custom.db"
    manager = DatabaseManager(database_path=db_path)
    try:
        manager.cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'market_universe'
            """
        )
        table_name = manager.cursor.fetchone()["name"]
    finally:
        manager.close()

    assert db_path.exists()
    assert table_name == "market_universe"
