from __future__ import annotations

from dataclasses import dataclass
from time import time


@dataclass(frozen=True)
class CacheEntry:
    data: object
    timestamp: float
    ttl_seconds: int


class CacheManager:
    """
    In-memory provider response cache.
    """

    def __init__(self, clock=None):
        self.clock = clock or time
        self._entries = {}

    def get(self, provider, endpoint, ticker=None, parameters=None):
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
        provider,
        endpoint,
        ticker=None,
        parameters=None,
        data=None,
        ttl_seconds=0,
    ):
        key = self.make_key(provider, endpoint, ticker, parameters)
        self._entries[key] = CacheEntry(
            data=data,
            timestamp=float(self.clock()),
            ttl_seconds=int(ttl_seconds),
        )
        return data

    def invalidate(self, provider, endpoint=None, ticker=None, parameters=None):
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

    def invalidate_provider(self, provider):
        return self.invalidate(provider)

    def clear(self):
        self._entries.clear()

    def is_expired(self, entry):
        if entry.ttl_seconds <= 0:
            return True

        return (float(self.clock()) - entry.timestamp) >= entry.ttl_seconds

    @classmethod
    def make_key(cls, provider, endpoint, ticker=None, parameters=None):
        return (
            cls.normalize(provider),
            cls.normalize(endpoint),
            cls.normalize(ticker),
            cls.normalize_parameters(parameters),
        )

    @classmethod
    def normalize_parameters(cls, parameters):
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
    def normalize_parameter_value(value):
        if isinstance(value, (list, tuple)):
            return tuple(str(item) for item in value)

        return str(value)

    @staticmethod
    def normalize(value):
        if value is None:
            return None

        return str(value).strip().lower()
