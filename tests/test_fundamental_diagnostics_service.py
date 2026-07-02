from services.fundamental_diagnostics_service import FundamentalDiagnosticsService


class FakeDatabaseManager:
    def __init__(self, rows=None, error=None):
        self.rows = rows or {}
        self.error = error
        self.calls = []

    def get_fundamentals(self, ticker):
        self.calls.append(ticker)

        if self.error is not None:
            raise self.error

        return self.rows.get(ticker)


def full_row(**overrides):
    row = {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "market_cap": 3000000000000,
        "revenue_growth_ttm": 12.5,
        "eps_growth_ttm": 10.2,
        "roe": 24.7,
        "gross_margin": 46.2,
        "free_cash_flow": 95000000000,
        "debt_to_equity": 1.2,
        "current_ratio": 0.92,
        "updated_at": "2026-07-01",
    }
    row.update(overrides)
    return row


def test_current_ticker():
    db = FakeDatabaseManager({"AAPL": full_row()})
    service = FundamentalDiagnosticsService(db)

    result = service.diagnose_ticker(
        " aapl ",
        stale_threshold_days=30,
        today="2026-07-02",
    )

    assert result["ticker"] == "AAPL"
    assert result["status"] == "Current"
    assert result["has_profile"] is True
    assert result["has_fundamentals"] is True
    assert result["company_name"] == "Apple Inc."
    assert result["sector"] == "Technology"
    assert result["industry"] == "Consumer Electronics"
    assert result["market_cap"] == 3000000000000
    assert result["revenue_growth"] == 12.5
    assert result["eps_growth"] == 10.2
    assert result["roe"] == 24.7
    assert result["free_cash_flow"] == 95000000000
    assert result["debt_to_equity"] == 1.2
    assert result["current_ratio"] == 0.92
    assert result["updated_at"] == "2026-07-01"
    assert result["stale_days"] == 1
    assert result["warnings"] == []
    assert db.calls == ["AAPL"]


def test_stale_ticker():
    service = FundamentalDiagnosticsService(
        FakeDatabaseManager({"AAPL": full_row(updated_at="2026-05-01")})
    )

    result = service.diagnose_ticker(
        "AAPL",
        stale_threshold_days=30,
        today="2026-07-02",
    )

    assert result["status"] == "Stale"
    assert result["stale_days"] > 30
    assert result["warnings"]


def test_incomplete_ticker():
    row = full_row(company_name=None, revenue_growth_ttm=None, roe=None)
    service = FundamentalDiagnosticsService(FakeDatabaseManager({"AAPL": row}))

    result = service.diagnose_ticker("AAPL", today="2026-07-02")

    assert result["status"] == "Incomplete"
    assert result["has_profile"] is False
    assert result["has_fundamentals"] is False
    assert "Missing profile fields: company_name" in result["warnings"]
    assert "revenue_growth_ttm" in result["warnings"][1]
    assert "roe" in result["warnings"][1]


def test_missing_ticker():
    service = FundamentalDiagnosticsService(FakeDatabaseManager())

    result = service.diagnose_ticker("AAPL")

    assert result["status"] == "Missing"
    assert result["has_profile"] is False
    assert result["has_fundamentals"] is False
    assert "No local fundamental row found." in result["warnings"]


def test_invalid_ticker():
    service = FundamentalDiagnosticsService(FakeDatabaseManager())

    result = service.diagnose_ticker(" ")

    assert result["status"] == "Error"
    assert "Ticker is required." in result["warnings"]


def test_invalid_threshold():
    service = FundamentalDiagnosticsService(FakeDatabaseManager())

    result = service.diagnose_ticker("AAPL", stale_threshold_days=-1)

    assert result["status"] == "Error"
    assert "Stale threshold days must be zero or greater." in result["warnings"]


def test_multiple_tickers():
    service = FundamentalDiagnosticsService(
        FakeDatabaseManager(
            {
                "AAPL": full_row(),
                "MSFT": full_row(ticker="MSFT", company_name=None),
            }
        )
    )

    result = service.diagnose_tickers(["AAPL", "MSFT"], today="2026-07-02")

    assert result["ticker"] == "MULTIPLE"
    assert result["status"] == "Incomplete"
    assert len(result["results"]) == 2
    assert result["has_profile"] is False
    assert result["has_fundamentals"] is True
    assert result["warnings"]


def test_stale_threshold_controls_status():
    service = FundamentalDiagnosticsService(
        FakeDatabaseManager({"AAPL": full_row(updated_at="2026-06-20")})
    )

    current = service.diagnose_ticker(
        "AAPL",
        stale_threshold_days=30,
        today="2026-07-02",
    )
    stale = service.diagnose_ticker(
        "AAPL",
        stale_threshold_days=3,
        today="2026-07-02",
    )

    assert current["status"] == "Current"
    assert stale["status"] == "Stale"


def test_alias_growth_fields_are_supported():
    row = full_row(
        revenue_growth_ttm=None,
        eps_growth_ttm=None,
        revenue_growth=8.5,
        eps_growth=7.5,
    )
    service = FundamentalDiagnosticsService(FakeDatabaseManager({"AAPL": row}))

    result = service.diagnose_ticker("AAPL", today="2026-07-02")

    assert result["status"] == "Current"
    assert result["revenue_growth"] == 8.5
    assert result["eps_growth"] == 7.5


def test_database_error_returns_error_status():
    service = FundamentalDiagnosticsService(
        FakeDatabaseManager(error=RuntimeError("read failed"))
    )

    result = service.diagnose_ticker("AAPL")

    assert result["status"] == "Error"
    assert "Fundamentals read failed" in result["warnings"][0]
