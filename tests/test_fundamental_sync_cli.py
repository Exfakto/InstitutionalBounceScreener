from tools import fundamental_sync


class FakeFundamentalSyncService:
    def __init__(self, summary=None):
        self.summary = summary or {
            "ticker": "AAPL",
            "provider": "fmp",
            "processed": 1,
            "inserted": 1,
            "updated": 0,
            "skipped": 0,
            "failed": 0,
            "warnings": [],
        }
        self.calls = []

    def sync_ticker(self, ticker):
        self.calls.append(("sync_ticker", ticker))
        return self.summary

    def sync_tickers(self, tickers):
        self.calls.append(("sync_tickers", tickers))
        return self.summary


def collect_output():
    lines = []
    return lines, lines.append


def test_single_ticker_dry_run():
    lines, output = collect_output()

    code = fundamental_sync.run(
        ticker="aapl",
        dry_run=True,
        output=output,
    )

    assert code == 0
    assert "Fundamental Sync Dry Run" in lines[0]
    assert "Provider: configured default" in lines[0]
    assert "Ticker count: 1" in lines[0]
    assert "Tickers: AAPL" in lines[0]
    assert "Provider calls: no" in lines[0]
    assert "Database writes: no" in lines[0]


def test_multiple_tickers_dry_run():
    lines, output = collect_output()

    code = fundamental_sync.run(
        tickers="aapl, msft,nvda",
        dry_run=True,
        output=output,
    )

    assert code == 0
    assert "Ticker count: 3" in lines[0]
    assert "Tickers: AAPL, MSFT, NVDA" in lines[0]


def test_live_mocked_sync_single_ticker():
    service = FakeFundamentalSyncService()
    lines, output = collect_output()

    code = fundamental_sync.run(
        ticker="aapl",
        service_factory=lambda: service,
        output=output,
    )

    assert code == 0
    assert service.calls == [("sync_ticker", "AAPL")]
    assert "Fundamental Sync Summary" in lines[0]
    assert "Provider: fmp" in lines[0]
    assert "Ticker count: 1" in lines[0]
    assert "Processed: 1" in lines[0]
    assert "Inserted: 1" in lines[0]
    assert "Updated: 0" in lines[0]
    assert "Skipped: 0" in lines[0]
    assert "Failed: 0" in lines[0]
    assert "Warning count: 0" in lines[0]


def test_live_mocked_sync_multiple_tickers():
    service = FakeFundamentalSyncService(
        {
            "ticker": "MULTIPLE",
            "provider": "fmp",
            "processed": 3,
            "inserted": 2,
            "updated": 1,
            "skipped": 0,
            "failed": 0,
            "warnings": [],
        }
    )
    lines, output = collect_output()

    code = fundamental_sync.run(
        tickers="AAPL,MSFT,NVDA",
        service_factory=lambda: service,
        output=output,
    )

    assert code == 0
    assert service.calls == [("sync_tickers", ["AAPL", "MSFT", "NVDA"])]
    assert "Ticker count: 3" in lines[0]
    assert "Processed: 3" in lines[0]
    assert "Inserted: 2" in lines[0]
    assert "Updated: 1" in lines[0]


def test_missing_ticker_fails_safely():
    lines, output = collect_output()

    code = fundamental_sync.run(output=output)

    assert code == 2
    assert "No ticker provided" in lines[0]


def test_provider_argument_dry_run():
    lines, output = collect_output()

    code = fundamental_sync.run(
        ticker="AAPL",
        provider="fmp",
        dry_run=True,
        output=output,
    )

    assert code == 0
    assert "Provider: fmp" in lines[0]


def test_invalid_provider_fails_safely():
    lines, output = collect_output()

    code = fundamental_sync.run(
        ticker="AAPL",
        provider="unknown",
        dry_run=True,
        output=output,
    )

    assert code == 2
    assert lines == ["Invalid provider: unknown"]


def test_limit_argument_applies_to_tickers():
    lines, output = collect_output()

    code = fundamental_sync.run(
        tickers="AAPL,MSFT,NVDA",
        limit=2,
        dry_run=True,
        output=output,
    )

    assert code == 0
    assert "Tickers: AAPL, MSFT" in lines[0]
    assert "NVDA" not in lines[0]


def test_limit_must_be_positive():
    lines, output = collect_output()

    code = fundamental_sync.run(
        tickers="AAPL,MSFT",
        limit=0,
        dry_run=True,
        output=output,
    )

    assert code == 2
    assert lines == ["Limit must be greater than zero."]


def test_summary_only_hides_warning_details():
    service = FakeFundamentalSyncService(
        {
            "ticker": "AAPL",
            "provider": "fmp",
            "processed": 0,
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 1,
            "warnings": ["provider failed"],
        }
    )
    lines, output = collect_output()

    code = fundamental_sync.run(
        ticker="AAPL",
        summary_only=True,
        service_factory=lambda: service,
        output=output,
    )

    assert code == 1
    assert "Warning count: 1" in lines[0]
    assert "provider failed" not in lines[0]


def test_missing_fmp_key_fails_safely(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    lines, output = collect_output()

    code = fundamental_sync.run(
        ticker="AAPL",
        provider="fmp",
        output=output,
    )

    assert code == 1
    assert lines == ["FMP API key is not configured."]


def test_safe_output_no_secrets(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "very-secret")
    service = FakeFundamentalSyncService(
        {
            "ticker": "AAPL",
            "provider": "fmp",
            "processed": 0,
            "inserted": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 1,
            "warnings": ["failure with very-secret"],
        }
    )
    lines, output = collect_output()

    code = fundamental_sync.run(
        ticker="AAPL",
        service_factory=lambda: service,
        output=output,
    )

    assert code == 1
    assert "very-secret" not in "\n".join(lines)
    assert "[redacted]" in lines[0]


def test_main_parses_arguments(monkeypatch):
    service = FakeFundamentalSyncService()
    lines, output = collect_output()

    monkeypatch.setenv("FMP_API_KEY", "configured")
    monkeypatch.setattr(fundamental_sync, "print", output, raising=False)
    monkeypatch.setattr(
        fundamental_sync,
        "build_fundamental_sync_service",
        lambda provider=None: service,
    )

    code = fundamental_sync.main(
        [
            "--ticker",
            "AAPL",
            "--provider",
            "fmp",
        ]
    )

    assert code == 0
    assert service.calls == [("sync_ticker", "AAPL")]
