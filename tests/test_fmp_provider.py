import json
from urllib.error import HTTPError, URLError

from providers.fmp_provider import FMPProvider


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


def http_error(status):
    return HTTPError(
        url="https://financialmodelingprep.com/api/v3/test",
        code=status,
        msg="planned",
        hdrs=None,
        fp=None,
    )


def test_fmp_provider_missing_api_key(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    opener = FakeOpener(payload=[{"symbol": "AAPL"}])
    provider = FMPProvider(opener=opener)

    result = provider.get_company_profile("AAPL")

    assert result.success is False
    assert result.source == "fmp"
    assert result.message == "FMP API key is required."
    assert result.metadata["ticker"] == "AAPL"
    assert "Missing FMP_API_KEY." in result.warnings
    assert opener.calls == []


def test_fmp_provider_missing_ticker(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    provider = FMPProvider(opener=FakeOpener(payload=[{"symbol": "AAPL"}]))

    result = provider.get_company_profile(" ")

    assert result.success is False
    assert result.message == "Ticker is required."
    assert "Missing ticker." in result.warnings


def test_fmp_provider_successful_company_profile(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    opener = FakeOpener(
        payload=[
            {
                "symbol": "AAPL",
                "companyName": "Apple Inc.",
                "sector": "Technology",
            }
        ]
    )
    provider = FMPProvider(opener=opener)

    result = provider.get_company_profile(" aapl ")

    assert result.success is True
    assert result.source == "fmp"
    assert result.message == "FMP company profile retrieved."
    assert result.data == {
        "symbol": "AAPL",
        "companyName": "Apple Inc.",
        "sector": "Technology",
    }
    assert result.metadata == {
        "ticker": "AAPL",
        "endpoint": "company_profile",
        "rows": 1,
    }
    assert "/profile/AAPL?" in opener.calls[0][0]
    assert "apikey=test-key" in opener.calls[0][0]
    assert opener.calls[0][1] == 30


def test_fmp_provider_successful_fundamentals(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    provider = FMPProvider(
        opener=FakeOpener(
            payload=[
                {"symbol": "MSFT", "date": "2025-12-31", "revenue": 1000},
                {"symbol": "MSFT", "date": "2024-12-31", "revenue": 900},
            ]
        )
    )

    result = provider.get_fundamentals("msft")

    assert result.success is True
    assert result.message == "FMP fundamentals retrieved."
    assert result.data[0]["symbol"] == "MSFT"
    assert result.metadata["rows"] == 2


def test_fmp_provider_successful_earnings(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    provider = FMPProvider(
        opener=FakeOpener(payload=[{"symbol": "NVDA", "date": "2026-02-20"}])
    )

    result = provider.get_earnings("nvda")

    assert result.success is True
    assert result.message == "FMP earnings retrieved."
    assert result.data == [{"symbol": "NVDA", "date": "2026-02-20"}]
    assert result.metadata["endpoint"] == "earnings"


def test_fmp_provider_successful_institutional_metrics(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    provider = FMPProvider(
        opener=FakeOpener(payload=[{"holder": "Example Fund", "shares": 1000}])
    )

    result = provider.get_institutional_metrics("amzn")

    assert result.success is True
    assert result.message == "FMP institutional metrics retrieved."
    assert result.data == [{"holder": "Example Fund", "shares": 1000}]
    assert result.metadata["ticker"] == "AMZN"


def test_fmp_provider_successful_insider_activity(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    opener = FakeOpener(payload=[{"symbol": "TSLA", "transactionType": "Buy"}])
    provider = FMPProvider(opener=opener)

    result = provider.get_insider_activity("tsla")

    assert result.success is True
    assert result.message == "FMP insider activity retrieved."
    assert result.data == [{"symbol": "TSLA", "transactionType": "Buy"}]
    assert "/insider-trading?" in opener.calls[0][0]
    assert "symbol=TSLA" in opener.calls[0][0]


def test_fmp_provider_malformed_response(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    provider = FMPProvider(opener=FakeOpener(payload={"symbol": "AAPL"}))

    result = provider.get_company_profile("AAPL")

    assert result.success is False
    assert result.message == "FMP response was malformed for AAPL."
    assert "Malformed response." in result.warnings


def test_fmp_provider_malformed_json(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    provider = FMPProvider(opener=FakeOpener(payload=b"{not-json"))

    result = provider.get_company_profile("AAPL")

    assert result.success is False
    assert result.message == "FMP response was malformed for AAPL."


def test_fmp_provider_server_error(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    provider = FMPProvider(opener=FakeOpener(error=http_error(500)))

    result = provider.get_company_profile("AAPL")

    assert result.success is False
    assert result.message == "FMP request failed for AAPL."
    assert "HTTP 500" in result.warnings


def test_fmp_provider_rate_limit(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    provider = FMPProvider(opener=FakeOpener(error=http_error(429)))

    result = provider.get_company_profile("AAPL")

    assert result.success is False
    assert result.message == "FMP rate limit reached for AAPL."
    assert "Rate limited." in result.warnings


def test_fmp_provider_network_failure(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    provider = FMPProvider(opener=FakeOpener(error=URLError("offline")))

    result = provider.get_company_profile("AAPL")

    assert result.success is False
    assert result.message == "FMP request failed for AAPL."
    assert result.warnings


def test_fmp_provider_deterministic_normalization(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    payload = [{"symbol": "AAPL", "companyName": "Apple Inc."}]
    provider = FMPProvider(opener=FakeOpener(payload=payload))

    first = provider.get_company_profile(" aapl ")
    second = provider.get_company_profile("AAPL")

    assert first.data == second.data
    assert first.metadata == second.metadata


def test_fmp_provider_price_history_not_implemented(monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "test-key")
    provider = FMPProvider(opener=FakeOpener(payload=[]))

    result = provider.get_price_history("AAPL")

    assert result.success is False
    assert result.source == "fmp"
    assert result.message == "FMP price history provider is not yet implemented."
    assert "Not yet implemented." in result.warnings
