from providers.local_provider import LocalProvider
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

    assert result.success is False
    assert result.message == "No active provider is available."
    assert "Missing provider." in result.warnings


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
    assert result.message == "Provider request failed for get_fundamentals."
    assert "planned provider failure" in result.warnings


def test_invalid_provider_result_returns_safe_failure():
    manager = ProviderManager(default_provider=InvalidProvider("local"))

    result = manager.get_fundamentals("AAPL")

    assert result.success is False
    assert result.message == "Provider returned an invalid result for get_fundamentals."
    assert "Invalid provider result." in result.warnings


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
