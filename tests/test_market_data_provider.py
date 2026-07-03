import pytest

from market_data import MarketDataProvider, MockMarketDataProvider


def test_market_data_provider_cannot_be_instantiated():
    with pytest.raises(TypeError):
        MarketDataProvider()


def test_partial_market_data_provider_cannot_be_instantiated():
    class PartialProvider(MarketDataProvider):
        def get_market_universe(self):
            return []

    with pytest.raises(TypeError):
        PartialProvider()


def test_market_data_provider_base_methods_raise_when_called_by_subclass():
    class DelegatingProvider(MarketDataProvider):
        def get_market_universe(self):
            return super().get_market_universe()

        def get_company_profile(self, ticker):
            return super().get_company_profile(ticker)

        def get_quote(self, ticker):
            return super().get_quote(ticker)

        def get_bulk_quotes(self, tickers):
            return super().get_bulk_quotes(tickers)

        def get_fundamentals(self, ticker):
            return super().get_fundamentals(ticker)

        def get_last_updated(self):
            return super().get_last_updated()

    provider = DelegatingProvider()

    with pytest.raises(NotImplementedError):
        provider.get_market_universe()
    with pytest.raises(NotImplementedError):
        provider.get_company_profile("AAPL")
    with pytest.raises(NotImplementedError):
        provider.get_quote("AAPL")
    with pytest.raises(NotImplementedError):
        provider.get_bulk_quotes(["AAPL"])
    with pytest.raises(NotImplementedError):
        provider.get_fundamentals("AAPL")
    with pytest.raises(NotImplementedError):
        provider.get_last_updated()


def test_mock_market_data_provider_universe_is_deterministic():
    provider = MockMarketDataProvider()

    first = provider.get_market_universe()
    second = provider.get_market_universe()

    assert first == second
    assert [record["ticker"] for record in first] == ["AAPL", "MSFT", "JPM"]
    assert first is not second


def test_mock_market_data_provider_profile_quote_and_fundamentals():
    provider = MockMarketDataProvider()

    profile = provider.get_company_profile("aapl")
    quote = provider.get_quote("AAPL")
    fundamentals = provider.get_fundamentals("AAPL")

    assert profile["company_name"] == "Apple Inc."
    assert profile["exchange"] == "NASDAQ"
    assert quote["price"] == 200.0
    assert quote["average_volume"] == 55000000
    assert fundamentals["market_cap"] == 3000000000000
    assert provider.get_company_profile("UNKNOWN") is None
    assert provider.get_quote("UNKNOWN") is None
    assert provider.get_fundamentals("UNKNOWN") is None


def test_mock_market_data_provider_bulk_quotes_and_last_updated():
    provider = MockMarketDataProvider()

    quotes = provider.get_bulk_quotes(["msft", "missing", "jpm"])

    assert set(quotes) == {"MSFT", "JPM"}
    assert quotes["MSFT"]["price"] == 450.0
    assert provider.get_last_updated() == "2026-07-03T00:00:00"
