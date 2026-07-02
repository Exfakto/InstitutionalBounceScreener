from tools import fundamental_diagnostics


class FakeFundamentalDiagnosticsService:
    def __init__(self, result=None):
        self.result = result or {
            "ticker": "AAPL",
            "has_profile": True,
            "has_fundamentals": True,
            "company_name": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "market_cap": 3000000000000,
            "revenue_growth": 12.5,
            "eps_growth": 10.2,
            "roe": 24.7,
            "free_cash_flow": 95000000000,
            "debt_to_equity": 1.2,
            "current_ratio": 0.92,
            "updated_at": "2026-07-01",
            "stale_days": 1,
            "status": "Current",
            "warnings": [],
        }
        self.calls = []

    def diagnose_ticker(self, ticker, stale_threshold_days=30):
        self.calls.append(("diagnose_ticker", ticker, stale_threshold_days))
        return self.result

    def diagnose_tickers(self, tickers, stale_threshold_days=30):
        self.calls.append(("diagnose_tickers", tickers, stale_threshold_days))
        return {
            "ticker": "MULTIPLE",
            "results": [self.result],
            "has_profile": self.result["has_profile"],
            "has_fundamentals": self.result["has_fundamentals"],
            "company_name": None,
            "sector": None,
            "industry": None,
            "market_cap": None,
            "revenue_growth": None,
            "eps_growth": None,
            "roe": None,
            "free_cash_flow": None,
            "debt_to_equity": None,
            "current_ratio": None,
            "updated_at": None,
            "stale_days": self.result["stale_days"],
            "status": self.result["status"],
            "warnings": self.result["warnings"],
        }


def collect_output():
    lines = []
    return lines, lines.append


def test_cli_single_ticker_output():
    service = FakeFundamentalDiagnosticsService()
    lines, output = collect_output()

    code = fundamental_diagnostics.run(
        ticker="aapl",
        service_factory=lambda: service,
        output=output,
    )

    assert code == 0
    assert service.calls == [("diagnose_ticker", "AAPL", 30)]
    assert "Ticker: AAPL" in lines[0]
    assert "Status: Current" in lines[0]
    assert "Company name: Apple Inc." in lines[0]
    assert "Sector: Technology" in lines[0]
    assert "Market cap: 3000000000000" in lines[0]
    assert "Updated at: 2026-07-01" in lines[0]
    assert "Stale days: 1" in lines[0]
    assert "Warnings: 0" in lines[0]


def test_cli_multiple_tickers_output():
    service = FakeFundamentalDiagnosticsService()
    lines, output = collect_output()

    code = fundamental_diagnostics.run(
        tickers="aapl,msft,nvda",
        service_factory=lambda: service,
        output=output,
    )

    assert code == 0
    assert service.calls == [
        ("diagnose_tickers", ["AAPL", "MSFT", "NVDA"], 30)
    ]
    assert "Ticker: MULTIPLE" in lines[0]
    assert "Ticker: AAPL" in lines[0]


def test_cli_stale_threshold():
    service = FakeFundamentalDiagnosticsService()
    fundamental_diagnostics.run(
        ticker="AAPL",
        stale_threshold_days=7,
        service_factory=lambda: service,
        output=lambda text: None,
    )

    assert service.calls == [("diagnose_ticker", "AAPL", 7)]


def test_cli_missing_ticker_fails_safely():
    lines, output = collect_output()

    code = fundamental_diagnostics.run(output=output)

    assert code == 2
    assert "No ticker provided" in lines[0]


def test_cli_invalid_threshold_fails_safely():
    lines, output = collect_output()

    code = fundamental_diagnostics.run(
        ticker="AAPL",
        stale_threshold_days=-1,
        output=output,
    )

    assert code == 2
    assert "Stale threshold days must be zero or greater." in lines[0]


def test_cli_error_status_returns_nonzero():
    service = FakeFundamentalDiagnosticsService(
        {
            "ticker": "AAPL",
            "has_profile": False,
            "has_fundamentals": False,
            "company_name": None,
            "sector": None,
            "industry": None,
            "market_cap": None,
            "revenue_growth": None,
            "eps_growth": None,
            "roe": None,
            "free_cash_flow": None,
            "debt_to_equity": None,
            "current_ratio": None,
            "updated_at": None,
            "stale_days": 0,
            "status": "Error",
            "warnings": ["Ticker is required."],
        }
    )
    lines, output = collect_output()

    code = fundamental_diagnostics.run(
        ticker="AAPL",
        service_factory=lambda: service,
        output=output,
    )

    assert code == 1
    assert "Status: Error" in lines[0]
    assert "Ticker is required." in lines[0]


def test_main_parses_arguments(monkeypatch):
    service = FakeFundamentalDiagnosticsService()
    lines, output = collect_output()

    monkeypatch.setattr(fundamental_diagnostics, "print", output, raising=False)
    monkeypatch.setattr(
        fundamental_diagnostics,
        "FundamentalDiagnosticsService",
        lambda: service,
    )

    code = fundamental_diagnostics.main(
        [
            "--ticker",
            "AAPL",
            "--stale-threshold-days",
            "5",
        ]
    )

    assert code == 0
    assert service.calls == [("diagnose_ticker", "AAPL", 5)]
