from __future__ import annotations

from services.live_provider_resilience_service import LiveProviderResilienceService
from services.market_data_service import MarketDataService
from services.provider_configuration_validation_service import (
    ProviderConfigurationValidationService,
)


class MarketDataController:
    def __init__(
        self,
        market_data_service=None,
        resilience_service=None,
        providers=None,
        settings_service=None,
        provider_configuration_validation_service=None,
    ):
        self.resilience_service = resilience_service or (
            LiveProviderResilienceService(providers=providers) if providers else None
        )
        self.market_data_service = market_data_service or MarketDataService(
            providers=providers,
            resilience_service=self.resilience_service,
        )
        self.settings_service = settings_service
        self.provider_configuration_validation_service = (
            provider_configuration_validation_service
            or ProviderConfigurationValidationService(
                settings_service=settings_service,
                resilience_service=self.resilience_service,
            )
        )

    def fetch_daily_ohlcv(self, ticker, start_date=None, end_date=None, use_cache=True):
        return self.market_data_service.fetch_daily_ohlcv(
            ticker,
            start_date=start_date,
            end_date=end_date,
            use_cache=use_cache,
        )

    def fetch_fundamentals(self, ticker):
        return self.market_data_service.fetch_fundamentals(ticker)

    def fetch_universe_symbols(self, exchange=None):
        return self.market_data_service.fetch_universe_symbols(exchange=exchange)

    def provider_health(self):
        if self.resilience_service is None:
            return []
        return self.resilience_service.all_health()

    def provider_failover_history(self, limit=25):
        if self.resilience_service is None:
            return []
        recent_events = getattr(self.resilience_service, "recent_failover_events", None)
        if recent_events is None:
            return []
        return list(recent_events(limit=limit) or [])

    def provider_health_dashboard(self):
        health = list(self.provider_health() or [])
        active = self.active_provider_name(health)
        failover = self.failover_provider_name(health, active)
        return {
            "providers": health,
            "active_provider": active,
            "failover_provider": failover,
            "failover_events": self.provider_failover_history(),
        }

    def validate_provider_configuration(self):
        return self.provider_configuration_validation_service.validate()

    @staticmethod
    def active_provider_name(health):
        for item in health or []:
            if getattr(item, "status", None) == "healthy":
                return getattr(item, "provider_name", None)
        for item in health or []:
            if getattr(item, "status", None) == "degraded":
                return getattr(item, "provider_name", None)
        return None

    @staticmethod
    def failover_provider_name(health, active_provider):
        for item in health or []:
            name = getattr(item, "provider_name", None)
            if name != active_provider and getattr(item, "status", None) in {
                "healthy",
                "degraded",
            }:
                return name
        return None
