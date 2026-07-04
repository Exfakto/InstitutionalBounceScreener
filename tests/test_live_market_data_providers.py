import json
from types import SimpleNamespace
from urllib.error import HTTPError, URLError

from market_data.http_client import HttpClient
from market_data.live_adapters import (
    AlpacaMarketDataProvider,
    FinancialModelingPrepProvider,
    PolygonMarketDataProvider,
)
from market_data.local_csv_provider import LocalCsvMarketDataProvider
from market_data.provider_factory import ProviderFactory


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class FakeOpener:
    def __init__(self, responses=None, errors=None):
        self.responses = list(responses or [])
        self.errors = list(errors or [])
        self.calls = []

    def __call__(self, request, timeout=None):
        self.calls.append((request.full_url, timeout, dict(request.header_items())))
        if self.errors:
            error = self.errors.pop(0)
            if error is not None:
                raise error
        if self.responses:
            return self.responses.pop(0)
        return FakeResponse({})


def http_error(status):
    return HTTPError("https://example.test", status, "planned", hdrs=None, fp=None)


def preferences(**overrides):
    defaults = {
        "selected_market_data_provider": "local_csv",
        "polygon_api_key": "",
        "fmp_api_key": "",
        "alpaca_api_key": "",
        "alpaca_api_secret": "",
        "request_timeout_seconds": 5,
        "max_retries": 1,
        "rate_limit_sleep_seconds": 0,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


class FakeSettingsService:
    def __init__(self, prefs):
        self.prefs = prefs

    def get_preferences(self):
        return self.prefs


def test_provider_factory_selection_polygon():
    result = ProviderFactory(
        settings_service=FakeSettingsService(
            preferences(selected_market_data_provider="polygon", polygon_api_key="key")
        ),
        http_client=HttpClient(opener=FakeOpener()),
    ).create()

    assert result.success is True
    assert result.provider_name == "polygon"
    assert isinstance(result.provider, PolygonMarketDataProvider)


def test_provider_factory_defaults_to_polygon_when_local_csv_and_env_key_present(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "env-polygon-key")
    monkeypatch.setenv("FMP_API_KEY", "env-fmp-key")

    result = ProviderFactory(
        settings_service=FakeSettingsService(
            preferences(selected_market_data_provider="local_csv")
        ),
        http_client=HttpClient(opener=FakeOpener()),
    ).create()

    assert result.success is True
    assert result.provider_name == "polygon"
    assert isinstance(result.provider, PolygonMarketDataProvider)
    assert result.provider.api_key == "env-polygon-key"


def test_provider_factory_defaults_to_fmp_when_only_fmp_env_key_present(monkeypatch):
    monkeypatch.delenv("POLYGON_API_KEY", raising=False)
    monkeypatch.setenv("FMP_API_KEY", "env-fmp-key")

    result = ProviderFactory(
        settings_service=FakeSettingsService(
            preferences(selected_market_data_provider="local_csv")
        ),
        http_client=HttpClient(opener=FakeOpener()),
    ).create()

    assert result.success is True
    assert result.provider_name == "fmp"
    assert isinstance(result.provider, FinancialModelingPrepProvider)
    assert result.provider.api_key == "env-fmp-key"


def test_provider_factory_missing_api_key_behavior(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)

    result = ProviderFactory(
        settings_service=FakeSettingsService(
            preferences(selected_market_data_provider="fmp")
        )
    ).create()

    assert result.success is False
    assert result.provider is None
    assert "Missing credentials" in result.errors[0]


def test_provider_factory_local_csv_fallback(tmp_path, monkeypatch):
    monkeypatch.delenv("POLYGON_API_KEY", raising=False)
    monkeypatch.delenv("FMP_API_KEY", raising=False)

    result = ProviderFactory(
        settings_service=FakeSettingsService(
            preferences(selected_market_data_provider="unknown")
        ),
        local_csv_directory=tmp_path,
    ).create()

    assert result.success is True
    assert result.provider_name == "local_csv"
    assert isinstance(result.provider, LocalCsvMarketDataProvider)
    assert result.warnings


def test_polygon_successful_mocked_ohlcv_response():
    opener = FakeOpener(
        responses=[
            FakeResponse(
                {
                    "results": [
                        {
                            "t": 1767312000000,
                            "o": 100,
                            "h": 105,
                            "l": 99,
                            "c": 104,
                            "v": 1000000,
                        }
                    ]
                }
            )
        ]
    )
    provider = PolygonMarketDataProvider(
        api_key="key",
        http_client=HttpClient(opener=opener),
    )

    rows = provider.fetch_daily_ohlcv("aapl", "2026-01-01", "2026-01-31")

    assert rows[0].ticker == "AAPL"
    assert rows[0].close == 104
    assert rows[0].source == "polygon"
    assert "apiKey=key" in opener.calls[0][0]


def test_fmp_mocked_fundamentals_response():
    provider = FinancialModelingPrepProvider(
        api_key="key",
        http_client=HttpClient(
            opener=FakeOpener(
                responses=[
                    FakeResponse(
                        [
                            {
                                "companyName": "Apple Inc.",
                                "exchangeShortName": "NASDAQ",
                                "sector": "Technology",
                                "industry": "Consumer Electronics",
                                "mktCap": 300,
                            }
                        ]
                    )
                ]
            )
        ),
    )

    data = provider.fetch_fundamentals("AAPL")

    assert data["company_name"] == "Apple Inc."
    assert data["market_cap"] == 300


def test_alpaca_mocked_universe_response():
    opener = FakeOpener(
        responses=[
            FakeResponse(
                [
                    {
                        "symbol": "AAPL",
                        "exchange": "NASDAQ",
                        "class": "us_equity",
                        "name": "Apple Inc.",
                    },
                    {
                        "symbol": "IBM",
                        "exchange": "NYSE",
                        "class": "us_equity",
                        "name": "IBM",
                    },
                ]
            )
        ]
    )
    provider = AlpacaMarketDataProvider(
        api_key="key",
        api_secret="secret",
        http_client=HttpClient(opener=opener),
    )

    symbols = provider.fetch_universe_symbols(exchange="NASDAQ")

    assert [symbol.ticker for symbol in symbols] == ["AAPL"]
    assert opener.calls[0][2]["Apca-api-key-id"] == "key"


def test_http_client_retry_behavior():
    opener = FakeOpener(
        responses=[FakeResponse({"ok": True})],
        errors=[http_error(500), None],
    )
    client = HttpClient(opener=opener, max_retries=1)

    response = client.get_json("https://example.test/data")

    assert response.success is True
    assert response.attempts == 2
    assert len(opener.calls) == 2


def test_http_client_rate_limit_behavior():
    sleeps = []
    opener = FakeOpener(
        responses=[FakeResponse({"ok": True})],
        errors=[http_error(429), None],
    )
    client = HttpClient(
        opener=opener,
        max_retries=1,
        rate_limit_sleep_seconds=2,
        sleeper=sleeps.append,
    )

    response = client.get_json("https://example.test/data")

    assert response.success is True
    assert sleeps == [2]
    assert "Rate limit" in response.warnings[0]


def test_http_client_timeout_and_error_behavior():
    client = HttpClient(
        opener=FakeOpener(errors=[URLError("timed out")]),
        max_retries=0,
    )

    response = client.get_json("https://example.test/data")

    assert response.success is False
    assert "timed out" in response.error


def test_live_provider_missing_credentials_safe_error():
    provider = PolygonMarketDataProvider(api_key="")

    rows = provider.fetch_daily_ohlcv("AAPL", "2026-01-01", "2026-01-31")

    assert rows == []
    assert provider.last_errors == ["Missing credentials: api_key"]
