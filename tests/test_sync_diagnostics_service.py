import pandas as pd

from services.sync_diagnostics_service import SyncDiagnosticsService


class FakeDatabaseManager:
    def __init__(self, histories=None, error=None):
        self.histories = histories or {}
        self.error = error
        self.calls = []

    def get_price_history(self, ticker):
        self.calls.append(ticker)

        if self.error is not None:
            raise self.error

        return self.histories.get(ticker, pd.DataFrame())

    def fetch_ohlcv(self, ticker, start_date=None, end_date=None):
        return self.get_price_history(ticker)


def price_history(dates):
    return pd.DataFrame(
        {
            "Open": [100.0] * len(dates),
            "High": [101.0] * len(dates),
            "Low": [99.0] * len(dates),
            "Close": [100.5] * len(dates),
            "Volume": [1000] * len(dates),
        },
        index=pd.to_datetime(dates),
    )


def test_current_ticker():
    db = FakeDatabaseManager(
        {"AAPL": price_history(["2026-07-01", "2026-07-02"])}
    )
    service = SyncDiagnosticsService(db)

    result = service.diagnose_ticker(
        "aapl",
        stale_threshold_days=3,
        today="2026-07-02",
    )

    assert result["ticker"] == "AAPL"
    assert result["status"] == "Current"
    assert result["row_count"] == 2
    assert result["first_date"] == "2026-07-01"
    assert result["last_date"] == "2026-07-02"
    assert result["stale_days"] == 0


def test_stale_ticker():
    db = FakeDatabaseManager({"AAPL": price_history(["2026-06-25"])})
    service = SyncDiagnosticsService(db)

    result = service.diagnose_ticker(
        "AAPL",
        stale_threshold_days=3,
        today="2026-07-02",
    )

    assert result["status"] == "Stale"
    assert result["stale_days"] > 3
    assert result["warnings"]


def test_incomplete_ticker_with_gap():
    db = FakeDatabaseManager(
        {"AAPL": price_history(["2026-07-01", "2026-07-03"])}
    )
    service = SyncDiagnosticsService(db)

    result = service.diagnose_ticker(
        "AAPL",
        start="2026-07-01",
        end="2026-07-03",
        today="2026-07-03",
    )

    assert result["status"] == "Incomplete"
    assert result["missing_days_count"] == 1


def test_polygon_251_row_dataset_open_ended_is_not_incomplete():
    dates = pd.bdate_range(end="2026-07-01", periods=251)
    db = FakeDatabaseManager({"AAPL": price_history(dates)})
    service = SyncDiagnosticsService(db)

    result = service.diagnose_ticker(
        "AAPL",
        stale_threshold_days=3,
        today="2026-07-02",
    )

    assert result["status"] == "Current"
    assert result["row_count"] == 251
    assert result["missing_days_count"] == 0
    assert result["expected_start"] is None
    assert result["expected_end"] is None


def test_weekend_gaps_are_not_incomplete_for_explicit_range():
    db = FakeDatabaseManager(
        {"AAPL": price_history(["2026-07-03", "2026-07-06"])}
    )
    service = SyncDiagnosticsService(db)

    result = service.diagnose_ticker(
        "AAPL",
        start="2026-07-03",
        end="2026-07-06",
        today="2026-07-06",
    )

    assert result["status"] == "Current"
    assert result["missing_days_count"] == 0
    assert result["expected_start"] == "2026-07-03"
    assert result["expected_end"] == "2026-07-06"


def test_holiday_gaps_are_not_incomplete_for_explicit_range():
    db = FakeDatabaseManager(
        {"AAPL": price_history(["2024-07-03", "2024-07-05"])}
    )
    service = SyncDiagnosticsService(db)

    result = service.diagnose_ticker(
        "AAPL",
        start="2024-07-03",
        end="2024-07-05",
        today="2024-07-05",
    )

    assert result["status"] == "Current"
    assert result["missing_days_count"] == 0


def test_open_ended_sync_only_reports_current_stale_or_missing():
    db = FakeDatabaseManager(
        {"AAPL": price_history(["2026-07-01", "2026-07-03"])}
    )
    service = SyncDiagnosticsService(db)

    result = service.diagnose_ticker(
        "AAPL",
        today="2026-07-03",
    )

    assert result["status"] == "Current"
    assert result["missing_days_count"] == 0


def test_explicit_date_range_compares_only_requested_range():
    db = FakeDatabaseManager(
        {
            "AAPL": price_history(
                ["2026-06-30", "2026-07-01", "2026-07-03", "2026-07-06"]
            )
        }
    )
    service = SyncDiagnosticsService(db)

    result = service.diagnose_ticker(
        "AAPL",
        start="2026-07-01",
        end="2026-07-03",
        today="2026-07-03",
    )

    assert result["status"] == "Incomplete"
    assert result["row_count"] == 2
    assert result["first_date"] == "2026-07-01"
    assert result["last_date"] == "2026-07-03"
    assert result["missing_days_count"] == 1


def test_missing_ticker_history():
    db = FakeDatabaseManager({"AAPL": pd.DataFrame()})
    service = SyncDiagnosticsService(db)

    result = service.diagnose_ticker("AAPL")

    assert result["status"] == "Missing"
    assert result["row_count"] == 0
    assert "No local price history rows found." in result["warnings"]


def test_invalid_ticker():
    service = SyncDiagnosticsService(FakeDatabaseManager())

    result = service.diagnose_ticker(" ")

    assert result["status"] == "Error"
    assert "Ticker is required." in result["warnings"]


def test_invalid_date_input():
    service = SyncDiagnosticsService(FakeDatabaseManager())

    result = service.diagnose_ticker("AAPL", start="2026/07/01")

    assert result["status"] == "Error"
    assert "Invalid start date." in result["warnings"]


def test_multiple_tickers():
    db = FakeDatabaseManager(
        {
            "AAPL": price_history(["2026-07-02"]),
            "MSFT": pd.DataFrame(),
        }
    )
    service = SyncDiagnosticsService(db)

    result = service.diagnose_tickers(
        ["AAPL", "MSFT"],
        today="2026-07-02",
    )

    assert result["ticker"] == "MULTIPLE"
    assert result["status"] == "Missing"
    assert len(result["results"]) == 2
    assert result["row_count"] == 1


def test_stale_threshold_controls_status():
    db = FakeDatabaseManager({"AAPL": price_history(["2026-06-30"])})
    service = SyncDiagnosticsService(db)

    current = service.diagnose_ticker(
        "AAPL",
        stale_threshold_days=3,
        today="2026-07-02",
    )
    stale = service.diagnose_ticker(
        "AAPL",
        stale_threshold_days=0,
        today="2026-07-02",
    )

    assert current["status"] == "Current"
    assert stale["status"] == "Stale"


def test_database_error_returns_error_status():
    service = SyncDiagnosticsService(
        FakeDatabaseManager(error=RuntimeError("read failed"))
    )

    result = service.diagnose_ticker("AAPL")

    assert result["status"] == "Error"
    assert "Price history read failed" in result["warnings"][0]
