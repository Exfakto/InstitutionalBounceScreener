from services.provider_failover_event_service import ProviderFailoverEventService


class FakeLogger:
    def __init__(self):
        self.messages = []

    def warning(self, message, *args):
        self.messages.append((message, args))


def test_provider_failover_event_creation_and_logging():
    logger = FakeLogger()
    service = ProviderFailoverEventService(logger=logger)

    event = service.record_failover(
        previous_provider="polygon",
        new_provider="fmp",
        reason="timeout",
        error_count=2,
        latency_seconds=1.2345678,
        timestamp="2026-01-01T00:00:00Z",
    )

    assert event.previous_provider == "polygon"
    assert event.new_provider == "fmp"
    assert event.timestamp == "2026-01-01T00:00:00Z"
    assert event.reason == "timeout"
    assert event.error_count == 2
    assert event.latency_seconds == 1.234568
    assert logger.messages
    assert "Provider failover" in logger.messages[0][0]


def test_provider_failover_event_retrieval_recent_first():
    service = ProviderFailoverEventService(logger=FakeLogger())
    service.record_failover("a", "b", "first", timestamp="1")
    service.record_failover("b", "c", "second", timestamp="2")

    events = service.recent_events(limit=2)

    assert [event.reason for event in events] == ["second", "first"]


def test_provider_failover_event_retention_limit():
    service = ProviderFailoverEventService(logger=FakeLogger(), max_events=1)
    service.record_failover("a", "b", "first", timestamp="1")
    service.record_failover("b", "c", "second", timestamp="2")

    assert [event.reason for event in service.recent_events(limit=10)] == ["second"]


def test_provider_failover_event_zero_limit_returns_empty():
    service = ProviderFailoverEventService(logger=FakeLogger())
    service.record_failover("a", "b", "first")

    assert service.recent_events(limit=0) == []
