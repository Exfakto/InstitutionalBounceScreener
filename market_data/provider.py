from __future__ import annotations

from abc import ABC, abstractmethod


class MarketDataProvider(ABC):
    """
    Abstract market data boundary for universe, quote, and fundamentals data.
    """

    @abstractmethod
    def get_market_universe(self):
        raise NotImplementedError

    @abstractmethod
    def get_company_profile(self, ticker):
        raise NotImplementedError

    @abstractmethod
    def get_quote(self, ticker):
        raise NotImplementedError

    @abstractmethod
    def get_bulk_quotes(self, tickers):
        raise NotImplementedError

    @abstractmethod
    def get_fundamentals(self, ticker):
        raise NotImplementedError

    @abstractmethod
    def get_last_updated(self):
        raise NotImplementedError
