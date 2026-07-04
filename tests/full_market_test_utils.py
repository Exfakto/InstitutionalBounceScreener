import sqlite3
from types import SimpleNamespace

from database.manager import DatabaseManager


def build_manager():
    manager = DatabaseManager.__new__(DatabaseManager)
    manager.connection = sqlite3.connect(":memory:")
    manager.connection.row_factory = sqlite3.Row
    manager.cursor = manager.connection.cursor()
    manager.initialize()
    return manager


class FakeProvider:
    def __init__(self, fail_universe_exchange=None):
        self.fail_universe_exchange = fail_universe_exchange
        self.universe_calls = []
        self.fundamental_calls = []
        self.institutional_calls = []

    def fetch_universe_symbols(self, exchange=None):
        self.universe_calls.append(exchange)
        if exchange == self.fail_universe_exchange:
            raise RuntimeError("universe unavailable")
        return [
            {"ticker": "aapl", "company_name": "Apple Inc.", "exchange": exchange, "security_type": "Common Stock", "market_cap": 1_000_000},
            {"ticker": "spy", "company_name": "SPDR ETF", "exchange": exchange, "security_type": "ETF"},
            {"ticker": "abcw", "company_name": "ABC Warrant", "exchange": exchange, "security_type": "Warrant"},
            {"ticker": "old", "company_name": "Inactive", "exchange": exchange, "security_type": "Common Stock", "active": "0"},
        ]

    def fetch_fundamentals(self, ticker):
        self.fundamental_calls.append(ticker)
        if ticker == "FAIL":
            raise RuntimeError("fundamentals unavailable")
        return {
            "ticker": ticker,
            "company_name": f"{ticker} Corp",
            "revenue_growth_ttm": 0.12,
            "eps_growth_ttm": 0.2,
            "roe": 0.3,
            "gross_margin": 0.4,
            "free_cash_flow": 1000,
            "debt_to_equity": 0.5,
            "current_ratio": 1.6,
            "bankruptcy_risk": 0.1,
            "going_concern_warning": 0,
            "last_earnings_date": "2026-01-01",
        }

    def fetch_institutional_data(self, ticker):
        self.institutional_calls.append(ticker)
        if ticker == "FAIL":
            raise RuntimeError("institutional unavailable")
        return {
            "institutional_ownership_pct": 70,
            "institutional_ownership_change_qoq": 2,
            "net_institutional_buying": 1_000_000,
            "insider_buying_flag": 1,
            "insider_selling_flag": 0,
        }


class FakeProviderFactory:
    def __init__(self, provider=None, success=True):
        self.provider = provider or FakeProvider()
        self.success = success

    def create(self):
        if not self.success:
            return SimpleNamespace(
                success=False,
                provider=None,
                provider_name="fake",
                warnings=["missing config"],
                errors=["provider unavailable"],
            )
        return SimpleNamespace(
            success=True,
            provider=self.provider,
            provider_name="fake",
            warnings=[],
            errors=[],
        )
