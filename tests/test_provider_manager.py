from providers.local_provider import LocalProvider
from providers.cache_manager import CacheManager
from providers.provider_config import ProviderConfig
from providers.provider_manager import ProviderManager
from providers.provider_result import ProviderResult


class FakeProvider:

    def __init__(self, name="fake"):
        self.name = name
        self.calls = []

    def result(self, method, ticker):
        self.calls.append((method, ticker))
        return ProviderResult.ok(
            data={"method": method, "ticker": ticker},
            message=f"{method} ok",
            source=self.name,
            metadata={"provider": self.name},
        )

    def get_price_history(self, ticker, start=None, end=None):
        self.calls.append(("get_price_history", ticker, start, end))
        return ProviderResult.ok(
            data={"ticker": ticker, "start": start, "end": end},
            message="prices ok",
            source=self.name,
        )

    def get_fundamentals(self, ticker):
        return self.result("get_fundamentals", ticker)

    def get_earnings(self, ticker):
        return self.result("get_earnings", ticker)

    def get_institutional_metrics(self, ticker):
        return self.result("get_institutional_metrics", ticker)

    def get_insider_activity(self, ticker):
        return self.result("get_insider_activity", ticker)

    def get_company_profile(self, ticker):
        return self.result("get_company_profile", ticker)


class RaisingProvider(FakeProvider):

    def get_fundamentals(self, ticker):
        raise RuntimeError("planned provider failure")


class InvalidProvider(FakeProvider):

    def get_fundamentals(self, ticker):
        return {"success": True}


class FailingProvider(FakeProvider):

    def result(self, method, ticker):
        self.calls.append((method, ticker))
        return ProviderResult.fail(
            "planned failure",
            source=self.name,
            metadata={"ticker": ticker},
        )

    def get_fundamentals(self, ticker):
        return self.result("get_fundamentals", ticker)


def test_default_provider_is_local_provider():
    manager = ProviderManager()

    assert manager.active_provider_name == "local"
    assert isinstance(manager.active_provider(), LocalProvider)


def test_provider_registration():
    manager = ProviderManager(default_provider=FakeProvider("local"))
    provider = FakeProvider("mock")

    result = manager.register_provider(" Mock ", provider)

    assert result.success is True
    assert result.metadata["provider"] == "mock"
    assert manager._providers["mock"] is provider


def test_provider_switching_and_delegation():
    local_provider = FakeProvider("local")
    mock_provider = FakeProvider("mock")
    manager = ProviderManager(default_provider=local_provider)
    manager.register_provider("mock", mock_provider)

    switch_result = manager.set_active_provider("mock")
    result = manager.get_price_history("AAPL", start="2026-01-01", end="2026-01-31")

    assert switch_result.success is True
    assert manager.active_provider_name == "mock"
    assert result.success is True
    assert result.source == "mock"
    assert result.data == {
        "ticker": "AAPL",
        "start": "2026-01-01",
        "end": "2026-01-31",
    }
    assert mock_provider.calls == [
        ("get_price_history", "AAPL", "2026-01-01", "2026-01-31")
    ]
    assert local_provider.calls == []


def test_unknown_provider_returns_safe_failure():
    manager = ProviderManager(default_provider=FakeProvider("local"))

    result = manager.set_active_provider("missing")

    assert result.success is False
    assert result.message == "Unknown provider."
    assert result.metadata["provider"] == "missing"
    assert "Provider is not registered." in result.warnings
    assert manager.active_provider_name == "local"


def test_missing_provider_never_crashes():
    manager = ProviderManager(default_provider=FakeProvider("local"))
    manager._active_provider_name = "missing"

    result = manager.get_fundamentals("AAPL")

    assert result.success is True
    assert result.source == "local"


def test_all_methods_delegate_and_propagate_provider_result():
    provider = FakeProvider("local")
    manager = ProviderManager(default_provider=provider)

    results = [
        manager.get_fundamentals("AAPL"),
        manager.get_earnings("AAPL"),
        manager.get_institutional_metrics("AAPL"),
        manager.get_insider_activity("AAPL"),
        manager.get_company_profile("AAPL"),
    ]

    assert all(result.success for result in results)
    assert [result.data["method"] for result in results] == [
        "get_fundamentals",
        "get_earnings",
        "get_institutional_metrics",
        "get_insider_activity",
        "get_company_profile",
    ]
    assert provider.calls == [
        ("get_fundamentals", "AAPL"),
        ("get_earnings", "AAPL"),
        ("get_institutional_metrics", "AAPL"),
        ("get_insider_activity", "AAPL"),
        ("get_company_profile", "AAPL"),
    ]


def test_provider_exception_returns_safe_failure():
    manager = ProviderManager(default_provider=RaisingProvider("local"))

    result = manager.get_fundamentals("AAPL")

    assert result.success is False
    assert result.message == "No provider could satisfy get_fundamentals."
    assert "planned provider failure" in result.warnings
    assert result.metadata["attempted_providers"] == ["local"]


def test_invalid_provider_result_returns_safe_failure():
    manager = ProviderManager(default_provider=InvalidProvider("local"))

    result = manager.get_fundamentals("AAPL")

    assert result.success is False
    assert result.message == "No provider could satisfy get_fundamentals."
    assert "Invalid provider result." in result.warnings
    assert result.metadata["attempted_providers"] == ["local"]


def test_registration_requires_name_and_provider():
    manager = ProviderManager(default_provider=FakeProvider("local"))

    missing_name = manager.register_provider(" ", FakeProvider())
    missing_provider = manager.register_provider("mock", None)

    assert missing_name.success is False
    assert missing_provider.success is False
    assert "Provider name and instance are required." in missing_name.warnings


def test_deterministic_behavior():
    manager = ProviderManager(default_provider=FakeProvider("local"))
    manager.register_provider("mock", FakeProvider("mock"))
    manager.set_active_provider("mock")

    first = manager.get_company_profile("AAPL")
    second = manager.get_company_profile("AAPL")

    assert first == second


def test_provider_manager_uses_config_active_provider():
    local_provider = FakeProvider("local")
    mock_provider = FakeProvider("mock")
    config = ProviderConfig(
        active_provider="mock",
        providers={
            "local": {"enabled": True},
            "mock": {"enabled": True},
        },
    )
    manager = ProviderManager(
        default_provider=local_provider,
        provider_config=config,
    )
    manager.register_provider("mock", mock_provider)
    manager.apply_configured_active_provider()

    result = manager.get_company_profile("AAPL")

    assert manager.active_provider_name == "mock"
    assert result.source == "mock"
    assert mock_provider.calls == [("get_company_profile", "AAPL")]


def test_provider_manager_active_polygon_configured_but_disabled_falls_back_to_local():
    manager = ProviderManager(
        default_provider=FakeProvider("local"),
        provider_config=ProviderConfig(
            active_provider="polygon",
            providers={
                "local": {"enabled": True},
                "polygon": {"enabled": False, "api_key_env": "POLYGON_API_KEY"},
            },
        ),
    )

    assert manager.active_provider_name == "local"
    assert "polygon" not in manager._providers


def test_provider_manager_unknown_configured_provider_falls_back_to_local():
    manager = ProviderManager(
        default_provider=FakeProvider("local"),
        provider_config=ProviderConfig(
            active_provider="missing",
            providers={
                "local": {"enabled": True},
                "missing": {"enabled": True},
            },
        ),
    )

    assert manager.active_provider_name == "local"


def test_provider_manager_registers_enabled_polygon_without_requiring_api_key(monkeypatch):
    monkeypatch.delenv("POLYGON_API_KEY", raising=False)
    manager = ProviderManager(
        default_provider=FakeProvider("local"),
        provider_config=ProviderConfig(
            active_provider="local",
            providers={
                "local": {"enabled": True},
                "polygon": {"enabled": True, "api_key_env": "POLYGON_API_KEY"},
            },
        ),
    )

    assert manager.active_provider_name == "local"
    assert "polygon" in manager._providers


def test_provider_manager_local_provider_requires_no_api_key(monkeypatch):
    monkeypatch.delenv("POLYGON_API_KEY", raising=False)
    provider = FakeProvider("local")
    manager = ProviderManager(
        default_provider=provider,
        provider_config=ProviderConfig(
            active_provider="local",
            providers={"local": {"enabled": True}},
        ),
    )

    result = manager.get_fundamentals("AAPL")

    assert result.success is True
    assert result.source == "local"


def test_provider_manager_cache_hit_avoids_provider_call():
    provider = FakeProvider("local")
    manager = ProviderManager(
        default_provider=provider,
        cache_manager=CacheManager(),
    )

    first = manager.get_fundamentals("AAPL")
    second = manager.get_fundamentals("AAPL")

    assert first == second
    assert provider.calls == [("get_fundamentals", "AAPL")]


def test_provider_manager_cache_miss_by_ticker():
    provider = FakeProvider("local")
    manager = ProviderManager(
        default_provider=provider,
        cache_manager=CacheManager(),
    )

    manager.get_fundamentals("AAPL")
    manager.get_fundamentals("MSFT")

    assert provider.calls == [
        ("get_fundamentals", "AAPL"),
        ("get_fundamentals", "MSFT"),
    ]


def test_provider_manager_cache_miss_by_parameters():
    provider = FakeProvider("local")
    manager = ProviderManager(
        default_provider=provider,
        cache_manager=CacheManager(),
    )

    manager.get_price_history("AAPL", start="2026-01-01", end="2026-01-31")
    manager.get_price_history("AAPL", start="2026-02-01", end="2026-02-28")

    assert provider.calls == [
        ("get_price_history", "AAPL", "2026-01-01", "2026-01-31"),
        ("get_price_history", "AAPL", "2026-02-01", "2026-02-28"),
    ]


def test_provider_manager_failed_results_are_not_cached():
    provider = FailingProvider("local")
    manager = ProviderManager(
        default_provider=provider,
        cache_manager=CacheManager(),
    )

    first = manager.get_fundamentals("AAPL")
    second = manager.get_fundamentals("AAPL")

    assert first.success is False
    assert second.success is False
    assert provider.calls == [
        ("get_fundamentals", "AAPL"),
        ("get_fundamentals", "AAPL"),
    ]


def test_provider_manager_cache_separates_multiple_providers():
    local_provider = FakeProvider("local")
    mock_provider = FakeProvider("mock")
    manager = ProviderManager(
        default_provider=local_provider,
        cache_manager=CacheManager(),
    )
    manager.register_provider("mock", mock_provider)

    local_result = manager.get_fundamentals("AAPL")
    manager.set_active_provider("mock")
    mock_result = manager.get_fundamentals("AAPL")
    second_mock_result = manager.get_fundamentals("AAPL")

    assert local_result.source == "local"
    assert mock_result.source == "mock"
    assert second_mock_result == mock_result
    assert local_provider.calls == [("get_fundamentals", "AAPL")]
    assert mock_provider.calls == [("get_fundamentals", "AAPL")]


def test_provider_manager_cache_uses_default_ttl():
    provider = FakeProvider("local")
    cache = CacheManager()
    manager = ProviderManager(default_provider=provider, cache_manager=cache)

    manager.get_company_profile("AAPL")
    key = cache.make_key(
        "local",
        "get_company_profile",
        "AAPL",
        {},
    )

    assert cache._entries[key].ttl_seconds == 7 * 24 * 60 * 60


def test_failover_first_provider_succeeds():
    first_provider = FakeProvider("first")
    second_provider = FakeProvider("second")
    manager = ProviderManager(
        default_provider=FakeProvider("local"),
        provider_priorities={"get_company_profile": ["first", "second"]},
    )
    manager.register_provider("first", first_provider)
    manager.register_provider("second", second_provider)

    result = manager.get_company_profile("AAPL")

    assert result.success is True
    assert result.source == "first"
    assert first_provider.calls == [("get_company_profile", "AAPL")]
    assert second_provider.calls == []


def test_failover_second_provider_succeeds():
    first_provider = FailingProvider("first")
    second_provider = FakeProvider("second")
    manager = ProviderManager(
        default_provider=FakeProvider("local"),
        provider_priorities={"get_company_profile": ["first", "second"]},
    )
    manager.register_provider("first", first_provider)
    manager.register_provider("second", second_provider)

    result = manager.get_company_profile("AAPL")

    assert result.success is True
    assert result.source == "second"
    assert first_provider.calls == [("get_company_profile", "AAPL")]
    assert second_provider.calls == [("get_company_profile", "AAPL")]


def test_failover_third_provider_succeeds():
    first_provider = FailingProvider("first")
    second_provider = FailingProvider("second")
    third_provider = FakeProvider("third")
    manager = ProviderManager(
        default_provider=FakeProvider("local"),
        provider_priorities={
            "get_company_profile": ["first", "second", "third"]
        },
    )
    manager.register_provider("first", first_provider)
    manager.register_provider("second", second_provider)
    manager.register_provider("third", third_provider)

    result = manager.get_company_profile("AAPL")

    assert result.success is True
    assert result.source == "third"
    assert first_provider.calls == [("get_company_profile", "AAPL")]
    assert second_provider.calls == [("get_company_profile", "AAPL")]
    assert third_provider.calls == [("get_company_profile", "AAPL")]


def test_failover_disabled_provider_skipped():
    disabled_provider = FakeProvider("disabled")
    fallback_provider = FakeProvider("fallback")
    manager = ProviderManager(
        default_provider=FakeProvider("local"),
        provider_config=ProviderConfig(
            active_provider="local",
            providers={
                "local": {"enabled": True},
                "disabled": {"enabled": False},
            },
        ),
        provider_priorities={
            "get_company_profile": ["disabled", "fallback"]
        },
    )
    manager.register_provider("disabled", disabled_provider)
    manager.register_provider("fallback", fallback_provider)

    result = manager.get_company_profile("AAPL")

    assert result.success is True
    assert result.source == "fallback"
    assert disabled_provider.calls == []
    assert fallback_provider.calls == [("get_company_profile", "AAPL")]


def test_failover_unregistered_provider_skipped():
    fallback_provider = FakeProvider("fallback")
    manager = ProviderManager(
        default_provider=FakeProvider("local"),
        provider_priorities={
            "get_company_profile": ["missing", "fallback"]
        },
    )
    manager.register_provider("fallback", fallback_provider)

    result = manager.get_company_profile("AAPL")

    assert result.success is True
    assert result.source == "fallback"
    assert fallback_provider.calls == [("get_company_profile", "AAPL")]


def test_failover_all_providers_fail_standardized_failure():
    first_provider = FailingProvider("first")
    second_provider = FailingProvider("second")
    manager = ProviderManager(
        default_provider=FailingProvider("local"),
        provider_priorities={"get_company_profile": ["first", "second"]},
    )
    manager.register_provider("first", first_provider)
    manager.register_provider("second", second_provider)

    result = manager.get_company_profile("AAPL")

    assert result.success is False
    assert result.source == "provider_manager"
    assert result.message == "No provider could satisfy get_company_profile."
    assert result.metadata["attempted_providers"] == [
        "first",
        "second",
        "local",
    ]
    assert result.metadata["skipped_providers"] == []
    assert "first: planned failure" in result.warnings
    assert "second: planned failure" in result.warnings
    assert "local: planned failure" in result.warnings


def test_failover_deterministic_provider_ordering():
    manager = ProviderManager(
        default_provider=FakeProvider("local"),
        provider_priorities={
            "get_earnings": ["third", "second", "first", "second"]
        },
    )

    assert manager.priority_for("get_earnings") == [
        "third",
        "second",
        "first",
        "local",
    ]
