from tools import sync_diagnostics


class FakeSyncDiagnosticsService:
    def __init__(self, result=None):
        self.result = result or {
            "ticker": "AAPL",
            "row_count": 2,
            "first_date": "2026-07-01",
            "last_date": "2026-07-02",
            "expected_start": None,
            "expected_end": None,
            "missing_days_count": 0,
            "stale_days": 0,
            "status": "Current",
            "warnings": [],
        }
        self.calls = []

    def diagnose_ticker(self, ticker, start=None, end=None, stale_threshold_days=3):
        self.calls.append(("diagnose_ticker", ticker, start, end, stale_threshold_days))
        return self.result

    def diagnose_tickers(self, tickers, start=None, end=None, stale_threshold_days=3):
        self.calls.append(("diagnose_tickers", tickers, start, end, stale_threshold_days))
        return {
            "ticker": "MULTIPLE",
            "results": [self.result],
            "row_count": self.result["row_count"],
            "first_date": None,
            "last_date": None,
            "expected_start": start,
            "expected_end": end,
            "missing_days_count": self.result["missing_days_count"],
            "stale_days": self.result["stale_days"],
            "status": self.result["status"],
            "warnings": self.result["warnings"],
        }


def collect_output():
    lines = []
    return lines, lines.append


def test_cli_single_ticker_output():
    service = FakeSyncDiagnosticsService()
    lines, output = collect_output()

    code = sync_diagnostics.run(
        ticker="aapl",
        service_factory=lambda: service,
        output=output,
    )

    assert code == 0
    assert service.calls == [("diagnose_ticker", "AAPL", None, None, 3)]
    assert "Ticker: AAPL" in lines[0]
    assert "Status: Current" in lines[0]
    assert "Rows: 2" in lines[0]


def test_cli_multiple_tickers_output():
    service = FakeSyncDiagnosticsService()
    lines, output = collect_output()

    code = sync_diagnostics.run(
        tickers="aapl,msft,nvda",
        service_factory=lambda: service,
        output=output,
    )

    assert code == 0
    assert service.calls == [
        ("diagnose_tickers", ["AAPL", "MSFT", "NVDA"], None, None, 3)
    ]
    assert "Ticker: MULTIPLE" in lines[0]


def test_cli_date_arguments():
    service = FakeSyncDiagnosticsService()
    lines, output = collect_output()

    code = sync_diagnostics.run(
        ticker="AAPL",
        start="2024-01-01",
        end="2024-12-31",
        service_factory=lambda: service,
        output=output,
    )

    assert code == 0
    assert service.calls == [
        ("diagnose_ticker", "AAPL", "2024-01-01", "2024-12-31", 3)
    ]


def test_cli_stale_threshold():
    service = FakeSyncDiagnosticsService()
    sync_diagnostics.run(
        ticker="AAPL",
        stale_threshold_days=7,
        service_factory=lambda: service,
        output=lambda text: None,
    )

    assert service.calls == [("diagnose_ticker", "AAPL", None, None, 7)]


def test_cli_missing_ticker_fails_safely():
    lines, output = collect_output()

    code = sync_diagnostics.run(output=output)

    assert code == 2
    assert "No ticker provided" in lines[0]


def test_cli_invalid_date_fails_safely():
    lines, output = collect_output()

    code = sync_diagnostics.run(
        ticker="AAPL",
        start="2024/01/01",
        output=output,
    )

    assert code == 2
    assert "Invalid start date" in lines[0]


def test_cli_error_status_returns_nonzero():
    service = FakeSyncDiagnosticsService(
        {
            "ticker": "AAPL",
            "row_count": 0,
            "first_date": None,
            "last_date": None,
            "expected_start": None,
            "expected_end": None,
            "missing_days_count": 0,
            "stale_days": 0,
            "status": "Error",
            "warnings": ["Ticker is required."],
        }
    )
    lines, output = collect_output()

    code = sync_diagnostics.run(
        ticker="AAPL",
        service_factory=lambda: service,
        output=output,
    )

    assert code == 1
    assert "Status: Error" in lines[0]
    assert "Ticker is required." in lines[0]


def test_main_parses_arguments(monkeypatch):
    service = FakeSyncDiagnosticsService()
    lines, output = collect_output()

    monkeypatch.setattr(sync_diagnostics, "print", output, raising=False)
    monkeypatch.setattr(
        sync_diagnostics,
        "SyncDiagnosticsService",
        lambda: service,
    )

    code = sync_diagnostics.main(
        [
            "--ticker",
            "AAPL",
            "--start",
            "2024-01-01",
            "--end",
            "2024-12-31",
            "--stale-threshold-days",
            "5",
        ]
    )

    assert code == 0
    assert service.calls == [
        ("diagnose_ticker", "AAPL", "2024-01-01", "2024-12-31", 5)
    ]
