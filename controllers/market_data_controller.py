from __future__ import annotations

from services.live_provider_resilience_service import LiveProviderResilienceService
from services.market_data_service import MarketDataService


class MarketDataController:
    def __init__(self, market_data_service=None, resilience_service=None, providers=None):
        self.resilience_service = resilience_service or (
            LiveProviderResilienceService(providers=providers) if providers else None
        )
        self.market_data_service = market_data_service or MarketDataService(
            providers=providers,
            resilience_service=self.resilience_service,
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
