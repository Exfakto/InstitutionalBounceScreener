from __future__ import annotations

from dataclasses import dataclass, field

from market_data.live_adapters import (
    AlpacaMarketDataProvider,
    FinancialModelingPrepProvider,
    PolygonMarketDataProvider,
)
from market_data.local_csv_provider import LocalCsvMarketDataProvider


@dataclass(frozen=True)
class ProviderFactoryResult:
    success: bool
    provider: object | None = None
    provider_name: str | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class ProviderFactory:
    """
    Build market data providers from AppSettingsService preferences.
    """

    def __init__(self, settings_service=None, http_client=None, local_csv_directory="data/ohlcv"):
        self.settings_service = settings_service
        self.http_client = http_client
        self.local_csv_directory = local_csv_directory

    def create(self):
        preferences = (
            self.settings_service.get_preferences()
            if self.settings_service is not None
            else None
        )
        provider_name = str(
            getattr(preferences, "selected_market_data_provider", "local_csv")
        ).lower()

        if provider_name == "polygon":
            return self.polygon(preferences)
        if provider_name == "fmp":
            return self.fmp(preferences)
        if provider_name == "alpaca":
            return self.alpaca(preferences)
        return self.local_csv(provider_name)

    def polygon(self, preferences):
        api_key = getattr(preferences, "polygon_api_key", "")
        if not api_key:
            return self.missing("polygon", "polygon_api_key")
        return self.success(
            "polygon",
            PolygonMarketDataProvider(
                api_key=api_key,
                http_client=self.http_client,
                timeout=getattr(preferences, "request_timeout_seconds", 10),
                max_retries=getattr(preferences, "max_retries", 2),
                rate_limit_sleep_seconds=getattr(preferences, "rate_limit_sleep_seconds", 1),
            ),
        )

    def fmp(self, preferences):
        api_key = getattr(preferences, "fmp_api_key", "")
        if not api_key:
            return self.missing("fmp", "fmp_api_key")
        return self.success(
            "fmp",
            FinancialModelingPrepProvider(
                api_key=api_key,
                http_client=self.http_client,
                timeout=getattr(preferences, "request_timeout_seconds", 10),
                max_retries=getattr(preferences, "max_retries", 2),
                rate_limit_sleep_seconds=getattr(preferences, "rate_limit_sleep_seconds", 1),
            ),
        )

    def alpaca(self, preferences):
        api_key = getattr(preferences, "alpaca_api_key", "")
        api_secret = getattr(preferences, "alpaca_api_secret", "")
        if not api_key or not api_secret:
            return self.missing("alpaca", "alpaca_api_key/alpaca_api_secret")
        return self.success(
            "alpaca",
            AlpacaMarketDataProvider(
                api_key=api_key,
                api_secret=api_secret,
                http_client=self.http_client,
                timeout=getattr(preferences, "request_timeout_seconds", 10),
                max_retries=getattr(preferences, "max_retries", 2),
                rate_limit_sleep_seconds=getattr(preferences, "rate_limit_sleep_seconds", 1),
            ),
        )

    def local_csv(self, requested_name="local_csv"):
        warnings = []
        if requested_name not in {"local_csv", ""}:
            warnings.append(f"Unknown provider '{requested_name}', using local_csv fallback")
        return ProviderFactoryResult(
            True,
            provider=LocalCsvMarketDataProvider(self.local_csv_directory),
            provider_name="local_csv",
            warnings=warnings,
        )

    @staticmethod
    def success(name, provider):
        return ProviderFactoryResult(True, provider=provider, provider_name=name)

    @staticmethod
    def missing(name, field):
        return ProviderFactoryResult(
            False,
            provider=None,
            provider_name=name,
            errors=[f"Missing credentials for {name}: {field}"],
        )
