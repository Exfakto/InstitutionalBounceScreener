from services.live_provider_resilience_service import LiveProviderResilienceService
from services.market_data_service import MarketDataService


class BadProvider:
    SOURCE = "bad"

    def fetch_daily_ohlcv(self, ticker, start=None, end=None):
        raise RuntimeError("temporary provider failure")

    def fetch_fundamentals(self, ticker):
        raise RuntimeError("fundamental timeout")

    def fetch_universe_symbols(self, exchange=None):
        raise RuntimeError("symbol timeout")


class GoodProvider:
    SOURCE = "good"

    def fetch_daily_ohlcv(self, ticker, start=None, end=None):
        return [
            {
                "date": "2026-01-01",
                "open": 10,
                "high": 11,
                "low": 9,
                "close": 10.5,
                "volume": 1000,
            }
        ]

    def fetch_fundamentals(self, ticker):
        return {"ticker": ticker, "market_cap": 100}

    def fetch_universe_symbols(self, exchange=None):
        return [{"ticker": "AAPL", "exchange": exchange or "NASDAQ"}]


def test_market_data_service_uses_resilience_failover_for_ohlcv():
    resilience = LiveProviderResilienceService(
        [BadProvider(), GoodProvider()],
        max_retries=0,
        timeout_seconds=1,
    )
    service = MarketDataService(
        providers=resilience.providers,
        resilience_service=resilience,
    )

    result = service.fetch_daily_ohlcv("aapl", use_cache=False)

    assert result.success is True
    assert result.rows[0].ticker == "AAPL"
    assert result.rows[0].source == "good"
    assert resilience.health_for("bad").status == "unavailable"
    assert resilience.health_for("good").status == "healthy"


def test_market_data_service_retry_exhaustion_returns_errors():
    resilience = LiveProviderResilienceService(
        [BadProvider()],
        max_retries=1,
        timeout_seconds=1,
    )
    service = MarketDataService(
        providers=resilience.providers,
        resilience_service=resilience,
    )

    result = service.fetch_daily_ohlcv("AAPL", use_cache=False)

    assert result.success is False
    assert result.errors
    assert resilience.health_for("bad").status == "unavailable"


def test_market_data_service_resilience_for_fundamentals_and_universe():
    resilience = LiveProviderResilienceService(
        [BadProvider(), GoodProvider()],
        max_retries=0,
        timeout_seconds=1,
    )
    service = MarketDataService(
        providers=resilience.providers,
        resilience_service=resilience,
    )

    fundamentals = service.fetch_fundamentals("AAPL")
    symbols = service.fetch_universe_symbols(exchange="NYSE")

    assert fundamentals.success is True
    assert fundamentals.data["market_cap"] == 100
    assert symbols.success is True
    assert symbols.symbols[0]["exchange"] == "NYSE"


def test_market_data_controller_provider_health():
    from controllers.market_data_controller import MarketDataController

    resilience = LiveProviderResilienceService([GoodProvider()], max_retries=0)
    controller = MarketDataController(
        providers=resilience.providers,
        resilience_service=resilience,
    )

    controller.fetch_daily_ohlcv("AAPL", use_cache=False)
    health = controller.provider_health()

    assert health[0].provider_name == "good"
    assert health[0].status == "healthy"
