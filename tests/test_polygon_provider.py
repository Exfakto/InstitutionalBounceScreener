import json
from urllib.error import HTTPError, URLError

import pandas as pd

from providers.polygon_provider import PolygonProvider


class FakeResponse:

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        if isinstance(self.payload, bytes):
            return self.payload

        return json.dumps(self.payload).encode("utf-8")


class FakeOpener:

    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.calls = []

    def __call__(self, url, timeout=None):
        self.calls.append((url, timeout))

        if self.error is not None:
            raise self.error

        return FakeResponse(self.payload)


def aggregate_payload():
    return {
        "ticker": "AAPL",
        "status": "OK",
        "results": [
            {
                "t": 1767225600000,
                "o": 100.0,
                "h": 103.0,
                "l": 99.0,
                "c": 102.0,
                "v": 1000000,
            },
            {
                "t": 1767312000000,
                "o": 102.0,
                "h": 104.0,
                "l": 101.0,
                "c": 103.0,
                "v": 1100000,
            },
        ],
    }


def http_error(status):
    return HTTPError(
        url="https://api.polygon.io/test",
        code=status,
        msg="planned",
        hdrs=None,
        fp=None,
    )


def test_polygon_provider_success(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "test-key")
    opener = FakeOpener(payload=aggregate_payload())
    provider = PolygonProvider(opener=opener)

    result = provider.get_price_history(
        " aapl ",
        start="2026-01-01",
        end="2026-01-02",
    )

    assert result.success is True
    assert result.source == "polygon"
    assert result.message == "Polygon price history retrieved."
    assert result.metadata == {
        "ticker": "AAPL",
        "rows": 2,
        "start": "2026-01-01",
        "end": "2026-01-02",
    }
    assert list(result.data.columns) == ["Open", "High", "Low", "Close", "Volume"]
    assert list(result.data["Close"]) == [102.0, 103.0]
    assert list(result.data.index) == list(
        pd.to_datetime(["2026-01-01", "2026-01-02"])
    )
    assert "AAPL" in opener.calls[0][0]
    assert "apiKey=test-key" in opener.calls[0][0]
    assert opener.calls[0][1] == 30


def test_polygon_provider_missing_key(monkeypatch):
    monkeypatch.delenv("POLYGON_API_KEY", raising=False)
    opener = FakeOpener(payload=aggregate_payload())
    provider = PolygonProvider(opener=opener)

    result = provider.get_price_history("AAPL")

    assert result.success is False
    assert result.message == "Polygon API key is required."
    assert result.metadata["ticker"] == "AAPL"
    assert "Missing POLYGON_API_KEY." in result.warnings
    assert opener.calls == []


def test_polygon_provider_invalid_ticker(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "test-key")
    provider = PolygonProvider(opener=FakeOpener(payload=aggregate_payload()))

    result = provider.get_price_history(" ")

    assert result.success is False
    assert result.message == "Ticker is required."
    assert "Missing ticker." in result.warnings


def test_polygon_provider_rate_limit(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "test-key")
    provider = PolygonProvider(opener=FakeOpener(error=http_error(429)))

    result = provider.get_price_history("AAPL")

    assert result.success is False
    assert result.message == "Polygon rate limit reached for AAPL."
    assert "Rate limited." in result.warnings


def test_polygon_provider_server_error(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "test-key")
    provider = PolygonProvider(opener=FakeOpener(error=http_error(500)))

    result = provider.get_price_history("AAPL")

    assert result.success is False
    assert result.message == "Polygon request failed for AAPL."
    assert "HTTP 500" in result.warnings


def test_polygon_provider_network_failure(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "test-key")
    provider = PolygonProvider(opener=FakeOpener(error=URLError("offline")))

    result = provider.get_price_history("AAPL")

    assert result.success is False
    assert result.message == "Polygon request failed for AAPL."
    assert result.warnings


def test_polygon_provider_malformed_response(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "test-key")
    provider = PolygonProvider(
        opener=FakeOpener(
            payload={
                "ticker": "AAPL",
                "results": [{"t": 1767225600000, "o": 100.0}],
            }
        )
    )

    result = provider.get_price_history("AAPL")

    assert result.success is False
    assert result.message == "Polygon response was malformed for AAPL."
    assert "Malformed response." in result.warnings


def test_polygon_provider_malformed_json(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "test-key")
    provider = PolygonProvider(opener=FakeOpener(payload=b"{not-json"))

    result = provider.get_price_history("AAPL")

    assert result.success is False
    assert result.message == "Polygon response was malformed for AAPL."


def test_polygon_provider_empty_results(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "test-key")
    provider = PolygonProvider(opener=FakeOpener(payload={"results": []}))

    result = provider.get_price_history("AAPL")

    assert result.success is False
    assert result.message == "No Polygon price history found for AAPL."


def test_polygon_provider_deterministic_normalization(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "test-key")
    provider = PolygonProvider(opener=FakeOpener(payload=aggregate_payload()))

    first = provider.get_price_history("AAPL", start="2026-01-01", end="2026-01-02")
    second = provider.get_price_history("AAPL", start="2026-01-01", end="2026-01-02")

    assert first.metadata == second.metadata
    assert first.data.equals(second.data)


def test_polygon_provider_unimplemented_methods(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "test-key")
    provider = PolygonProvider(opener=FakeOpener(payload=aggregate_payload()))

    results = [
        provider.get_fundamentals("AAPL"),
        provider.get_earnings("AAPL"),
        provider.get_institutional_metrics("AAPL"),
        provider.get_insider_activity("AAPL"),
        provider.get_company_profile("AAPL"),
    ]

    assert all(result.success is False for result in results)
    assert all(result.source == "polygon" for result in results)
    assert all("Not yet implemented." in result.warnings for result in results)


def test_polygon_provider_fetch_universe_symbols_normalizes_exchange(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "test-key")
    opener = FakeOpener(
        payload={
            "results": [
                {
                    "ticker": "AAPL",
                    "name": "Apple Inc.",
                    "primary_exchange": "XNAS",
                    "type": "CS",
                    "active": True,
                }
            ]
        }
    )
    provider = PolygonProvider(opener=opener)

    result = provider.fetch_universe_symbols(exchange="NASDAQ")

    assert result.success is True
    assert result.data == [
        {
            "ticker": "AAPL",
            "company_name": "Apple Inc.",
            "exchange": "NASDAQ",
            "security_type": "CS",
            "sector": None,
            "industry": None,
            "market_cap": None,
            "price": None,
            "average_volume": None,
            "average_dollar_volume": None,
            "active": True,
            "source": "polygon",
        }
    ]
    assert "exchange=NASDAQ" in opener.calls[0][0]


def test_polygon_provider_fetch_universe_symbols_paginates(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "test-key")
    opener = FakeOpener(
        payload=None,
    )
    opener.payloads = [
        {
            "results": [{"ticker": "AAPL", "name": "Apple Inc.", "primary_exchange": "XNAS", "type": "CS"}],
            "next_url": "https://api.polygon.io/v3/reference/tickers?cursor=abc",
        },
        {
            "results": [{"ticker": "IBM", "name": "IBM", "primary_exchange": "XNYS", "type": "CS"}],
        },
    ]

    def next_payload(url, timeout=None):
        opener.calls.append((url, timeout))
        return FakeResponse(opener.payloads.pop(0))

    opener.__call__ = next_payload
    provider = PolygonProvider(opener=next_payload)

    result = provider.fetch_universe_symbols()

    assert result.success is True
    assert [row["ticker"] for row in result.data] == ["AAPL", "IBM"]
    assert len(opener.calls) == 2
    assert "apiKey=test-key" in opener.calls[1][0]


def test_polygon_provider_fetch_universe_symbols_missing_key(monkeypatch):
    monkeypatch.delenv("POLYGON_API_KEY", raising=False)
    opener = FakeOpener(payload={"results": []})
    provider = PolygonProvider(opener=opener)

    result = provider.fetch_universe_symbols(exchange="NYSE")

    assert result.success is False
    assert result.message == "Polygon API key is required."
    assert "Missing POLYGON_API_KEY." in result.warnings
    assert opener.calls == []


def test_polygon_provider_fetch_universe_symbols_malformed_response(monkeypatch):
    monkeypatch.setenv("POLYGON_API_KEY", "test-key")
    provider = PolygonProvider(opener=FakeOpener(payload={"results": {"bad": "shape"}}))

    result = provider.fetch_universe_symbols()

    assert result.success is False
    assert result.message == "Polygon universe response was malformed."
    assert "Malformed response." in result.warnings
