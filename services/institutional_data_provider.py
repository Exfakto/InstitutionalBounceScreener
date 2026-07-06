"""
Institutional data provider interfaces.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import logging

from database.institutional_data import InstitutionalData


logger = logging.getLogger(__name__)


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
        self.last_warnings = []

    def fetch_for_ticker(self, ticker: str) -> InstitutionalData | None:
        self.last_warnings = []
        normalized = self.normalize_ticker(ticker)
        if normalized is None:
            return None

        try:
            record = self.repository.get_institutional_data(normalized)
        except Exception as exc:
            self.last_warnings = [self.unavailable_warning(exc)]
            logger.info(self.last_warnings[0])
            return self.empty_record(normalized)
        if record is None:
            self.last_warnings = [self.no_rows_warning()]
        return record or self.empty_record(normalized)

    def fetch_for_tickers(self, tickers) -> dict[str, InstitutionalData]:
        self.last_warnings = []
        normalized = [
            value
            for value in (self.normalize_ticker(ticker) for ticker in (tickers or []))
            if value is not None
        ]
        if not normalized:
            return {}

        try:
            records = self.repository.get_institutional_data_for_tickers(normalized) or {}
        except Exception as exc:
            self.last_warnings = [self.unavailable_warning(exc)]
            logger.info(self.last_warnings[0])
            records = {}
        if not records and not self.last_warnings:
            self.last_warnings = [self.no_rows_warning()]
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

    @staticmethod
    def unavailable_warning(error) -> str:
        return f"Institutional data unavailable; using neutral score ({error})"

    @staticmethod
    def no_rows_warning() -> str:
        return "Institutional data unavailable; using neutral score (no institutional rows found)"


class UnavailableInstitutionalDataProvider(InstitutionalDataProvider):
    """
    Explicit no-data provider used when no institutional source is configured.
    """

    def fetch_for_ticker(self, ticker: str) -> InstitutionalData | None:
        normalized = LocalInstitutionalDataProvider.normalize_ticker(ticker)
        if normalized is None:
            return None
        return LocalInstitutionalDataProvider.empty_record(normalized)

    def fetch_for_tickers(self, tickers) -> dict[str, InstitutionalData]:
        normalized = [
            value
            for value in (
                LocalInstitutionalDataProvider.normalize_ticker(ticker)
                for ticker in (tickers or [])
            )
            if value is not None
        ]
        return {
            ticker: LocalInstitutionalDataProvider.empty_record(ticker)
            for ticker in normalized
        }
