from __future__ import annotations

from abc import ABC, abstractmethod


class BaseProvider(ABC):
    """
    Abstract interface for local and future external data providers.
    """

    @abstractmethod
    def get_price_history(self, ticker, start=None, end=None):
        raise NotImplementedError

    @abstractmethod
    def get_fundamentals(self, ticker):
        raise NotImplementedError

    @abstractmethod
    def get_earnings(self, ticker):
        raise NotImplementedError

    @abstractmethod
    def get_institutional_metrics(self, ticker):
        raise NotImplementedError

    @abstractmethod
    def get_insider_activity(self, ticker):
        raise NotImplementedError

    @abstractmethod
    def get_company_profile(self, ticker):
        raise NotImplementedError
