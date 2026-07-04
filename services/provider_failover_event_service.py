from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from logging import Logger

from config.logging_config import provider_failover_logger


@dataclass(frozen=True)
class ProviderFailoverEvent:
    previous_provider: str
    new_provider: str
    timestamp: str
    reason: str
    error_count: int = 0
    latency_seconds: float | None = None


class ProviderFailoverEventService:
    """Record provider failover events for diagnostics and troubleshooting."""

    def __init__(self, logger: Logger | None = None, max_events=100):
        self.logger = logger or provider_failover_logger
        self.max_events = max(1, int(max_events or 100))
        self.events: list[ProviderFailoverEvent] = []

    def record_failover(
        self,
        previous_provider,
        new_provider,
        reason,
        error_count=0,
        latency_seconds=None,
        timestamp=None,
    ):
        event = ProviderFailoverEvent(
            previous_provider=str(previous_provider or "unknown"),
            new_provider=str(new_provider or "unknown"),
            timestamp=timestamp or now_utc(),
            reason=str(reason or "Provider failover"),
            error_count=int(error_count or 0),
            latency_seconds=round(float(latency_seconds), 6)
            if latency_seconds is not None
            else None,
        )
        self.events.append(event)
        self.events = self.events[-self.max_events :]
        self.logger.warning(
            "Provider failover: %s -> %s | reason=%s | errors=%s | latency=%s",
            event.previous_provider,
            event.new_provider,
            event.reason,
            event.error_count,
            event.latency_seconds,
        )
        return event

    def recent_events(self, limit=25):
        safe_limit = max(0, int(limit or 0))
        if safe_limit == 0:
            return []
        return list(reversed(self.events[-safe_limit:]))


def now_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
