from controllers.market_data_controller import MarketDataController
from services.live_provider_resilience_service import ProviderHealthResult


class ResilienceService:
    def __init__(self, health):
        self.health = health

    def all_health(self):
        return list(self.health)


class MarketDataService:
    def __init__(self):
        self.calls = []

    def fetch_daily_ohlcv(self, ticker, start_date=None, end_date=None, use_cache=True):
        self.calls.append(("ohlcv", ticker, start_date, end_date, use_cache))
        return "ohlcv"

    def fetch_fundamentals(self, ticker):
        self.calls.append(("fundamentals", ticker))
        return "fundamentals"

    def fetch_universe_symbols(self, exchange=None):
        self.calls.append(("universe", exchange))
        return "universe"


def health(name, status):
    return ProviderHealthResult(provider_name=name, status=status)


def test_market_data_controller_provider_health_dashboard_selects_active_and_failover():
    controller = MarketDataController(
        market_data_service=MarketDataService(),
        resilience_service=ResilienceService(
            [
                health("polygon", "degraded"),
                health("fmp", "healthy"),
                health("alpaca", "unavailable"),
            ]
        ),
    )

    dashboard = controller.provider_health_dashboard()

    assert dashboard["active_provider"] == "fmp"
    assert dashboard["failover_provider"] == "polygon"
    assert len(dashboard["providers"]) == 3


def test_market_data_controller_provider_health_empty_without_resilience():
    controller = MarketDataController(market_data_service=MarketDataService())

    assert controller.provider_health() == []
    assert controller.provider_health_dashboard()["providers"] == []


def test_market_data_controller_market_data_delegation():
    service = MarketDataService()
    controller = MarketDataController(market_data_service=service)

    assert controller.fetch_daily_ohlcv("AAPL", "2026-01-01", "2026-01-31", use_cache=False) == "ohlcv"
    assert controller.fetch_fundamentals("AAPL") == "fundamentals"
    assert controller.fetch_universe_symbols(exchange="NYSE") == "universe"
    assert service.calls == [
        ("ohlcv", "AAPL", "2026-01-01", "2026-01-31", False),
        ("fundamentals", "AAPL"),
        ("universe", "NYSE"),
    ]
