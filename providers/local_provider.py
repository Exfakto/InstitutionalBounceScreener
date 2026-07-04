from __future__ import annotations

import pandas as pd

from database.manager import DatabaseManager
from providers.base_provider import BaseProvider
from providers.provider_result import ProviderResult


class LocalProvider(BaseProvider):
    """
    Database-backed local provider.

    This provider only reads local repository data through DatabaseManager-style
    methods. It does not perform network calls, writes, analysis calculations,
    service calls, or UI work.
    """

    SOURCE = "local"

    def __init__(self, database_manager=None):
        self.database_manager = database_manager or DatabaseManager()

    def get_price_history(self, ticker, start=None, end=None):
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return self.missing_ticker_result()

        try:
            history = self.database_manager.get_price_history(normalized_ticker)
        except Exception as exc:
            return self.failure(
                f"Local price history unavailable for {normalized_ticker}.",
                normalized_ticker,
                warnings=[str(exc)],
            )

        if history is None or getattr(history, "empty", False):
            return self.failure(
                f"No local price history found for {normalized_ticker}.",
                normalized_ticker,
            )

        filtered = self.filter_price_history(history, start=start, end=end)

        if filtered.empty:
            return self.failure(
                f"No local price history found for {normalized_ticker}.",
                normalized_ticker,
                metadata={"ticker": normalized_ticker},
            )

        return ProviderResult.ok(
            data=filtered,
            message="Local price history retrieved.",
            source=self.SOURCE,
            metadata={"ticker": normalized_ticker, "rows": len(filtered)},
        )

    def get_fundamentals(self, ticker):
        return self.get_row_result(
            ticker,
            "get_fundamentals",
            "Local fundamentals retrieved.",
            "No local fundamentals found",
        )

    def get_earnings(self, ticker):
        return self.get_row_result(
            ticker,
            "get_earnings",
            "Local earnings retrieved.",
            "No local earnings found",
        )

    def get_institutional_metrics(self, ticker):
        return self.get_row_result(
            ticker,
            "get_institutional_metrics",
            "Local institutional metrics retrieved.",
            "No local institutional metrics found",
        )

    def get_insider_activity(self, ticker):
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return self.missing_ticker_result()

        return self.failure(
            f"No local insider activity source is configured for {normalized_ticker}.",
            normalized_ticker,
            warnings=["Local insider activity is unavailable."],
        )

    def get_company_profile(self, ticker):
        return self.get_row_result(
            ticker,
            "get_company_profile",
            "Local company profile retrieved.",
            "No local company profile found",
        )

    def fetch_universe_symbols(self, exchange=None):
        if not hasattr(self.database_manager, "fetch_universe_symbols"):
            return ProviderResult.ok(
                data=[],
                message="No local universe source is configured.",
                source=self.SOURCE,
            )

        try:
            rows = self.database_manager.fetch_universe_symbols(
                exchange=exchange,
                active_only=True,
            )
        except Exception as exc:
            return self.failure(
                "Local universe symbols unavailable.",
                warnings=[str(exc)],
            )

        return ProviderResult.ok(
            data=[self.row_to_dict(row) for row in rows],
            message="Local universe symbols retrieved.",
            source=self.SOURCE,
            metadata={"exchange": exchange, "rows": len(rows)},
        )

    def get_row_result(
        self,
        ticker,
        method_name,
        success_message,
        missing_message,
    ):
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return self.missing_ticker_result()

        method = getattr(self.database_manager, method_name, None)

        if method is None:
            return self.failure(
                f"{missing_message} for {normalized_ticker}.",
                normalized_ticker,
            )

        try:
            row = method(normalized_ticker)
        except Exception as exc:
            return self.failure(
                f"{missing_message} for {normalized_ticker}.",
                normalized_ticker,
                warnings=[str(exc)],
            )

        if row is None:
            return self.failure(
                f"{missing_message} for {normalized_ticker}.",
                normalized_ticker,
            )

        return ProviderResult.ok(
            data=self.row_to_dict(row),
            message=success_message,
            source=self.SOURCE,
            metadata={"ticker": normalized_ticker},
        )

    @classmethod
    def failure(cls, message, ticker=None, warnings=None, metadata=None):
        result_metadata = dict(metadata or {})

        if ticker is not None:
            result_metadata.setdefault("ticker", ticker)

        return ProviderResult.fail(
            message=message,
            source=cls.SOURCE,
            warnings=list(warnings or []),
            metadata=result_metadata,
        )

    @classmethod
    def missing_ticker_result(cls):
        return cls.failure(
            "Ticker is required.",
            warnings=["Missing ticker."],
        )

    @staticmethod
    def normalize_ticker(ticker):
        if ticker is None:
            return None

        normalized = str(ticker).strip().upper()

        if not normalized:
            return None

        return normalized

    @staticmethod
    def row_to_dict(row):
        if isinstance(row, dict):
            return dict(row)

        try:
            return dict(row)
        except (TypeError, ValueError):
            return row

    @staticmethod
    def filter_price_history(history, start=None, end=None):
        filtered = history.copy()

        if start is not None:
            filtered = filtered[filtered.index >= pd.to_datetime(start)]

        if end is not None:
            filtered = filtered[filtered.index <= pd.to_datetime(end)]

        return filtered
