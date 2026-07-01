import pandas as pd

from providers.local_provider import LocalProvider


class FakeLocalDatabase:

    def __init__(
        self,
        price_history=None,
        fundamentals=None,
        earnings=None,
        institutional_metrics=None,
        company_profile=None,
    ):
        self.price_history = price_history
        self.fundamentals = fundamentals
        self.earnings = earnings
        self.institutional_metrics = institutional_metrics
        self.company_profile = company_profile
        self.calls = []

    def get_price_history(self, ticker):
        self.calls.append(("get_price_history", ticker))
        if self.price_history is None:
            return pd.DataFrame()
        return self.price_history

    def get_fundamentals(self, ticker):
        self.calls.append(("get_fundamentals", ticker))
        return self.fundamentals

    def get_earnings(self, ticker):
        self.calls.append(("get_earnings", ticker))
        return self.earnings

    def get_institutional_metrics(self, ticker):
        self.calls.append(("get_institutional_metrics", ticker))
        return self.institutional_metrics

    def get_company_profile(self, ticker):
        self.calls.append(("get_company_profile", ticker))
        return self.company_profile

    def download_prices(self, ticker):
        raise AssertionError("LocalProvider attempted a network-style download")

    def fetch(self, *args, **kwargs):
        raise AssertionError("LocalProvider attempted a network-style fetch")


def price_history():
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0],
            "High": [102.0, 103.0, 104.0],
            "Low": [99.0, 100.0, 101.0],
            "Close": [101.0, 102.0, 103.0],
            "Volume": [1000, 1100, 1200],
        },
        index=pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
    )


def test_local_provider_normalizes_ticker_for_price_history():
    db = FakeLocalDatabase(price_history=price_history())
    provider = LocalProvider(database_manager=db)

    result = provider.get_price_history(" aapl ")

    assert result.success is True
    assert result.source == "local"
    assert result.metadata["ticker"] == "AAPL"
    assert result.metadata["rows"] == 3
    assert db.calls == [("get_price_history", "AAPL")]


def test_local_provider_price_history_success_with_date_filter():
    provider = LocalProvider(database_manager=FakeLocalDatabase(price_history=price_history()))

    result = provider.get_price_history("MSFT", start="2026-01-02", end="2026-01-03")

    assert result.success is True
    assert list(result.data["Close"]) == [102.0, 103.0]
    assert result.metadata["rows"] == 2


def test_local_provider_missing_price_history_safe_failure():
    provider = LocalProvider(database_manager=FakeLocalDatabase())

    result = provider.get_price_history("AAPL")

    assert result.success is False
    assert result.data is None
    assert "No local price history found" in result.message
    assert result.metadata["ticker"] == "AAPL"


def test_local_provider_missing_ticker():
    provider = LocalProvider(database_manager=FakeLocalDatabase())

    result = provider.get_price_history(" ")

    assert result.success is False
    assert result.message == "Ticker is required."
    assert "Missing ticker." in result.warnings


def test_local_provider_fundamentals_success():
    db = FakeLocalDatabase(
        fundamentals={
            "ticker": "AAPL",
            "market_cap": 100.0,
            "quality_score": 80.0,
        }
    )
    provider = LocalProvider(database_manager=db)

    result = provider.get_fundamentals("aapl")

    assert result.success is True
    assert result.data["ticker"] == "AAPL"
    assert result.metadata["ticker"] == "AAPL"
    assert db.calls == [("get_fundamentals", "AAPL")]


def test_local_provider_fundamentals_missing_safe_failure():
    provider = LocalProvider(database_manager=FakeLocalDatabase())

    result = provider.get_fundamentals("AAPL")

    assert result.success is False
    assert "No local fundamentals found" in result.message


def test_local_provider_earnings_institutional_and_profile():
    db = FakeLocalDatabase(
        earnings={"ticker": "AAPL", "days_until_earnings": 14},
        institutional_metrics={"ticker": "AAPL", "institutional_score": 75.0},
        company_profile={"ticker": "AAPL", "company": "Apple Inc."},
    )
    provider = LocalProvider(database_manager=db)

    assert provider.get_earnings("aapl").data["days_until_earnings"] == 14
    assert provider.get_institutional_metrics("aapl").data["institutional_score"] == 75.0
    assert provider.get_company_profile("aapl").data["company"] == "Apple Inc."


def test_local_provider_insider_activity_unavailable():
    provider = LocalProvider(database_manager=FakeLocalDatabase())

    result = provider.get_insider_activity("AAPL")

    assert result.success is False
    assert "No local insider activity source" in result.message
    assert "Local insider activity is unavailable." in result.warnings


def test_local_provider_no_network_calls():
    db = FakeLocalDatabase(price_history=price_history())
    provider = LocalProvider(database_manager=db)

    result = provider.get_price_history("AAPL")

    assert result.success is True
    assert ("get_price_history", "AAPL") in db.calls
