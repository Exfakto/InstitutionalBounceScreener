from providers.cache_manager import CacheEntry, CacheManager


class FakeClock:

    def __init__(self, current=0):
        self.current = current

    def __call__(self):
        return self.current

    def advance(self, seconds):
        self.current += seconds


def test_cache_hit():
    clock = FakeClock()
    cache = CacheManager(clock=clock)
    cached_data = {"ticker": "AAPL"}

    cache.put(
        "local",
        "get_price_history",
        ticker="AAPL",
        parameters={"start": "2026-01-01"},
        data=cached_data,
        ttl_seconds=60,
    )

    assert cache.get(
        "local",
        "get_price_history",
        ticker="aapl",
        parameters={"start": "2026-01-01"},
    ) == cached_data


def test_cache_miss():
    cache = CacheManager(clock=FakeClock())

    assert cache.get("local", "get_price_history", ticker="AAPL") is None


def test_cache_expiration():
    clock = FakeClock()
    cache = CacheManager(clock=clock)
    cache.put("local", "get_fundamentals", "AAPL", data="value", ttl_seconds=10)

    clock.advance(10)

    assert cache.get("local", "get_fundamentals", "AAPL") is None


def test_is_expired():
    clock = FakeClock()
    cache = CacheManager(clock=clock)
    entry = CacheEntry(data="value", timestamp=0, ttl_seconds=5)

    assert cache.is_expired(entry) is False

    clock.advance(5)

    assert cache.is_expired(entry) is True


def test_invalidate_specific_entry():
    cache = CacheManager(clock=FakeClock())
    cache.put("local", "get_price_history", "AAPL", data="a", ttl_seconds=60)
    cache.put("local", "get_price_history", "MSFT", data="m", ttl_seconds=60)

    assert cache.invalidate("local", "get_price_history", "AAPL") is True
    assert cache.get("local", "get_price_history", "AAPL") is None
    assert cache.get("local", "get_price_history", "MSFT") == "m"


def test_invalidate_provider():
    cache = CacheManager(clock=FakeClock())
    cache.put("local", "get_price_history", "AAPL", data="local", ttl_seconds=60)
    cache.put("polygon", "get_price_history", "AAPL", data="polygon", ttl_seconds=60)

    assert cache.invalidate_provider("local") is True
    assert cache.get("local", "get_price_history", "AAPL") is None
    assert cache.get("polygon", "get_price_history", "AAPL") == "polygon"


def test_full_clear():
    cache = CacheManager(clock=FakeClock())
    cache.put("local", "get_price_history", "AAPL", data="value", ttl_seconds=60)

    cache.clear()

    assert cache.get("local", "get_price_history", "AAPL") is None


def test_multiple_tickers_and_parameters_are_distinct():
    cache = CacheManager(clock=FakeClock())
    cache.put(
        "local",
        "get_price_history",
        "AAPL",
        parameters={"start": "2026-01-01"},
        data="aapl-start",
        ttl_seconds=60,
    )
    cache.put(
        "local",
        "get_price_history",
        "AAPL",
        parameters={"start": "2026-02-01"},
        data="aapl-other",
        ttl_seconds=60,
    )
    cache.put(
        "local",
        "get_price_history",
        "MSFT",
        parameters={"start": "2026-01-01"},
        data="msft-start",
        ttl_seconds=60,
    )

    assert cache.get(
        "local",
        "get_price_history",
        "AAPL",
        parameters={"start": "2026-01-01"},
    ) == "aapl-start"
    assert cache.get(
        "local",
        "get_price_history",
        "AAPL",
        parameters={"start": "2026-02-01"},
    ) == "aapl-other"
    assert cache.get(
        "local",
        "get_price_history",
        "MSFT",
        parameters={"start": "2026-01-01"},
    ) == "msft-start"
