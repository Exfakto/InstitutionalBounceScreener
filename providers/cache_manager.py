from __future__ import annotations

from dataclasses import dataclass
from time import time
from typing import Any, Callable


@dataclass(frozen=True)
class CacheEntry:
    """Single in-memory cache entry with an absolute insertion timestamp."""

    data: object
    timestamp: float
    ttl_seconds: int


class CacheManager:
    """
    In-memory provider response cache.

    Cache keys are normalized by provider, endpoint, ticker, and request
    parameters so provider responses remain isolated from one another.
    """

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self.clock = clock or time
        self._entries = {}

    def get(
        self,
        provider: str,
        endpoint: str,
        ticker: str | None = None,
        parameters: dict | None = None,
    ) -> object | None:
        key = self.make_key(provider, endpoint, ticker, parameters)
        entry = self._entries.get(key)

        if entry is None:
            return None

        if self.is_expired(entry):
            self._entries.pop(key, None)
            return None

        return entry.data

    def put(
        self,
        provider: str,
        endpoint: str,
        ticker: str | None = None,
        parameters: dict | None = None,
        data: object = None,
        ttl_seconds: int = 0,
    ) -> object:
        key = self.make_key(provider, endpoint, ticker, parameters)
        self._entries[key] = CacheEntry(
            data=data,
            timestamp=float(self.clock()),
            ttl_seconds=int(ttl_seconds),
        )
        return data

    def invalidate(
        self,
        provider: str,
        endpoint: str | None = None,
        ticker: str | None = None,
        parameters: dict | None = None,
    ) -> bool:
        if endpoint is not None:
            key = self.make_key(provider, endpoint, ticker, parameters)
            return self._entries.pop(key, None) is not None

        removed = False
        normalized_provider = self.normalize(provider)

        for key in list(self._entries):
            if key[0] == normalized_provider:
                self._entries.pop(key, None)
                removed = True

        return removed

    def invalidate_provider(self, provider: str) -> bool:
        return self.invalidate(provider)

    def clear(self) -> None:
        self._entries.clear()

    def is_expired(self, entry: CacheEntry) -> bool:
        if entry.ttl_seconds <= 0:
            return True

        return (float(self.clock()) - entry.timestamp) >= entry.ttl_seconds

    @classmethod
    def make_key(
        cls,
        provider: str,
        endpoint: str,
        ticker: str | None = None,
        parameters: dict | None = None,
    ) -> tuple:
        return (
            cls.normalize(provider),
            cls.normalize(endpoint),
            cls.normalize(ticker),
            cls.normalize_parameters(parameters),
        )

    @classmethod
    def normalize_parameters(cls, parameters: dict | None) -> tuple:
        if not parameters:
            return ()

        return tuple(
            sorted(
                (str(key), cls.normalize_parameter_value(value))
                for key, value in parameters.items()
                if value is not None
            )
        )

    @staticmethod
    def normalize_parameter_value(value: Any) -> object:
        if isinstance(value, (list, tuple)):
            return tuple(str(item) for item in value)

        return str(value)

    @staticmethod
    def normalize(value: object) -> str | None:
        if value is None:
            return None

        return str(value).strip().lower()
