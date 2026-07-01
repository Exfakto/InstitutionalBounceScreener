import json
from urllib.error import HTTPError, URLError

from providers.finnhub_provider import FinnhubProvider


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

    def __init__(self, responses=None, error=None):
        self.responses = list(responses or [])
        self.error = error
        self.calls = []

    def __call__(self, url, timeout=None):
        self.calls.append((url, timeout))

        if self.error is not None:
            raise self.error

        return FakeResponse(self.responses.pop(0))


def http_error(status):
    return HTTPError(
        url="https://finnhub.io/api/v1/test",
        code=status,
        msg="planned",
        hdrs=None,
        fp=None,
    )


def test_finnhub_provider_missing_api_key(monkeypatch):
    monkeypatch.delenv("FINNHUB_API_KEY", raising=False)
    opener = FakeOpener(responses=[{}])
    provider = FinnhubProvider(opener=opener)

    result = provider.get_company_profile("AAPL")

    assert result.success is False
    assert result.source == "finnhub"
    assert result.message == "Finnhub API key is required."
    assert result.metadata["ticker"] == "AAPL"
    assert "Missing FINNHUB_API_KEY." in result.warnings
    assert opener.calls == []


def test_finnhub_provider_missing_ticker(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key")
    provider = FinnhubProvider(opener=FakeOpener(responses=[{}]))

    result = provider.get_company_profile(" ")

    assert result.success is False
    assert result.message == "Ticker is required."
    assert "Missing ticker." in result.warnings


def test_finnhub_provider_successful_earnings(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key")
    opener = FakeOpener(
        responses=[
            {"earningsCalendar": [{"date": "2026-02-01", "symbol": "AAPL"}]},
            [
                {
                    "period": "2025-Q4",
                    "estimate": 2.1,
                    "actual": 2.3,
                    "surprisePercent": 9.52,
                }
            ],
        ]
    )
    provider = FinnhubProvider(opener=opener)

    result = provider.get_earnings(" aapl ")

    assert result.success is True
    assert result.source == "finnhub"
    assert result.message == "Finnhub earnings retrieved."
    assert result.data == {
        "upcoming_earnings_date": "2026-02-01",
        "historical_earnings_surprises": [
            {
                "period": "2025-Q4",
                "eps_estimate": 2.1,
                "eps_actual": 2.3,
                "surprise_percent": 9.52,
            }
        ],
        "eps_estimate": 2.1,
        "eps_actual": 2.3,
        "surprise_percent": 9.52,
    }
    assert result.metadata == {"ticker": "AAPL", "historical_rows": 1}
    assert "calendar/earnings" in opener.calls[0][0]
    assert "symbol=AAPL" in opener.calls[0][0]
    assert "token=test-key" in opener.calls[0][0]
    assert opener.calls[0][1] == 30


def test_finnhub_provider_successful_insider_activity(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key")
    opener = FakeOpener(
        responses=[
            {"data": [{"symbol": "MSFT", "mspr": 12.5}]},
            {"data": [{"name": "Jane Insider", "share": 100, "transactionCode": "P"}]},
        ]
    )
    provider = FinnhubProvider(opener=opener)

    result = provider.get_insider_activity("msft")

    assert result.success is True
    assert result.message == "Finnhub insider activity retrieved."
    assert result.data == {
        "insider_sentiment": [{"symbol": "MSFT", "mspr": 12.5}],
        "insider_transactions": [
            {"name": "Jane Insider", "share": 100, "transactionCode": "P"}
        ],
    }
    assert result.metadata == {
        "ticker": "MSFT",
        "sentiment_rows": 1,
        "transaction_rows": 1,
    }


def test_finnhub_provider_successful_company_profile(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key")
    opener = FakeOpener(
        responses=[
            {
                "name": "NVIDIA Corp",
                "ticker": "NVDA",
                "exchange": "NASDAQ NMS - GLOBAL MARKET",
                "finnhubIndustry": "Semiconductors",
                "sector": "Technology",
                "marketCapitalization": 3500000,
                "weburl": "https://www.nvidia.com",
            }
        ]
    )
    provider = FinnhubProvider(opener=opener)

    result = provider.get_company_profile("nvda")

    assert result.success is True
    assert result.message == "Finnhub company profile retrieved."
    assert result.data == {
        "name": "NVIDIA Corp",
        "ticker": "NVDA",
        "exchange": "NASDAQ NMS - GLOBAL MARKET",
        "industry": "Semiconductors",
        "sector": "Technology",
        "market_cap": 3500000,
        "web_url": "https://www.nvidia.com",
    }
    assert result.metadata == {"ticker": "NVDA"}
    assert "stock/profile2" in opener.calls[0][0]


def test_finnhub_provider_malformed_response(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key")
    provider = FinnhubProvider(opener=FakeOpener(responses=[[]]))

    result = provider.get_company_profile("AAPL")

    assert result.success is False
    assert result.message == "Finnhub response was malformed for AAPL."
    assert "Malformed response." in result.warnings


def test_finnhub_provider_malformed_json(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key")
    provider = FinnhubProvider(opener=FakeOpener(responses=[b"{not-json"]))

    result = provider.get_company_profile("AAPL")

    assert result.success is False
    assert result.message == "Finnhub response was malformed for AAPL."


def test_finnhub_provider_server_error(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key")
    provider = FinnhubProvider(opener=FakeOpener(error=http_error(500)))

    result = provider.get_company_profile("AAPL")

    assert result.success is False
    assert result.message == "Finnhub request failed for AAPL."
    assert "HTTP 500" in result.warnings


def test_finnhub_provider_rate_limit(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key")
    provider = FinnhubProvider(opener=FakeOpener(error=http_error(429)))

    result = provider.get_company_profile("AAPL")

    assert result.success is False
    assert result.message == "Finnhub rate limit reached for AAPL."
    assert "Rate limited." in result.warnings


def test_finnhub_provider_network_failure(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key")
    provider = FinnhubProvider(opener=FakeOpener(error=URLError("offline")))

    result = provider.get_company_profile("AAPL")

    assert result.success is False
    assert result.message == "Finnhub request failed for AAPL."
    assert result.warnings


def test_finnhub_provider_deterministic_ticker_normalization(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key")
    payload = {"name": "Apple Inc.", "ticker": "AAPL"}
    first_provider = FinnhubProvider(opener=FakeOpener(responses=[payload]))
    second_provider = FinnhubProvider(opener=FakeOpener(responses=[payload]))

    first = first_provider.get_company_profile(" aapl ")
    second = second_provider.get_company_profile("AAPL")

    assert first.data == second.data
    assert first.metadata == second.metadata


def test_finnhub_provider_not_implemented_methods_return_safe_failures(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "test-key")
    provider = FinnhubProvider(opener=FakeOpener(responses=[]))

    results = [
        provider.get_price_history("AAPL"),
        provider.get_fundamentals("AAPL"),
        provider.get_institutional_metrics("AAPL"),
    ]

    assert all(result.success is False for result in results)
    assert all(result.source == "finnhub" for result in results)
    assert all("Not yet implemented." in result.warnings for result in results)
