from __future__ import annotations

from providers.provider_manager import ProviderManager
from providers.provider_result import ProviderResult


class LiveDataService:
    """
    Thin service for retrieving live/provider-backed data.
    """

    def __init__(self, provider_manager=None):
        self.provider_manager = provider_manager or ProviderManager()

    def get_price_history(self, ticker, start=None, end=None):
        normalized_ticker = self.normalize_ticker(ticker)

        if normalized_ticker is None:
            return self.missing_ticker_result()

        return self.provider_manager.get_price_history(
            normalized_ticker,
            start=start,
            end=end,
        )

    def get_company_profile(self, ticker):
        return self.get_provider_data("get_company_profile", ticker)

    def get_fundamentals(self, ticker):
        return self.get_provider_data("get_fundamentals", ticker)

    def get_earnings(self, ticker):
        return self.get_provider_data("get_earnings", ticker)

    def get_institutional_metrics(self, ticker):
        return self.get_provider_data("get_institutional_metrics", ticker)

    def get_provider_data(self, method_name, ticker):
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
    def normalize_ticker(ticker):
        if ticker is None:
            return None

        normalized = str(ticker).strip().upper()

        if not normalized:
            return None

        return normalized

    @staticmethod
    def missing_ticker_result():
        return ProviderResult.fail(
            "Ticker is required.",
            source="live_data_service",
            warnings=["Missing ticker."],
        )
