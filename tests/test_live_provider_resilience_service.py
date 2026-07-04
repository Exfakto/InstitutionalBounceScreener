import time

from services.live_provider_resilience_service import LiveProviderResilienceService
from services.provider_failover_event_service import ProviderFailoverEventService


class FakeLogger:
    def __init__(self):
        self.messages = []

    def warning(self, message, *args):
        self.messages.append((message, args))


class FlakyProvider:
    SOURCE = "flaky"

    def __init__(self, failures=1):
        self.failures = failures
        self.calls = 0

    def fetch_daily_ohlcv(self, ticker, start=None, end=None):
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError("temporary provider failure")
        return [{"date": "2026-01-01", "open": 1, "high": 2, "low": 1, "close": 2, "volume": 100}]


class SlowProvider:
    SOURCE = "slow"

    def fetch_daily_ohlcv(self, ticker, start=None, end=None):
        time.sleep(0.05)
        return []


class GoodProvider:
    SOURCE = "good"

    def fetch_daily_ohlcv(self, ticker, start=None, end=None):
        return [{"date": "2026-01-01"}]


def test_live_provider_resilience_retry_success():
    provider = FlakyProvider(failures=1)
    service = LiveProviderResilienceService([provider], max_retries=2, timeout_seconds=1)

    result = service.call("fetch_daily_ohlcv", "AAPL")

    assert result.success is True
    assert result.attempts == 2
    assert provider.calls == 2
    health = service.health_for("flaky")
    assert health.status == "degraded"
    assert health.success_count == 1
    assert health.error_count == 1


def test_live_provider_resilience_retry_exhaustion_unavailable():
    provider = FlakyProvider(failures=5)
    service = LiveProviderResilienceService([provider], max_retries=1, timeout_seconds=1)

    result = service.call("fetch_daily_ohlcv", "AAPL")

    assert result.success is False
    assert result.attempts == 2
    health = service.health_for("flaky")
    assert health.status == "unavailable"
    assert health.error_count == 2
    assert "temporary provider failure" in health.last_failure_reason


def test_live_provider_resilience_timeout_handling():
    service = LiveProviderResilienceService([SlowProvider()], max_retries=0, timeout_seconds=0.001)

    result = service.call("fetch_daily_ohlcv", "AAPL")

    assert result.success is False
    assert result.health.status == "unavailable"
    assert "timed out" in result.errors[0]


def test_live_provider_resilience_failover_behavior():
    bad = FlakyProvider(failures=5)
    good = GoodProvider()
    event_service = ProviderFailoverEventService(logger=FakeLogger())
    service = LiveProviderResilienceService(
        [bad, good],
        max_retries=0,
        timeout_seconds=1,
        failover_event_service=event_service,
    )

    result = service.call("fetch_daily_ohlcv", "AAPL")

    assert result.success is True
    assert result.provider_name == "good"
    assert service.health_for("flaky").status == "unavailable"
    assert service.health_for("good").status == "healthy"
    events = service.recent_failover_events()
    assert len(events) == 1
    assert events[0].previous_provider == "flaky"
    assert events[0].new_provider == "good"
    assert "temporary provider failure" in events[0].reason


def test_live_provider_resilience_degraded_provider_state():
    provider = FlakyProvider(failures=1)
    service = LiveProviderResilienceService([provider], max_retries=2, timeout_seconds=1)

    service.call("fetch_daily_ohlcv", "AAPL")

    health = service.health_for("flaky")
    assert health.status == "degraded"
    assert health.average_latency_seconds >= 0


def test_live_provider_resilience_no_failover_event_when_same_provider_recovers():
    provider = FlakyProvider(failures=1)
    event_service = ProviderFailoverEventService(logger=FakeLogger())
    service = LiveProviderResilienceService(
        [provider],
        max_retries=2,
        timeout_seconds=1,
        failover_event_service=event_service,
    )

    result = service.call("fetch_daily_ohlcv", "AAPL")

    assert result.success is True
    assert service.recent_failover_events() == []
