from controllers.market_data_controller import MarketDataController
from services.live_provider_resilience_service import LiveProviderResilienceService
from services.provider_failover_event_service import ProviderFailoverEventService


class SettingsService:
    def get_preferences(self):
        return {
            "selected_market_data_provider": "polygon",
            "polygon_api_key": "polygon-key",
            "request_timeout_seconds": 5,
            "max_retries": 0,
            "rate_limit_sleep_seconds": 1,
        }


class FailingProvider:
    SOURCE = "polygon"

    def fetch_fundamentals(self, ticker):
        raise TimeoutError("temporary provider timeout")


class WorkingProvider:
    SOURCE = "fmp"

    def fetch_fundamentals(self, ticker):
        return {"ticker": ticker, "market_cap": 3_000_000_000}


def test_end_to_end_provider_workflow_failover_health_and_validation():
    failover_events = ProviderFailoverEventService(max_events=10)
    resilience = LiveProviderResilienceService(
        providers=[FailingProvider(), WorkingProvider()],
        max_retries=0,
        timeout_seconds=1,
        failover_event_service=failover_events,
    )
    controller = MarketDataController(
        providers=[FailingProvider(), WorkingProvider()],
        resilience_service=resilience,
        settings_service=SettingsService(),
    )

    result = controller.fetch_fundamentals("aapl")
    health_dashboard = controller.provider_health_dashboard()
    validation = controller.validate_provider_configuration()
    history = controller.provider_failover_history()

    assert result.success is True
    assert result.ticker == "AAPL"
    assert result.data["market_cap"] == 3_000_000_000
    assert health_dashboard["active_provider"] == "fmp"
    assert health_dashboard["failover_provider"] is None
    assert validation.status == "Passed"
    assert len(history) == 1
    assert history[0].previous_provider == "polygon"
    assert history[0].new_provider == "fmp"
    assert "timed out" in history[0].reason
