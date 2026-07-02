import pandas as pd

from providers.provider_result import ProviderResult
from services.historical_sync_service import HistoricalSyncService


class FakeLiveDataService:
    def __init__(self, results=None):
        self.results = results or {}
        self.calls = []

    def get_price_history(self, ticker, start=None, end=None):
        self.calls.append((ticker, start, end))
        result = self.results.get(ticker)

        if result is None:
            return ProviderResult.ok(data=[], source="fake")

        return result


class FakeDatabaseManager:
    def __init__(self):
        self.rows = {}
        self.commit_count = 0
        self.cursor = FakeCursor(self)

    def commit(self):
        self.commit_count += 1


class FakeCursor:
    def __init__(self, database):
        self.database = database
        self.fetchone_result = None

    def execute(self, sql, params):
        statement = " ".join(sql.split()).upper()

        if statement.startswith("SELECT"):
            ticker, row_date = params
            self.fetchone_result = self.database.rows.get((ticker, row_date))
            return

        if statement.startswith("INSERT"):
            ticker, row_date, open_, high, low, close, volume = params
            self.database.rows[(ticker, row_date)] = {
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            }
            return

        if statement.startswith("UPDATE"):
            open_, high, low, close, volume, ticker, row_date = params
            self.database.rows[(ticker, row_date)] = {
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            }

    def fetchone(self):
        return self.fetchone_result


def price_result(rows):
    return ProviderResult.ok(data=rows, message="ok", source="fake")


def test_sync_one_ticker_inserts_new_rows():
    live = FakeLiveDataService(
        {
            "AAPL": price_result(
                [
                    {
                        "date": "2026-01-02",
                        "Open": 100,
                        "High": 105,
                        "Low": 99,
                        "Close": 104,
                        "Volume": 1000,
                    }
                ]
            )
        }
    )
    database = FakeDatabaseManager()
    service = HistoricalSyncService(live, database)

    summary = service.sync_ticker(" aapl ", start="2026-01-01", end="2026-01-31")

    assert summary["ticker"] == "AAPL"
    assert summary["processed"] == 1
    assert summary["inserted"] == 1
    assert summary["updated"] == 0
    assert summary["skipped"] == 0
    assert database.rows[("AAPL", "2026-01-02")]["close"] == 104.0
    assert live.calls == [("AAPL", "2026-01-01", "2026-01-31")]


def test_sync_multiple_tickers_aggregates_counts():
    live = FakeLiveDataService(
        {
            "AAPL": price_result(
                [{"date": "2026-01-02", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 10}]
            ),
            "MSFT": price_result(
                [{"date": "2026-01-03", "open": 3, "high": 4, "low": 3, "close": 4, "volume": 20}]
            ),
        }
    )
    service = HistoricalSyncService(live, FakeDatabaseManager())

    summary = service.sync_tickers(["aapl", "msft"])

    assert summary["ticker"] == "MULTIPLE"
    assert summary["processed"] == 2
    assert summary["inserted"] == 2
    assert len(summary["tickers"]) == 2


def test_sync_updates_existing_changed_rows():
    live = FakeLiveDataService(
        {
            "AAPL": price_result(
                [{"date": "2026-01-02", "open": 100, "high": 106, "low": 99, "close": 105, "volume": 1000}]
            )
        }
    )
    database = FakeDatabaseManager()
    database.rows[("AAPL", "2026-01-02")] = {
        "open": 100.0,
        "high": 105.0,
        "low": 99.0,
        "close": 104.0,
        "volume": 1000,
    }
    service = HistoricalSyncService(live, database)

    summary = service.sync_ticker("AAPL")

    assert summary["updated"] == 1
    assert database.rows[("AAPL", "2026-01-02")]["close"] == 105.0


def test_sync_skips_duplicate_unchanged_rows():
    live = FakeLiveDataService(
        {
            "AAPL": price_result(
                [{"date": "2026-01-02", "open": 100, "high": 105, "low": 99, "close": 104, "volume": 1000}]
            )
        }
    )
    database = FakeDatabaseManager()
    database.rows[("AAPL", "2026-01-02")] = {
        "open": 100.0,
        "high": 105.0,
        "low": 99.0,
        "close": 104.0,
        "volume": 1000,
    }
    service = HistoricalSyncService(live, database)

    summary = service.sync_ticker("AAPL")

    assert summary["inserted"] == 0
    assert summary["updated"] == 0
    assert summary["skipped"] == 1


def test_provider_failure_fails_safely():
    live = FakeLiveDataService(
        {
            "AAPL": ProviderResult.fail(
                "provider failed",
                source="fake",
                warnings=["planned failure"],
            )
        }
    )
    service = HistoricalSyncService(live, FakeDatabaseManager())

    summary = service.sync_ticker("AAPL")

    assert summary["failed"] == 1
    assert summary["processed"] == 0
    assert "planned failure" in summary["warnings"]
    assert "provider failed" in summary["warnings"]


def test_empty_data_does_not_crash():
    live = FakeLiveDataService({"AAPL": price_result([])})
    service = HistoricalSyncService(live, FakeDatabaseManager())

    summary = service.sync_ticker("AAPL")

    assert summary["processed"] == 0
    assert summary["inserted"] == 0
    assert summary["failed"] == 0
    assert "Provider returned no price history rows." in summary["warnings"]


def test_invalid_row_is_skipped_with_warning():
    live = FakeLiveDataService(
        {
            "AAPL": price_result(
                [{"date": "2026-01-02", "open": 100, "high": 105}]
            )
        }
    )
    service = HistoricalSyncService(live, FakeDatabaseManager())

    summary = service.sync_ticker("AAPL")

    assert summary["processed"] == 1
    assert summary["skipped"] == 1
    assert "Invalid price history row skipped." in summary["warnings"]


def test_missing_ticker_fails_safely():
    live = FakeLiveDataService()
    service = HistoricalSyncService(live, FakeDatabaseManager())

    summary = service.sync_ticker(" ")

    assert summary["ticker"] is None
    assert summary["failed"] == 1
    assert live.calls == []
    assert "Ticker is required." in summary["warnings"]


def test_dataframe_provider_result_is_supported():
    dataframe = pd.DataFrame(
        [
            {
                "Open": 10,
                "High": 11,
                "Low": 9,
                "Close": 10.5,
                "Volume": 100,
            }
        ],
        index=pd.to_datetime(["2026-01-02"]),
    )
    live = FakeLiveDataService({"AAPL": price_result(dataframe)})
    database = FakeDatabaseManager()
    service = HistoricalSyncService(live, database)

    summary = service.sync_ticker("AAPL")

    assert summary["processed"] == 1
    assert summary["inserted"] == 1
    assert database.rows[("AAPL", "2026-01-02")]["close"] == 10.5


def test_summary_counts_mixed_rows():
    live = FakeLiveDataService(
        {
            "AAPL": price_result(
                [
                    {"date": "2026-01-02", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 10},
                    {"date": "bad-date", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 10},
                ]
            )
        }
    )
    service = HistoricalSyncService(live, FakeDatabaseManager())

    summary = service.sync_ticker("AAPL")

    assert summary["processed"] == 2
    assert summary["inserted"] == 1
    assert summary["skipped"] == 1
    assert summary["updated"] == 0
    assert summary["failed"] == 0
