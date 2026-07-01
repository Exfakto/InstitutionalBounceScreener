from services.live_data_service import LiveDataService
from providers.provider_result import ProviderResult


class FakeProviderManager:

    def __init__(self, failure=False):
        self.calls = []
        self.failure = failure

    def result(self, method_name, ticker):
        self.calls.append((method_name, ticker))

        if self.failure:
            return ProviderResult.fail(
                "provider failed",
                source="fake_provider",
                warnings=["planned failure"],
            )

        return ProviderResult.ok(
            data={"method": method_name, "ticker": ticker},
            message=f"{method_name} ok",
            source="fake_provider",
        )

    def get_price_history(self, ticker, start=None, end=None):
        self.calls.append(("get_price_history", ticker, start, end))

        if self.failure:
            return ProviderResult.fail(
                "provider failed",
                source="fake_provider",
                warnings=["planned failure"],
            )

        return ProviderResult.ok(
            data={"ticker": ticker, "start": start, "end": end},
            message="price history ok",
            source="fake_provider",
        )

    def get_company_profile(self, ticker):
        return self.result("get_company_profile", ticker)

    def get_fundamentals(self, ticker):
        return self.result("get_fundamentals", ticker)

    def get_earnings(self, ticker):
        return self.result("get_earnings", ticker)

    def get_institutional_metrics(self, ticker):
        return self.result("get_institutional_metrics", ticker)


class WriteTrackingProviderManager(FakeProviderManager):

    def __init__(self):
        super().__init__()
        self.write_called = False

    def save_price_history(self, *args, **kwargs):
        self.write_called = True
        raise AssertionError("LiveDataService must not write data.")


class NetworkTrackingProviderManager(FakeProviderManager):

    def __init__(self):
        super().__init__()
        self.network_called = False

    def request(self, *args, **kwargs):
        self.network_called = True
        raise AssertionError("LiveDataService must not perform network calls.")


def test_successful_price_history_fetch_through_fake_provider():
    manager = FakeProviderManager()
    service = LiveDataService(provider_manager=manager)

    result = service.get_price_history(" aapl ", start="2026-01-01", end="2026-01-31")

    assert result.success is True
    assert result.data == {
        "ticker": "AAPL",
        "start": "2026-01-01",
        "end": "2026-01-31",
    }
    assert manager.calls == [
        ("get_price_history", "AAPL", "2026-01-01", "2026-01-31")
    ]


def test_missing_ticker_returns_safe_failure():
    manager = FakeProviderManager()
    service = LiveDataService(provider_manager=manager)

    result = service.get_price_history(" ")

    assert result.success is False
    assert result.message == "Ticker is required."
    assert "Missing ticker." in result.warnings
    assert manager.calls == []


def test_provider_failure_passes_through_safely():
    manager = FakeProviderManager(failure=True)
    service = LiveDataService(provider_manager=manager)

    result = service.get_fundamentals("AAPL")

    assert result.success is False
    assert result.message == "provider failed"
    assert result.source == "fake_provider"
    assert "planned failure" in result.warnings


def test_provider_manager_dependency_injection():
    manager = FakeProviderManager()
    service = LiveDataService(provider_manager=manager)

    assert service.provider_manager is manager


def test_company_profile_pass_through():
    manager = FakeProviderManager()
    service = LiveDataService(provider_manager=manager)

    result = service.get_company_profile("msft")

    assert result.success is True
    assert result.data == {"method": "get_company_profile", "ticker": "MSFT"}
    assert manager.calls == [("get_company_profile", "MSFT")]


def test_fundamentals_pass_through():
    manager = FakeProviderManager()
    service = LiveDataService(provider_manager=manager)

    result = service.get_fundamentals("tsla")

    assert result.success is True
    assert result.data == {"method": "get_fundamentals", "ticker": "TSLA"}
    assert manager.calls == [("get_fundamentals", "TSLA")]


def test_earnings_pass_through():
    manager = FakeProviderManager()
    service = LiveDataService(provider_manager=manager)

    result = service.get_earnings("nvda")

    assert result.success is True
    assert result.data == {"method": "get_earnings", "ticker": "NVDA"}
    assert manager.calls == [("get_earnings", "NVDA")]


def test_institutional_metrics_pass_through():
    manager = FakeProviderManager()
    service = LiveDataService(provider_manager=manager)

    result = service.get_institutional_metrics("amzn")

    assert result.success is True
    assert result.data == {
        "method": "get_institutional_metrics",
        "ticker": "AMZN",
    }
    assert manager.calls == [("get_institutional_metrics", "AMZN")]


def test_no_database_writes():
    manager = WriteTrackingProviderManager()
    service = LiveDataService(provider_manager=manager)

    result = service.get_price_history("AAPL")

    assert result.success is True
    assert manager.write_called is False


def test_no_network_calls_in_tests():
    manager = NetworkTrackingProviderManager()
    service = LiveDataService(provider_manager=manager)

    result = service.get_company_profile("AAPL")

    assert result.success is True
    assert manager.network_called is False


def test_unavailable_provider_manager_method_fails_safely():
    service = LiveDataService(provider_manager=object())

    result = service.get_fundamentals("AAPL")

    assert result.success is False
    assert result.message == "Provider manager method is unavailable."
    assert "get_fundamentals is not available." in result.warnings
