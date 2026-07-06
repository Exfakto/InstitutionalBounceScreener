from __future__ import annotations

from typing import Any

from providers.provider_manager import ProviderManager
from providers.provider_result import ProviderResult


class LiveDataService:
    """
    Retrieve provider-backed data through ProviderManager.

    This service performs input normalization and safe failure handling only.
    It does not calculate analytics, write to SQLite, call controllers, or
    import UI code.
    """

    def __init__(self, provider_manager: ProviderManager | None = None) -> None:
        self.provider_manager = provider_manager or ProviderManager()

    def fetch_daily_ohlcv(
        self,
        ticker: str,
        start: Any = None,
        end: Any = None,
    ) -> ProviderResult:
        """Return provider price history for a normalized ticker."""
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return self.missing_ticker_result()

        return self.provider_manager.get_price_history(
            normalized_ticker,
            start=start,
            end=end,
        )

    def get_price_history(
        self,
        ticker: str,
        start: Any = None,
        end: Any = None,
    ) -> ProviderResult:
        """Compatibility alias for provider-backed OHLCV fetches."""
        return self.fetch_daily_ohlcv(ticker, start=start, end=end)

    def get_company_profile(self, ticker: str) -> ProviderResult:
        """Return provider company profile data."""
        return self.get_provider_data("get_company_profile", ticker)

    def get_fundamentals(self, ticker: str) -> ProviderResult:
        """Return provider fundamental metrics."""
        return self.get_provider_data("get_fundamentals", ticker)

    def get_earnings(self, ticker: str) -> ProviderResult:
        """Return provider earnings data."""
        return self.get_provider_data("get_earnings", ticker)

    def get_institutional_metrics(self, ticker: str) -> ProviderResult:
        """Return provider institutional metrics."""
        return self.get_provider_data("get_institutional_metrics", ticker)

    def get_provider_data(self, method_name: str, ticker: str) -> ProviderResult:
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return self.missing_ticker_result()

        method = getattr(self.provider_manager, method_name, None)

        if method is None:
            return ProviderResult.fail(
                "Provider manager method is unavailable.",
                source="live_data_service",
                warnings=[f"{method_name} is not available."],
            )

        return method(normalized_ticker)

    @staticmethod
    def normalize_ticker(ticker: str | None) -> str | None:
        if ticker is None:
            return None

        normalized = str(ticker).strip().upper()

        if not normalized:
            return None

        return normalized

    @staticmethod
    def missing_ticker_result() -> ProviderResult:
        return ProviderResult.fail(
            "Ticker is required.",
            source="live_data_service",
            warnings=["Missing ticker."],
        )
