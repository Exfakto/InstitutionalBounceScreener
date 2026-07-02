from tools import historical_sync


class FakeHistoricalSyncService:
    def __init__(self, summary=None):
        self.summary = summary or {
            "ticker": "AAPL",
            "processed": 1,
            "inserted": 1,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "warnings": [],
        }
        self.calls = []

    def sync_ticker(
        self,
        ticker,
        start=None,
        end=None,
        force_update=False,
        lookback_days=None,
    ):
        self.calls.append(
            ("sync_ticker", ticker, start, end, force_update, lookback_days)
        )
        return self.summary

    def sync_tickers(
        self,
        tickers,
        start=None,
        end=None,
        force_update=False,
        lookback_days=None,
    ):
        self.calls.append(
            ("sync_tickers", tickers, start, end, force_update, lookback_days)
        )
        return self.summary


def collect_output():
    lines = []
    return lines, lines.append


def test_single_ticker_dry_run():
    lines, output = collect_output()

    code = historical_sync.run(
        ticker="aapl",
        start="2024-01-01",
        end="2024-12-31",
        dry_run=True,
        output=output,
    )

    assert code == 0
    assert "Historical Sync Dry Run" in lines[0]
    assert "Provider: configured default" in lines[0]
    assert "Ticker count: 1" in lines[0]
    assert "Tickers: AAPL" in lines[0]
    assert "Date range: 2024-01-01 to 2024-12-31" in lines[0]
    assert "Provider calls: no" in lines[0]
    assert "Database writes: no" in lines[0]


def test_multiple_tickers_dry_run():
    lines, output = collect_output()

    code = historical_sync.run(
        tickers="aapl, msft,nvda",
        dry_run=True,
        output=output,
    )

    assert code == 0
    assert "Tickers: AAPL, MSFT, NVDA" in lines[0]


def test_live_mocked_sync_single_ticker():
    service = FakeHistoricalSyncService()
    lines, output = collect_output()

    code = historical_sync.run(
        ticker="aapl",
        start="2024-01-01",
        end="2024-12-31",
        service_factory=lambda: service,
        output=output,
    )

    assert code == 0
    assert service.calls == [
        ("sync_ticker", "AAPL", "2024-01-01", "2024-12-31", False, None)
    ]
    assert "Provider: configured default" in lines[0]
    assert "Ticker count: 1" in lines[0]
    assert "Date range: 2024-01-01 to 2024-12-31" in lines[0]
    assert "Processed: 1" in lines[0]
    assert "Inserted: 1" in lines[0]
    assert "Warning count: 0" in lines[0]


def test_missing_ticker_fails_safely():
    lines, output = collect_output()

    code = historical_sync.run(output=output)

    assert code == 2
    assert "No ticker provided" in lines[0]


def test_invalid_date_fails_safely():
    lines, output = collect_output()

    code = historical_sync.run(
        ticker="AAPL",
        start="2024/01/01",
        output=output,
    )

    assert code == 2
    assert "Invalid start date" in lines[0]


def test_provider_argument_dry_run():
    lines, output = collect_output()

    code = historical_sync.run(
        ticker="AAPL",
        provider="polygon",
        dry_run=True,
        output=output,
    )

    assert code == 0
    assert "Provider: polygon" in lines[0]


def test_invalid_provider_fails_safely():
    lines, output = collect_output()

    code = historical_sync.run(
        ticker="AAPL",
        provider="unknown",
        dry_run=True,
        output=output,
    )

    assert code == 2
    assert lines == ["Invalid provider: unknown"]


def test_limit_argument_applies_to_tickers():
    lines, output = collect_output()

    code = historical_sync.run(
        tickers="AAPL,MSFT,NVDA",
        limit=2,
        dry_run=True,
        output=output,
    )

    assert code == 0
    assert "Tickers: AAPL, MSFT" in lines[0]
    assert "NVDA" not in lines[0]


def test_lookback_days_calculates_start_date():
    service = FakeHistoricalSyncService()
    lines, output = collect_output()

    code = historical_sync.run(
        ticker="AAPL",
        end="2024-12-31",
        lookback_days=30,
        service_factory=lambda: service,
        output=output,
    )

    assert code == 0
    assert service.calls == [
        ("sync_ticker", "AAPL", "2024-12-01", "2024-12-31", False, 30)
    ]
    assert "Date range: 2024-12-01 to 2024-12-31" in lines[0]


def test_force_update_is_passed_to_service():
    service = FakeHistoricalSyncService()

    code = historical_sync.run(
        ticker="AAPL",
        force_update=True,
        service_factory=lambda: service,
        output=lambda text: None,
    )

    assert code == 0
    assert service.calls == [("sync_ticker", "AAPL", None, None, True, None)]


def test_summary_only_hides_warning_details():
    service = FakeHistoricalSyncService(
        {
            "ticker": "AAPL",
            "processed": 0,
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 1,
            "warnings": ["provider failed"],
        }
    )
    lines, output = collect_output()

    code = historical_sync.run(
        ticker="AAPL",
        summary_only=True,
        service_factory=lambda: service,
        output=output,
    )

    assert code == 1
    assert "Warning count: 1" in lines[0]
    assert "provider failed" not in lines[0]


def test_missing_polygon_key_fails_safely(monkeypatch):
    monkeypatch.delenv("POLYGON_API_KEY", raising=False)
    lines, output = collect_output()

    code = historical_sync.run(
        ticker="AAPL",
        provider="polygon",
        output=output,
    )

    assert code == 1
    assert lines == ["Polygon API key is not configured."]


def test_safe_output_no_secrets(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "very-secret")
    service = FakeHistoricalSyncService(
        {
            "ticker": "AAPL",
            "processed": 0,
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 1,
            "warnings": ["failure with very-secret"],
        }
    )
    lines, output = collect_output()

    code = historical_sync.run(
        ticker="AAPL",
        service_factory=lambda: service,
        output=output,
    )

    assert code == 1
    assert "very-secret" not in "\n".join(lines)
    assert "[redacted]" in lines[0]


def test_main_parses_arguments(monkeypatch):
    service = FakeHistoricalSyncService()
    lines, output = collect_output()

    monkeypatch.setenv("POLYGON_API_KEY", "configured")
    monkeypatch.setattr(historical_sync, "print", output, raising=False)
    monkeypatch.setattr(
        historical_sync,
        "build_historical_sync_service",
        lambda provider=None: service,
    )

    code = historical_sync.main(
        [
            "--ticker",
            "AAPL",
            "--start",
            "2024-01-01",
            "--end",
            "2024-12-31",
            "--provider",
            "polygon",
        ]
    )

    assert code == 0
    assert service.calls == [
        ("sync_ticker", "AAPL", "2024-01-01", "2024-12-31", False, None)
    ]
