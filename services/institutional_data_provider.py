"""
Institutional data provider interfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from database.institutional_data import InstitutionalData


class InstitutionalDataProvider(ABC):
    """
    Abstract source for raw institutional metrics.
    """

    @abstractmethod
    def fetch_for_ticker(self, ticker: str) -> InstitutionalData | None:
        """
        Fetch institutional metrics for a single ticker.
        """

    @abstractmethod
    def fetch_for_tickers(self, tickers) -> dict[str, InstitutionalData]:
        """
        Fetch institutional metrics for multiple tickers.
        """


class LocalInstitutionalDataProvider(InstitutionalDataProvider):
    """
    Institutional data provider backed by the local database repository.
    """

    def __init__(self, repository):
        self.repository = repository

    def fetch_for_ticker(self, ticker: str) -> InstitutionalData | None:
        normalized = self.normalize_ticker(ticker)
        if normalized is None:
            return None

        record = self.repository.get_institutional_data(normalized)
        return record or self.empty_record(normalized)

    def fetch_for_tickers(self, tickers) -> dict[str, InstitutionalData]:
        normalized = [
            value
            for value in (self.normalize_ticker(ticker) for ticker in (tickers or []))
            if value is not None
        ]
        if not normalized:
            return {}

        records = self.repository.get_institutional_data_for_tickers(normalized) or {}
        return {
            ticker: records.get(ticker) or self.empty_record(ticker)
            for ticker in normalized
        }

    @staticmethod
    def normalize_ticker(ticker: str) -> str | None:
        value = str(ticker or "").strip().upper()
        return value or None

    @staticmethod
    def empty_record(ticker: str) -> InstitutionalData:
        return InstitutionalData(
            ticker=ticker,
            insider_buying_flag=None,
            insider_selling_flag=None,
        )
