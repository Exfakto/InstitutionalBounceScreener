from __future__ import annotations

from copy import deepcopy

from market_data.provider import MarketDataProvider


class MockMarketDataProvider(MarketDataProvider):
    """
    Deterministic market data provider for tests and local development.
    """

    LAST_UPDATED = "2026-07-03T00:00:00"

    UNIVERSE = [
        {
            "ticker": "AAPL",
            "company_name": "Apple Inc.",
            "exchange": "NASDAQ",
            "security_type": "Common Stock",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "market_cap": 3000000000000,
            "price": 200.0,
            "average_volume": 55000000,
            "average_dollar_volume": 11000000000,
            "is_active": True,
            "last_updated": LAST_UPDATED,
        },
        {
            "ticker": "MSFT",
            "company_name": "Microsoft Corporation",
            "exchange": "NASDAQ",
            "security_type": "Common Stock",
            "sector": "Technology",
            "industry": "Software Infrastructure",
            "market_cap": 3200000000000,
            "price": 450.0,
            "average_volume": 22000000,
            "average_dollar_volume": 9900000000,
            "is_active": True,
            "last_updated": LAST_UPDATED,
        },
        {
            "ticker": "JPM",
            "company_name": "JPMorgan Chase & Co.",
            "exchange": "NYSE",
            "security_type": "Common Stock",
            "sector": "Financial Services",
            "industry": "Banks Diversified",
            "market_cap": 600000000000,
            "price": 210.0,
            "average_volume": 9000000,
            "average_dollar_volume": 1890000000,
            "is_active": True,
            "last_updated": LAST_UPDATED,
        },
    ]

    def __init__(self, universe=None):
        self.universe = deepcopy(universe if universe is not None else self.UNIVERSE)

    def get_market_universe(self):
        return deepcopy(self.universe)

    def get_company_profile(self, ticker):
        record = self.record_for_ticker(ticker)
        if record is None:
            return None
        return {
            "ticker": record["ticker"],
            "company_name": record["company_name"],
            "exchange": record["exchange"],
            "sector": record["sector"],
            "industry": record["industry"],
        }

    def get_quote(self, ticker):
        record = self.record_for_ticker(ticker)
        if record is None:
            return None
        return {
            "ticker": record["ticker"],
            "price": record["price"],
            "average_volume": record["average_volume"],
            "average_dollar_volume": record["average_dollar_volume"],
            "last_updated": record["last_updated"],
        }

    def get_bulk_quotes(self, tickers):
        quotes = {}
        for ticker in tickers or []:
            quote = self.get_quote(ticker)
            if quote is not None:
                quotes[quote["ticker"]] = quote
        return quotes

    def get_fundamentals(self, ticker):
        record = self.record_for_ticker(ticker)
        if record is None:
            return None
        return {
            "ticker": record["ticker"],
            "market_cap": record["market_cap"],
            "sector": record["sector"],
            "industry": record["industry"],
        }

    def get_last_updated(self):
        return self.LAST_UPDATED

    def record_for_ticker(self, ticker):
        normalized = str(ticker or "").strip().upper()
        for record in self.universe:
            if str(record.get("ticker") or "").upper() == normalized:
                return deepcopy(record)
        return None
